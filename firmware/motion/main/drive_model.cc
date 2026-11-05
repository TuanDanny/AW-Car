#include "drive_model.h"

#include <algorithm>
#include <cstdlib>

namespace awcar::motion {
bool Config::Valid() const {
  return circumference_um >= 10000 && circumference_um <= 2000000 &&
         pulses_per_rev >= 1 && pulses_per_rev <= 100000 && track_mm >= 20 &&
         track_mm <= 1000 && full_speed_mm_s >= 1 && full_speed_mm_s <= 2000 &&
         max_v >= 1 && max_v <= 2000 && max_omega >= 1 && max_omega <= 10000 &&
         kick_ms >= 10 && kick_ms <= 1000 && rest_ms >= 100 &&
         rest_ms <= 5000 && reverse_ms >= rest_ms && reverse_ms <= 10000 &&
         slow_mm_s >= 1 && slow_mm_s <= 100 && duty_limit >= 1 &&
         duty_limit <= 1350;
}
void DriveModel::Configure(Config cfg, uint64_t now) {
  cfg_ = cfg;
  Stop(now);
}
void DriveModel::Observe(const fpga::Snapshot& s, uint64_t now) {
  const std::array<uint32_t, 2> count{s.left_count, s.right_count};
  const std::array<uint32_t, 2> period{s.left_period, s.right_period};
  const std::array<uint32_t, 2> age{s.left_age, s.right_age};
  speeds_valid_ = (s.encoder & 3) == 3;
  for (int i = 0; i < 2; ++i) {
    if (!have_sample_ || count[i] != counts_[i]) {
      quiet_at_[i] = progress_at_[i] = now;
    }
    if ((s.encoder & (1u << i)) && period[i] && age[i] != UINT32_MAX) {
      // Age prevents an old fast period from claiming the wheel is still fast
      // forever. This is an unsigned estimate, never measured direction.
      const uint64_t ticks = std::max(period[i], age[i]);
      speeds_[i] = uint32_t(std::min<uint64_t>(
          UINT32_MAX, uint64_t(cfg_.circumference_um) * 27000 /
                          (uint64_t(cfg_.pulses_per_rev) * ticks)));
    } else {
      speeds_[i] = 0;
    }
    counts_[i] = count[i];
  }
  have_sample_ = true;
}
bool DriveModel::Rested(uint64_t now) const {
  return have_sample_ && now - zero_at_ >= uint64_t(cfg_.rest_ms) * 1000 &&
         now - quiet_at_[0] >= uint64_t(cfg_.rest_ms) * 1000 &&
         now - quiet_at_[1] >= uint64_t(cfg_.rest_ms) * 1000;
}
void DriveModel::Stop(uint64_t now) {
  target_ = {};
  phase_ = DrivePhase::Neutral;
  phase_at_ = zero_at_ = now;
  monitoring_ = {};
  slow_started_ = false;
  // Keep the last physical direction across disarm: wheels may still coast.
}
void DriveModel::Target(int v, int omega, uint64_t now) {
  const int64_t turn = int64_t(omega) * cfg_.track_mm / 2000;
  std::array<int64_t, 2> t{int64_t(v) - turn, int64_t(v) + turn};
  const auto peak = std::max(std::abs(t[0]), std::abs(t[1]));
  if (peak > cfg_.full_speed_mm_s)
    for (auto& value : t) value = value * cfg_.full_speed_mm_s / peak;
  if (!t[0] && !t[1]) {
    if (phase_ != DrivePhase::Neutral) Stop(now);
    return;
  }
  target_ = {int32_t(t[0]), int32_t(t[1])};
  if (phase_ == DrivePhase::Neutral) {
    phase_ = Rested(now) ? DrivePhase::Kick : DrivePhase::Run;
    phase_at_ = now;
  }
}
DriveOutput DriveModel::Step(uint64_t now) {
  DriveOutput out{};
  out.left_target = target_[0];
  out.right_target = target_[1];
  out.direction = direction_;
  out.phase = phase_;
  out.left_speed_abs = speeds_[0];
  out.right_speed_abs = speeds_[1];
  out.speeds_valid = speeds_valid_;
  if (phase_ == DrivePhase::Neutral) return out;
  uint8_t desired = direction_;
  for (int i = 0; i < 2; ++i) {
    if (target_[i] > 0) desired &= uint8_t(~(1u << i));
    if (target_[i] < 0) desired |= uint8_t(1u << i);
  }
  if (have_direction_ && desired != direction_ &&
      phase_ != DrivePhase::Coasting) {
    phase_ = DrivePhase::Coasting;
    phase_at_ = zero_at_ = now;
    monitoring_ = {};
    slow_started_ = false;
  }
  if (phase_ == DrivePhase::Coasting) {
    out.phase = phase_;
    if (now - phase_at_ >= uint64_t(cfg_.reverse_ms) * 1000) {
      out.fault = ReversalTimeout;
      return out;
    }
    const bool slow = speeds_valid_ && speeds_[0] <= cfg_.slow_mm_s &&
                      speeds_[1] <= cfg_.slow_mm_s;
    if (slow && !slow_started_) {
      slow_started_ = true;
      slow_at_ = now;
    }
    if (!slow) slow_started_ = false;
    if (!Rested(now) && !(slow_started_ && now - slow_at_ >= 100000))
      return out;
    direction_ = desired;
    have_direction_ = true;
    phase_ = Rested(now) ? DrivePhase::Kick : DrivePhase::Run;
    phase_at_ = now;
  } else {
    direction_ = desired;
    have_direction_ = true;
  }
  if (phase_ == DrivePhase::Kick &&
      now - phase_at_ >= uint64_t(cfg_.kick_ms) * 1000)
    phase_ = DrivePhase::Run;
  std::array<uint32_t, 2> duty{};
  const int64_t peak =
      std::max(std::abs(int64_t(target_[0])), std::abs(int64_t(target_[1])));
  const int64_t requested = peak * cfg_.duty_limit / cfg_.full_speed_mm_s;
  int64_t amplitude = requested;
  if (phase_ == DrivePhase::Kick) {
    const int64_t boost =
        std::min<int64_t>(cfg_.duty_limit, requested * 100 / 30);
    const auto elapsed = now - phase_at_;
    amplitude =
        boost - (boost - requested) * int64_t(elapsed) / (cfg_.kick_ms * 1000);
  }
  for (int i = 0; i < 2; ++i) {
    duty[i] = uint32_t(std::abs(int64_t(target_[i])) * amplitude / peak);
    if (!duty[i]) {
      monitoring_[i] = false;
      continue;
    }
    if (!monitoring_[i]) {
      monitoring_[i] = true;
      progress_at_[i] = now;
    }
    const uint64_t expected =
        uint64_t(cfg_.circumference_um) * 2000 /
            (uint64_t(cfg_.pulses_per_rev) *
             uint64_t(std::max<int64_t>(1, std::abs(int64_t(target_[i]))))) +
        200000;
    const uint64_t limit = std::clamp<uint64_t>(expected, 750000, 10000000);
    if (now - progress_at_[i] >= limit) out.fault |= Encoder;
  }
  out.left = uint16_t(duty[0]);
  out.right = uint16_t(duty[1]);
  out.direction = direction_;
  out.phase = phase_;
  return out;
}
}  // namespace awcar::motion
