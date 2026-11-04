#pragma once
#include <cstdint>

namespace awcar::indicator {
enum class Color : uint8_t { Blue, Green, Red };
enum class Reason : uint8_t {
  Starting, WifiOffline, MotionWaiting, MotionStale, MotionFault,
  AiWaiting, Ready, Locked, FpgaWaiting, SafetyWaiting, InternalFault
};
struct State {
  Color color = Color::Blue;
  Reason reason = Reason::Starting;
};
constexpr const char* Name(Color color) {
  return color == Color::Red ? "red" : color == Color::Green ? "green" : "blue";
}
constexpr const char* Name(Reason reason) {
  constexpr const char* names[] = {
    "starting", "wifi_offline", "motion_waiting", "motion_stale", "motion_fault",
    "ai_waiting", "ready", "locked", "fpga_waiting", "safety_waiting", "internal_fault"
  };
  return names[static_cast<unsigned>(reason)];
}
constexpr State Brain(bool wifi, int64_t age_ms, uint16_t fault,
                      bool motion_fault, bool ai_required, bool ai_online) {
  if (fault || motion_fault) return {Color::Red, Reason::MotionFault};
  if (age_ms >= 150) return {Color::Red, Reason::MotionStale};
  if (!wifi) return {Color::Blue, Reason::WifiOffline};
  if (age_ms < 0) return {Color::Blue, Reason::MotionWaiting};
  if (ai_required && !ai_online) return {Color::Blue, Reason::AiWaiting};
  return {Color::Green, Reason::Ready};
}
constexpr State Motion(uint16_t fault, uint16_t fpga_fault, bool configured,
                       bool fresh, bool safety_ok, bool gate_ok, bool runtime_ok) {
  if (!runtime_ok) return {Color::Red, Reason::InternalFault};
  // FPGA encoder/RX diagnostic warnings alone are not latched safety faults.
  if (fault || (fpga_fault & 0x88ff)) return {Color::Red, Reason::MotionFault};
  if (!configured) return {Color::Blue, Reason::Locked};
  if (!fresh) return {Color::Blue, Reason::FpgaWaiting};
  if (!safety_ok || !gate_ok) return {Color::Blue, Reason::SafetyWaiting};
  return {Color::Green, Reason::Ready};
}
// A retry deadline bounds failed LED writes. Color/diagnosis are not motor authority.
class OutputCache {
 public:
  bool Due(State desired, uint64_t now_us) const {
    return now_us >= retry_at_ && (!known_ || desired.color != applied_);
  }
  void Complete(State desired, bool success, uint64_t now_us) {
    known_ = success;
    if (success) { applied_ = desired.color; ++writes_; retry_at_ = 0; }
    else { ++errors_; retry_at_ = now_us + 1000000; }
  }
  bool Known() const { return known_; }
  uint32_t Writes() const { return writes_; }
  uint32_t Errors() const { return errors_; }
 private:
  bool known_ = false;
  Color applied_ = Color::Blue;
  uint64_t retry_at_ = 0;
  uint32_t writes_ = 0, errors_ = 0;
};
}  // namespace awcar::indicator
