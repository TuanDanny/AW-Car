#include "motion_core.h"

#include <algorithm>
#include <cstdlib>

namespace awcar::motion {
void MotionCore::Revoke(uint64_t now) {
  ++epoch_;
  if (!epoch_) ++epoch_;
  lease_until_ = first_twist_until_ = 0;
  arm_context_ = clearing_ = false;
  command_dirty_ = false;
  stop_wait_ = false;
  drive_.Stop(now);
  output_ = {};
  state_ = fault_ ? State::Fault : State::Disarmed;
  if (fault_)
    link_.Fail(fault_, now);
  else
    link_.Stop(now);
  StatusChanged();
}
void MotionCore::Trip(uint16_t cause, uint64_t now) {
  const bool changed =
      (fault_ | cause) != fault_ || state_ != State::Fault || clearing_;
  fault_ |= cause;
  if (changed)
    Revoke(now);
  else
    link_.Fail(cause, now);
  // A persistent latched fault must not overwrite a fresh HELLO/STOP ACK on
  // every tick; otherwise asynchronous recovery can never reach CLEAR_FAULT.
  if (changed) result_ = Result::Unsafe;
}
void MotionCore::RuntimeFault(uint16_t cause, uint64_t now) {
  Trip(cause, now);
}
void MotionCore::LocalStop(uint64_t now) {
  Revoke(now);
  stop_wait_ = !fault_;
  result_ = fault_ ? Result::Unsafe : Result::Busy;
}
void MotionCore::InputsNow(Inputs inputs, uint64_t now) {
  inputs_ = inputs;
  if ((state_ == State::Arming || state_ == State::Armed) &&
      (!inputs.safety_ok || !inputs.gate_ok))
    Trip(Gate, now);
}
bool MotionCore::Configure(const Config& cfg, uint64_t now) {
  if (state_ != State::Disarmed || link_.DriverPermit() ||
      link_.MotionPermit() || link_.Busy() || !cfg.Valid())
    return false;
  cfg_ = cfg;
  drive_.Configure(cfg_, now);
  StatusChanged();
  return true;
}
void MotionCore::OnBrain(const bm::Frame& f, uint64_t now) {
  Tick(now);  // Expiration wins a frame arriving exactly at its deadline.
  if (f.type < bm::Hello || f.type > bm::Clear ||
      f.length != (f.type == bm::Twist ? 7 : 0))
    return;
  last_req_ = f.seq;
  StatusChanged();
  if (f.type == bm::Stop) {
    operation_seq_ = f.seq;
    Revoke(now);
    stop_wait_ = !fault_;
    result_ = fault_ ? Result::OK : Result::Busy;
    return;
  }
  if (f.type == bm::Hello) {
    if (state_ != State::Disarmed && state_ != State::Fault) {
      result_ = Result::BadState;
      return;
    }
    if (stop_wait_ || link_.Busy() || clearing_) {
      result_ = Result::Busy;
      return;
    }
    if (!f.session || f.session == session_) {
      result_ = Result::BadSession;
      return;
    }
    session_ = f.session;
    accepted_seq_ = f.seq;
    have_accepted_ = true;
    arm_context_ = true;
    applied_ = 0xffff;
    result_ = Result::OK;
    return;
  }
  if (!f.session || f.session != session_ || !arm_context_) {
    result_ = Result::BadSession;
    return;
  }
  const uint16_t delta = uint16_t(f.seq - accepted_seq_);
  if (have_accepted_ && (!delta || delta >= 0x8000)) {
    result_ = Result::BadSequence;
    return;
  }
  if (f.type == bm::Arm) {
    if (state_ != State::Disarmed || fault_ || clearing_ || stop_wait_ ||
        link_.Busy()) {
      result_ = Result::BadState;
      return;
    }
    if (!cfg_.validated || !cfg_.Valid() || !inputs_.safety_ok ||
        !inputs_.gate_ok || inputs_.ack || !link_.Fresh(now) ||
        (link_.Sample().encoder & 0x1c) != 0x1c || link_.Sample().state != 0 ||
        (link_.Sample().fault & 0x88ff)) {
      result_ = Result::Unsafe;
      return;
    }
    accepted_seq_ = f.seq;
    operation_seq_ = f.seq;
    state_ = State::Arming;
    result_ = Result::Busy;
    drive_.Stop(now);
    link_.Begin(false, now);
    return;
  }
  if (f.type == bm::Clear) {
    if (state_ != State::Fault || clearing_ || stop_wait_ || link_.Busy()) {
      result_ = Result::BadState;
      return;
    }
    if (!inputs_.safety_ok || inputs_.ack || !link_.Fresh(now) ||
        link_.ResetRequired() || (link_.Sample().encoder & 0x1c) != 0x1c) {
      result_ = Result::Unsafe;
      return;
    }
    accepted_seq_ = f.seq;
    operation_seq_ = f.seq;
    clearing_ = true;
    result_ = Result::Busy;
    link_.Begin(true, now);
    return;
  }
  if (state_ != State::Armed) {
    result_ = Result::BadState;
    return;
  }
  const auto* p = f.payload.data();
  const int v = int16_t(bm::U16(p)), omega = int16_t(bm::U16(p + 2));
  const uint16_t ttl = bm::U16(p + 5);
  if ((p[4] != 1 && p[4] != 2) || !ttl || ttl > 250 ||
      std::abs(int64_t(v)) > cfg_.max_v ||
      std::abs(int64_t(omega)) > cfg_.max_omega) {
    result_ = Result::BadRange;
    return;
  }
  if (!link_.Fresh(now) || !link_.Ready()) {
    result_ = Result::Unsafe;
    return;
  }
  accepted_seq_ = applied_ = f.seq;
  have_accepted_ = true;
  result_ = Result::OK;
  lease_until_ = now + uint64_t(ttl) * 1000;
  first_twist_until_ = 0;
  drive_.Target(v, omega, now);
  command_dirty_ = true;
}
void MotionCore::OnFpga(const fpga::Frame& f, uint64_t now) {
  Tick(now);
  fpga::Snapshot sample;
  if (!fpga::DecodeStatus(f, sample) || !link_.Receive(sample, now)) return;
  drive_.Observe(sample, now);
  if (link_.ResetRequired())
    Trip(Internal, now);
  else if (!clearing_ && ((sample.fault & 0xff) || sample.state == 4))
    Trip(Gate, now);
  else if (link_.Faults())
    Trip(link_.Faults(), now);
  Tick(now);
}
void MotionCore::Tick(uint64_t now) {
  if (had_tick_ && now < last_tick_) {
    Trip(Internal, last_tick_);
    return;
  }
  if (had_tick_ && (state_ == State::Armed || state_ == State::Arming) &&
      now - last_tick_ >= 20000)
    Trip(Internal, now);
  had_tick_ = true;
  last_tick_ = now;
  if (state_ == State::Armed) {
    const uint64_t until = lease_until_ ? lease_until_ : first_twist_until_;
    if (until && now >= until) {
      operation_seq_ = last_req_;
      Revoke(now);
      stop_wait_ = true;
      result_ = Result::LeaseExpired;
    } else if (!link_.Fresh(now))
      Trip(FpgaStale, now);
  }
  link_.Tick(inputs_, now);
  if (link_.Faults() && (!clearing_ || link_.Phase() == LinkPhase::Faulted)) {
    const bool was_clearing = clearing_;
    Trip(link_.Faults(), now);
    if (was_clearing) clearing_ = false;
  }
  if (clearing_ && link_.Phase() == LinkPhase::Idle && inputs_.gate_ok &&
      inputs_.safety_ok && link_.Fresh(now)) {
    clearing_ = false;
    fault_ = 0;
    state_ = State::Disarmed;
    arm_context_ = false;
    lease_until_ = first_twist_until_ = 0;
    last_req_ = operation_seq_;
    result_ = Result::OK;
    ++epoch_;
    StatusChanged();
  }
  if (stop_wait_ && link_.Phase() == LinkPhase::Idle) {
    stop_wait_ = false;
    last_req_ = operation_seq_;
    if (result_ != Result::LeaseExpired) result_ = Result::OK;
    StatusChanged();
  }
  if (state_ == State::Arming && link_.Ready()) {
    state_ = State::Armed;
    last_req_ = operation_seq_;
    result_ = Result::OK;
    first_twist_until_ = now + 120000;
    command_dirty_ = true;
    StatusChanged();
  }
  if (link_.DriverPermit() &&
      (state_ == State::Armed || state_ == State::Arming)) {
    output_ = state_ == State::Armed ? drive_.Step(now) : DriveOutput{};
    if (output_.fault) {
      Trip(output_.fault, now);
      return;
    }
    if (command_dirty_ || now - last_cmd_ >= 10000) {
      link_.Command(output_.direction, output_.left, output_.right, now);
      command_dirty_ = false;
      last_cmd_ = now;
    }
  } else
    output_ = {};
}
bool MotionCore::TakeFpgaTx(fpga::Frame& f, uint64_t now) {
  // This does not generate commands or renew a lease. A stalled control task
  // must never be hidden by a serial task replaying a cached duty.
  if ((state_ == State::Armed || state_ == State::Arming) &&
      (!had_tick_ || now - last_tick_ >= 20000))
    Trip(Internal, now);
  return link_.TakeTx(f, now);
}
bool MotionCore::TakeBrainTx(bm::Frame& f, uint64_t now) {
  if (!status_dirty_ && now - last_status_ < 50000) return false;
  f = {};
  f.type = bm::Status;
  f.length = 17;
  f.session = session_;
  f.seq = ++brain_seq_;
  auto* p = f.payload.data();
  bm::Put16(p, last_req_);
  bm::Put16(p + 2, applied_);
  p[4] = uint8_t(result_);
  p[5] = uint8_t(state_);
  bm::Put16(p + 6, fault_);
  // Single-OUT cannot establish signed body v/omega. Battery has no ADC yet.
  bm::Put16(p + 14, uint16_t(std::min<uint64_t>(65535, link_.Age(now) / 1000)));
  p[16] = uint8_t((link_.Fresh(now) ? 8 : 0) |
                  (state_ == State::Armed && lease_until_ > now ? 16 : 0) |
                  (link_.DriverPermit() && !fault_ ? 32 : 0));
  last_status_ = now;
  status_dirty_ = false;
  return true;
}
View MotionCore::GetView(uint64_t now) const {
  View v;
  v.state = state_;
  v.fault = fault_;
  v.fpga_fault = link_.Sample().fault;
  v.last_req = last_req_;
  v.applied = applied_;
  v.result = result_;
  v.epoch = epoch_;
  v.driver_permit = link_.DriverPermit() && !fault_;
  v.motion_permit = link_.MotionPermit();
  v.recovery_req = link_.RecoveryReq();
  v.configured = cfg_.validated && cfg_.Valid();
  v.lease = state_ == State::Armed && lease_until_ > now;
  v.fresh = link_.Fresh(now);
  v.snapshot_age_us = link_.Age(now);
  v.link_phase = link_.Phase();
  v.drive = output_;
  v.snapshot_seq = link_.Sample().seq;
  v.fpga_state = link_.Sample().state;
  v.left_count = link_.Sample().left_count;
  v.right_count = link_.Sample().right_count;
  return v;
}
}  // namespace awcar::motion
