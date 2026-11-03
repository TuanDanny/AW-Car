#pragma once
#include <cstdint>

#include "brain_motion_codec.h"
#include "drive_model.h"
#include "fpga_link.h"

namespace awcar::motion {
enum class State : uint8_t { Disarmed, Arming, Armed, Fault };
enum class Result : uint8_t {
  OK,
  BadState,
  BadSession,
  BadSequence,
  BadRange,
  Unsafe,
  LeaseExpired,
  Busy,
  None = 255
};
struct View {
  State state = State::Disarmed;
  uint16_t fault = 0, fpga_fault = 0, last_req = 0xffff, applied = 0xffff;
  Result result = Result::None;
  uint32_t epoch = 1;
  bool driver_permit = false, motion_permit = false, recovery_req = false;
  bool configured = false, lease = false, fresh = false;
  uint64_t snapshot_age_us = UINT64_MAX;
  uint16_t snapshot_seq = 0;
  uint8_t fpga_state = 0;
  uint32_t left_count = 0, right_count = 0;
  LinkPhase link_phase = LinkPhase::Idle;
  DriveOutput drive{};
};
// One owner serializes every method. Monotonic microseconds are supplied by
// the caller, making the exact production algorithms executable on a PC.
class MotionCore {
 public:
  explicit MotionCore(Config cfg = {}, uint32_t seed = 1)
      : cfg_(cfg), drive_(cfg), link_(seed) {}
  void InputsNow(Inputs inputs, uint64_t now);
  void OnBrain(const bm::Frame& f, uint64_t now);
  void OnFpga(const fpga::Frame& f, uint64_t now);
  void Tick(uint64_t now);
  void LocalStop(uint64_t now);
  void RuntimeFault(uint16_t fault, uint64_t now);
  bool Configure(const Config& cfg, uint64_t now);
  const Config& Configuration() const { return cfg_; }
  bool TakeFpgaTx(fpga::Frame& f, uint64_t now);
  bool TakeBrainTx(bm::Frame& f, uint64_t now);
  uint32_t LinkGeneration() const { return link_.Generation(); }
  View GetView(uint64_t now) const;

 private:
  Config cfg_;
  DriveModel drive_;
  FpgaLink link_;
  Inputs inputs_{};
  State state_ = State::Disarmed;
  Result result_ = Result::None;
  DriveOutput output_{};
  uint16_t fault_ = 0, last_req_ = 0xffff, applied_ = 0xffff;
  uint16_t brain_seq_ = 0, accepted_seq_ = 0, operation_seq_ = 0;
  uint32_t session_ = 0, epoch_ = 1;
  bool have_accepted_ = false, arm_context_ = false, clearing_ = false;
  bool stop_wait_ = false, status_dirty_ = true, had_tick_ = false,
       command_dirty_ = false;
  uint64_t lease_until_ = 0, first_twist_until_ = 0, last_tick_ = 0;
  uint64_t last_cmd_ = 0, last_status_ = 0;
  void Revoke(uint64_t now);
  void Trip(uint16_t cause, uint64_t now);
  void StatusChanged() { status_dirty_ = true; }
};
}  // namespace awcar::motion
