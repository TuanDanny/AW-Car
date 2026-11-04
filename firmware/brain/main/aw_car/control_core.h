#pragma once
#include <array>
#include <cstdint>

#include "brain_motion_codec.h"

namespace awcar {
enum class Mode { Manual, AI };
enum class Result { OK, Unsafe, Busy, BadRange, BadSequence, Stale, WrongMode };
const char* ResultName(Result r);
struct Config {
  int v_max = 200, omega_max = 1000;
  uint32_t session_seed = 0x419b7a21;
};
struct State {
  Mode mode = Mode::Manual;
  bool web = false, ai_online = false, authorized = false, switching = false;
  bool clearing = false;
  uint32_t epoch = 1, challenge = 0;
  uint64_t ai_remaining_ms = 0, action_remaining_ms = 0;
  int v = 0, omega = 0, motion_state = 0;
  uint16_t fault = 0, last_req = 0xffff, applied = 0xffff;
  uint8_t result = 255, flags = 0;
  int v_est = 0, omega_est = 0, battery = 0, encoder_age = 65535;
  int64_t telemetry_age_ms = -1;
  const char* reason = "boot";
};
// All methods must be serialized by the adapter. No I/O, allocation, RTOS or
// sleeping here.
class ControlCore {
 public:
  explicit ControlCore(Config cfg = {})
      : cfg_(cfg), next_session_(cfg.session_seed ? cfg.session_seed : 1) {}
  void Tick(uint64_t now);
  void WebConnect(uint64_t now);
  void WebDisconnect(uint64_t now);
  void SetAiOnline(bool online, uint64_t now);
  Result SetMode(Mode mode, uint64_t now);
  Result RequestArm(uint32_t epoch, uint64_t now);
  Result RequestClear(uint32_t epoch, uint64_t now);
  void Stop(const char* reason, uint64_t now);
  Result ManualMove(uint32_t epoch, uint32_t challenge, uint32_t seq, int v,
                    int omega, int ttl, bool deadman, uint64_t now);
  Result VoiceMove(uint32_t epoch, int action, int pct, int duration,
                   uint64_t now);
  void OnStatus(const bm::Frame& frame, uint64_t now);
  bool TakeTx(bm::Frame& frame, uint64_t now);
  State GetState(uint64_t now) const;
  uint32_t Epoch() const { return s_.epoch; }
  bool Authorized() const { return s_.authorized; }

 private:
  enum class ArmPhase {
    None, Hello, WaitHello, Arm, WaitArm, WaitClearStop,
    ClearHello, WaitClearHello, Clear, WaitClear
  };
  struct Challenge {
    uint32_t id = 0, epoch = 0;
    uint64_t at = 0;
  };
  Config cfg_;
  State s_;
  ArmPhase arm_ = ArmPhase::None;
  std::array<Challenge, 3> challenges_{};
  size_t challenge_slot_ = 0;
  uint32_t challenge_next_ = 0, challenge_epoch_ = 0, last_web_seq_ = 0,
           next_session_ = 0, session_ = 0;
  uint16_t tx_seq_ = 0, expected_req_ = 0, last_status_seq_ = 0,
           stop_ack_seq_ = 0;
  bool have_web_seq_ = false, have_status_seq_ = false, have_status_ = false,
       stop_pending_ = true, dirty_ = false, await_stop_ack_ = true;
  bool status_loss_handled_ = false;
  uint64_t last_status_ = 0, last_manual_ = 0, manual_ttl_ = 120000,
           action_until_ = 0, grant_until_ = 0;
  uint64_t last_tx_ = 0, last_challenge_ = 0, arm_until_ = 0;
  void Target(int v, int omega) {
    s_.v = v;
    s_.omega = omega;
    dirty_ = true;
  }
  bool Fresh(uint64_t now) const {
    return have_status_ && now - last_status_ < 150000;
  }
};
}  // namespace awcar
