#pragma once
#include <array>
#include <cstdint>

#include "fpga_codec.h"

namespace awcar::motion {
enum Fault : uint16_t {
  Gate = 1,
  FpgaStale = 2,
  Encoder = 4,
  Sensor = 8,
  Overcurrent = 16,
  Undervolt = 32,
  Pid = 64,
  Internal = 128,
  ReversalTimeout = 256
};
struct Config {
  bool validated = false;
  uint32_t circumference_um = 188496, pulses_per_rev = 20, track_mm = 120;
  uint32_t full_speed_mm_s = 200, max_v = 200, max_omega = 1000;
  uint32_t kick_ms = 200, rest_ms = 500, reverse_ms = 1500;
  uint32_t slow_mm_s = 20, duty_limit = 1350;
  bool Valid() const;
};
enum class DrivePhase : uint8_t { Neutral, Kick, Run, Coasting };
struct DriveOutput {
  uint16_t left = 0, right = 0, fault = 0;
  uint8_t direction = 0;
  DrivePhase phase = DrivePhase::Neutral;
  int32_t left_target = 0, right_target = 0;
  uint32_t left_speed_abs = 0, right_speed_abs = 0;
  bool speeds_valid = false;
};
class DriveModel {
 public:
  explicit DriveModel(Config cfg = {}) : cfg_(cfg) {}
  void Configure(Config cfg, uint64_t now);
  void Observe(const fpga::Snapshot& s, uint64_t now);
  void Target(int v, int omega, uint64_t now);
  void Stop(uint64_t now);
  DriveOutput Step(uint64_t now);

 private:
  Config cfg_;
  std::array<int32_t, 2> target_{};
  std::array<uint32_t, 2> counts_{}, speeds_{};
  std::array<uint64_t, 2> quiet_at_{}, progress_at_{};
  std::array<bool, 2> monitoring_{};
  bool have_sample_ = false, speeds_valid_ = false, have_direction_ = false;
  uint8_t direction_ = 0;
  DrivePhase phase_ = DrivePhase::Neutral;
  uint64_t zero_at_ = 0, phase_at_ = 0, slow_at_ = 0;
  bool slow_started_ = false;
  bool Rested(uint64_t now) const;
};
}  // namespace awcar::motion
