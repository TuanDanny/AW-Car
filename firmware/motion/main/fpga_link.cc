#include "fpga_link.h"
namespace awcar::motion {
void FpgaLink::Queue(uint8_t type, uint64_t now) {
  tx_ = {};
  tx_.type = type;
  tx_.session = session_;
  tx_.seq = ++seq_;
  pending_ = true;
  tx_at_ = now;
}
void FpgaLink::Begin(bool clear, uint64_t now) {
  discovery_pending_ = false;
  clear_ = clear;
  permit_ = false;
  pending_ = false;
  pending_seen_ = false;
  phase_ = LinkPhase::ReqHigh;
  until_ = now + 500000;
  // Keep snapshot freshness monotonic through a protocol recovery. The peer's
  // snapshot counter does not reset when its UART session is invalidated.
  session_ = ++seed_;
  if (!session_) session_ = ++seed_;
  seq_ = 0;
  fault_ = 0;
  ++generation_;
}
void FpgaLink::Stop(uint64_t now) {
  discovery_pending_ = false;
  if (phase_ == LinkPhase::Stopping)
    return;  // Repeated STOP cannot extend time.
  if (phase_ == LinkPhase::Faulted) {
    Queue(fpga::Disable, now);
    return;
  }
  if (phase_ == LinkPhase::Idle && !permit_) {
    ++generation_;
    Queue(fpga::Disable, now);
    return;
  }
  phase_ = LinkPhase::Stopping;
  until_ = now + 30000;
  pending_seen_ = false;
  ++generation_;
  Queue(fpga::Disable, now);
  // Keep the FPGA's logical permit until DISABLE is acknowledged. The separate
  // driver permit is already LOW because Stopping is never DriverPermit().
}
void FpgaLink::Fail(uint16_t cause, uint64_t now) {
  const bool was_failed = phase_ == LinkPhase::Faulted;
  if (!was_failed) discovery_pending_ = false;
  fault_ |= cause;
  phase_ = LinkPhase::Faulted;
  permit_ = false;
  pending_seen_ = false;
  if (!was_failed) {
    ++generation_;
    Queue(fpga::Disable, now);
  }
}
bool FpgaLink::Receive(const fpga::Snapshot& s, uint64_t now) {
  // Session-zero terminal snapshots are only meaningful during discovery,
  // revocation or CLEAR. Running snapshots must belong to the new handshake.
  const bool scoped = phase_ == LinkPhase::Hello ||
                      phase_ == LinkPhase::Pending ||
                      phase_ == LinkPhase::Armed || phase_ == LinkPhase::Wake ||
                      phase_ == LinkPhase::Ready;
  if (scoped && s.session != session_) return false;
  if (phase_ == LinkPhase::Clearing && s.session != session_ && s.session != 0)
    return false;
  const uint16_t delta = uint16_t(s.seq - last_snapshot_);
  const uint32_t ticks = s.timestamp - last_timestamp_;
  if (have_seq_ &&
      (!delta || delta >= 0x8000 || !ticks || ticks >= 0x80000000u)) {
    // A reboot resets two counters with different wrap periods. Their
    // differences from the old sample cannot reliably identify that reboot.
    // Rebaseline only after revocation/staleness, from two progressing
    // session-zero samples. Duplicates/sparse candidates never renew age.
    if ((phase_ != LinkPhase::Idle && phase_ != LinkPhase::Faulted) ||
        permit_ || Fresh(now) || s.session != 0) {
      discovery_pending_ = false;
      return false;
    }
    const uint16_t probe_delta = uint16_t(s.seq - discovery_seq_);
    const uint32_t probe_ticks = s.timestamp - discovery_ticks_;
    const bool progressing = discovery_pending_ &&
        now - discovery_at_ < 30000 && probe_delta && probe_delta < 0x8000 &&
        probe_ticks && probe_ticks < 0x80000000u;
    discovery_seq_ = s.seq;
    discovery_ticks_ = s.timestamp;
    discovery_at_ = now;
    discovery_pending_ = true;
    if (!progressing) return false;
    have_seq_ = false;
  }
  discovery_pending_ = false;
  have_seq_ = have_sample_ = true;
  last_snapshot_ = s.seq;
  last_timestamp_ = s.timestamp;
  sample_ = s;
  sample_at_ = now;
  if (s.fault & 0x8800) {
    Fail(Internal, now);
    return true;
  }
  if ((phase_ == LinkPhase::Ready || phase_ == LinkPhase::Wake) &&
      s.state != 3) {
    Fail(Internal, now);
    return true;
  }
  if (phase_ == LinkPhase::Hello && s.session == session_) {
    if (clear_ && s.state == 4) {
      Queue(fpga::Clear, now);
      phase_ = LinkPhase::Clearing;
    } else if (clear_ && s.state == 1 && !(s.fault & 0xff)) {
      // A local-only fault may find a healthy FPGA. Close this recovery
      // session instead of trying CLEAR in HANDSHAKE (which would be ignored).
      Queue(fpga::Disable, now);
      phase_ = LinkPhase::Clearing;
    } else if (!clear_ && s.state == 1 && !(s.fault & 0xff)) {
      Queue(fpga::ArmZero, now);
      phase_ = LinkPhase::Pending;
    } else if (!clear_ && (s.state == 4 || s.fault & 0xff))
      Fail(Gate, now);
  } else if (phase_ == LinkPhase::Pending && s.state == 2 &&
             !(s.fault & 0xff)) {
    pending_seen_ = true;
  } else if (phase_ == LinkPhase::Stopping && s.state == 0 &&
             !(s.fault & 0xff)) {
    permit_ = false;
    phase_ = LinkPhase::Idle;
    pending_ = false;
  } else if (phase_ == LinkPhase::Clearing && s.state == 0 &&
             !(s.fault & 0xff)) {
    permit_ = false;
    phase_ = LinkPhase::Idle;
    pending_ = false;
    fault_ = 0;
  } else if ((phase_ == LinkPhase::Armed || phase_ == LinkPhase::Wake ||
              phase_ == LinkPhase::Ready || phase_ == LinkPhase::Stopping) &&
             (s.fault & 0xff || s.state == 4 || s.state == 5))
    Fail(Gate, now);
  return true;
}
void FpgaLink::Tick(Inputs in, uint64_t now) {
  if (phase_ == LinkPhase::Idle || phase_ == LinkPhase::Faulted) return;
  if (now >= until_ && phase_ != LinkPhase::Ready &&
      phase_ != LinkPhase::Wake) {
    Fail(phase_ == LinkPhase::Stopping ? FpgaStale : Internal, now);
    return;
  }
  if (!in.safety_ok) {
    Fail(Gate, now);
    return;
  }
  // gate_ok may legitimately be LOW while CLEAR requests the external latch.
  if (!clear_ && !in.gate_ok) {
    Fail(Gate, now);
    return;
  }
  if (phase_ == LinkPhase::ReqHigh && in.ack)
    phase_ = LinkPhase::ReqLow;
  else if (phase_ == LinkPhase::ReqLow && !in.ack) {
    phase_ = LinkPhase::Quiet;
    quiet_until_ = now + 5000;
  } else if (phase_ == LinkPhase::Quiet && now >= quiet_until_) {
    Queue(fpga::Hello, now);
    phase_ = LinkPhase::Hello;
  } else if (phase_ == LinkPhase::Pending && pending_seen_ && in.ack) {
    permit_ = true;
    phase_ = LinkPhase::Armed;
  } else if (phase_ == LinkPhase::Armed && sample_.state == 3 &&
             sample_.session == session_ && Fresh(now) && in.fpga_permit) {
    phase_ = LinkPhase::Wake;
    wake_until_ = now + 1000;
  } else if (phase_ == LinkPhase::Wake && now >= wake_until_) {
    phase_ = LinkPhase::Ready;
  }
  if ((phase_ == LinkPhase::Wake || phase_ == LinkPhase::Ready) &&
      (!in.fpga_permit || !in.gate_ok || !Fresh(now)))
    Fail(FpgaStale, now);
}
void FpgaLink::Command(uint8_t dir, uint16_t left, uint16_t right,
                       uint64_t now) {
  if (phase_ != LinkPhase::Ready && phase_ != LinkPhase::Wake) return;
  if (phase_ == LinkPhase::Wake) left = right = 0;
  if (pending_ && tx_.type != fpga::Command) return;
  tx_ = fpga::CommandFrame(session_, ++seq_, dir, left, right);
  pending_ = true;
  tx_at_ = now;
}
bool FpgaLink::TakeTx(fpga::Frame& out, uint64_t now) {
  if (!pending_) return false;
  if (tx_.type == fpga::Command &&
      (now - tx_at_ >= 20000 || !Fresh(now) || !DriverPermit())) {
    pending_ = false;
    return false;
  }
  out = tx_;
  pending_ = false;
  return true;
}
}  // namespace awcar::motion
