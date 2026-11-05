#pragma once
#include <cstdint>

#include "drive_model.h"
#include "fpga_codec.h"

namespace awcar::motion {
struct Inputs {
  bool ack = false, fpga_permit = false, safety_ok = false, gate_ok = false;
};
enum class LinkPhase : uint8_t {
  Idle,
  ReqHigh,
  ReqLow,
  Quiet,
  Hello,
  Pending,
  Armed,
  Wake,
  Ready,
  Stopping,
  Clearing,
  Faulted
};
class FpgaLink {
 public:
  explicit FpgaLink(uint32_t seed = 1) : seed_(seed ? seed : 1) {}
  void Begin(bool clear, uint64_t now);
  void Stop(uint64_t now);
  void Fail(uint16_t cause, uint64_t now);
  bool Receive(const fpga::Snapshot& s, uint64_t now);
  void Tick(Inputs in, uint64_t now);
  void Command(uint8_t dir, uint16_t left, uint16_t right, uint64_t now);
  bool TakeTx(fpga::Frame& out, uint64_t now);
  bool Fresh(uint64_t now) const {
    return have_sample_ && now - sample_at_ < 30000;
  }
  bool Ready() const { return phase_ == LinkPhase::Ready; }
  bool Busy() const {
    return phase_ != LinkPhase::Idle && phase_ != LinkPhase::Faulted;
  }
  bool DriverPermit() const {
    return phase_ == LinkPhase::Ready || phase_ == LinkPhase::Wake;
  }
  bool MotionPermit() const { return permit_; }
  bool RecoveryReq() const { return phase_ == LinkPhase::ReqHigh; }
  bool ResetRequired() const { return (sample_.fault & 0x8800) != 0; }
  uint16_t Faults() const { return fault_; }
  uint32_t Generation() const { return generation_; }
  LinkPhase Phase() const { return phase_; }
  const fpga::Snapshot& Sample() const { return sample_; }
  uint64_t Age(uint64_t now) const {
    return have_sample_ ? now - sample_at_ : UINT64_MAX;
  }

 private:
  LinkPhase phase_ = LinkPhase::Idle;
  fpga::Snapshot sample_{};
  fpga::Frame tx_{};
  bool have_sample_ = false, have_seq_ = false, pending_ = false;
  bool permit_ = false, clear_ = false, pending_seen_ = false;
  uint32_t seed_ = 1, session_ = 0, generation_ = 1, last_timestamp_ = 0;
  uint16_t seq_ = 0, last_snapshot_ = 0, fault_ = 0;
  uint64_t sample_at_ = 0, until_ = 0, quiet_until_ = 0, wake_until_ = 0,
           tx_at_ = 0;
  void Queue(uint8_t type, uint64_t now);
};
}  // namespace awcar::motion
