#include "control_core.h"

#include <algorithm>
#include <cstdlib>
namespace awcar {
const char* ResultName(Result r) {
  switch (r) {
    case Result::OK:
      return "OK";
    case Result::Unsafe:
      return "UNSAFE";
    case Result::Busy:
      return "BUSY";
    case Result::BadRange:
      return "BAD_RANGE";
    case Result::BadSequence:
      return "BAD_SEQUENCE";
    case Result::Stale:
      return "STALE";
    case Result::WrongMode:
      return "WRONG_MODE";
  }
  return "UNSAFE";
}
void ControlCore::Stop(const char* reason, uint64_t) {
  ++s_.epoch;
  if (!s_.epoch) ++s_.epoch;
  s_.authorized = false;
  s_.clearing = false;
  s_.reason = reason;
  arm_ = ArmPhase::None;
  grant_until_ = action_until_ = 0;
  s_.v = s_.omega = 0;
  dirty_ = false;
  stop_pending_ = true;
  await_stop_ack_ = true;
  have_web_seq_ = false;
  // Revocation also ends the receive context: a rebooted Motion may restart
  // its STATUS sequence. Discovery cannot grant authority; a matching STOP
  // acknowledgement and a fresh HELLO/ARM exchange are still required.
  have_status_seq_ = false;
}
void ControlCore::WebConnect(uint64_t now) {
  s_.web = true;
  if (s_.mode == Mode::Manual) Stop("web_connected", now);
}
void ControlCore::WebDisconnect(uint64_t now) {
  s_.web = false;
  if (s_.mode == Mode::Manual) Stop("web_disconnected", now);
}
void ControlCore::SetAiOnline(bool online, uint64_t now) {
  s_.ai_online = online;
  if (!online && s_.mode == Mode::AI &&
      (s_.authorized || arm_ != ArmPhase::None))
    Stop("ai_offline", now);
}
Result ControlCore::SetMode(Mode mode, uint64_t now) {
  if (!s_.web) return Result::Unsafe;
  if (s_.mode == mode && !s_.switching) return Result::OK;
  Stop("mode_changed", now);
  s_.mode = mode;
  s_.switching = true;
  return Result::OK;
}
Result ControlCore::RequestArm(uint32_t epoch, uint64_t now) {
  if (epoch != s_.epoch) return Result::Stale;
  if (!s_.web || !Fresh(now) || s_.fault || s_.switching || stop_pending_ ||
      await_stop_ack_)
    return Result::Unsafe;
  if (s_.mode == Mode::AI && !s_.ai_online) return Result::Unsafe;
  if (s_.authorized || arm_ != ArmPhase::None) return Result::Busy;
  if (s_.motion_state != 0) return Result::Unsafe;
  session_ = ++next_session_;
  if (!session_) session_ = ++next_session_;
  tx_seq_ = 0;
  have_status_seq_ = false;
  arm_ = ArmPhase::Hello;
  arm_until_ = now + 500000;
  s_.reason = "arming";
  return Result::OK;
}
Result ControlCore::RequestClear(uint32_t epoch, uint64_t now) {
  Tick(now);
  if (epoch != s_.epoch) return Result::Stale;
  if (!s_.web || !Fresh(now) || s_.authorized ||
      (s_.motion_state != 3 && !s_.fault)) return Result::Unsafe;
  if (arm_ != ArmPhase::None || s_.clearing) return Result::Busy;
  Stop("clear_requested", now);
  session_ = ++next_session_;
  if (!session_) session_ = ++next_session_;
  tx_seq_ = 0;
  have_status_seq_ = false;
  s_.clearing = true;
  arm_ = ArmPhase::WaitClearStop;
  arm_until_ = now + 1000000;
  return Result::OK;
}
void ControlCore::Tick(uint64_t now) {
  if (!challenge_next_ || challenge_epoch_ != s_.epoch ||
      now - last_challenge_ >= 50000) {
    ++challenge_next_;
    if (!challenge_next_) ++challenge_next_;
    challenges_[challenge_slot_++ % challenges_.size()] = {challenge_next_,
                                                           s_.epoch, now};
    s_.challenge = challenge_next_;
    challenge_epoch_ = s_.epoch;
    last_challenge_ = now;
  }
  if (!Fresh(now) && ((have_status_ && !status_loss_handled_) ||
                     s_.authorized || arm_ != ArmPhase::None)) {
    // A reboot can restart STATUS sequence even while already DISARMED.
    // Revoke/reset discovery once per outage, never flood STOP or auto-ARM.
    status_loss_handled_ = true;
    Stop("motion_stale", now);
    return;
  }
  if (arm_ != ArmPhase::None && now >= arm_until_) {
    Stop("arm_timeout", now);
    return;
  }
  if (!s_.authorized) return;
  if (s_.mode == Mode::Manual) {
    if (!s_.web || now - last_manual_ >= 150000) {
      Stop("manual_timeout", now);
      return;
    }
    if ((s_.v || s_.omega) && now - last_manual_ >= manual_ttl_) Target(0, 0);
  } else {
    if (!s_.ai_online || now >= grant_until_) {
      Stop(s_.ai_online ? "ai_grant_expired" : "ai_offline", now);
      return;
    }
    if (action_until_ && now >= action_until_) {
      Target(0, 0);
      action_until_ = 0;
      s_.reason = "action_complete";
    }
  }
}
Result ControlCore::ManualMove(uint32_t epoch, uint32_t challenge, uint32_t seq,
                               int v, int w, int ttl, bool deadman,
                               uint64_t now) {
  Tick(now);
  if (epoch != s_.epoch) return Result::Stale;
  if (s_.mode != Mode::Manual) return Result::WrongMode;
  if (!s_.web || !s_.authorized || !Fresh(now)) return Result::Unsafe;
  bool fresh_challenge = false;
  for (auto c : challenges_)
    if (c.id == challenge && c.epoch == epoch && now - c.at < 120000)
      fresh_challenge = true;
  if (!fresh_challenge) return Result::Stale;
  uint32_t delta = seq - last_web_seq_;
  if (have_web_seq_ && (!delta || delta >= 0x80000000u))
    return Result::BadSequence;
  if (std::abs(int64_t(v)) > cfg_.v_max ||
      std::abs(int64_t(w)) > cfg_.omega_max || ttl < 1 || ttl > 250 ||
      (!deadman && (v || w)))
    return Result::BadRange;
  have_web_seq_ = true;
  last_web_seq_ = seq;
  last_manual_ = now;
  manual_ttl_ = uint64_t(ttl) * 1000;
  Target(v, w);
  s_.reason = (v || w) ? "manual_move" : "neutral";
  return Result::OK;
}
Result ControlCore::VoiceMove(uint32_t epoch, int action, int pct, int duration,
                              uint64_t now) {
  Tick(now);
  if (epoch != s_.epoch) return Result::Stale;
  if (s_.mode != Mode::AI) return Result::WrongMode;
  if (!s_.authorized || !s_.ai_online || !Fresh(now)) return Result::Unsafe;
  if (action < 0 || action > 5 || pct < 0 || pct > 100 || duration < 100 ||
      duration > 3000)
    return Result::BadRange;
  int v = cfg_.v_max * pct / 100, w = cfg_.omega_max * pct / 100;
  switch (action) {
    case 0:
      Target(v, 0);
      break;
    case 1:
      Target(-v, 0);
      break;
    case 2:
      Target(v, w);
      break;
    case 3:
      Target(v, -w);
      break;
    case 4:
      Target(0, w);
      break;
    case 5:
      Target(0, -w);
      break;
  }
  action_until_ = now + uint64_t(duration) * 1000;
  s_.reason = "voice_move";
  return Result::OK;
}
void ControlCore::OnStatus(const bm::Frame& f, uint64_t now) {
  if (f.type != bm::Status || f.length != 17) return;
  uint8_t state = f.payload[5], flags = f.payload[16], result = f.payload[4];
  if (state > 3 || flags & 0xc0 || (result > 7 && result != 255)) return;
  // Expire authority before sequence/session admission. While fresh, the
  // original monotonic sequence and session checks below remain unchanged.
  Tick(now);
  // STOP revokes the peer's context; its exact ACK can use the previous or
  // zero session. No HELLO is emitted until that ACK, so a receive-buffer
  // flush on Motion's epoch change cannot swallow the new recovery HELLO.
  if ((s_.authorized || arm_ != ArmPhase::None) && f.session != session_ &&
      arm_ != ArmPhase::WaitClearStop)
    return;
  uint16_t delta = uint16_t(f.seq - last_status_seq_);
  if (have_status_seq_ && (!delta || delta >= 0x8000)) return;
  const bool rediscovered = !have_status_ || status_loss_handled_;
  have_status_ = have_status_seq_ = true;
  status_loss_handled_ = false;
  // The first STOP may have been sent while the peer was in ROM/UART init.
  // Confirm it once after rediscovery; subsequent STATUS never flood STOP.
  if (rediscovered && await_stop_ack_) stop_pending_ = true;
  last_status_ = now;
  last_status_seq_ = f.seq;
  s_.last_req = bm::U16(f.payload.data());
  s_.applied = bm::U16(f.payload.data() + 2);
  s_.result = result;
  s_.motion_state = state;
  s_.fault = bm::U16(f.payload.data() + 6);
  s_.flags = flags;
  s_.v_est = int16_t(bm::U16(f.payload.data() + 8));
  s_.omega_est = int16_t(bm::U16(f.payload.data() + 10));
  s_.battery = bm::U16(f.payload.data() + 12);
  s_.encoder_age = bm::U16(f.payload.data() + 14);
  if (state == 0 && !stop_pending_ && s_.last_req == stop_ack_seq_ &&
      result == 0) {
    await_stop_ack_ = false;
    s_.switching = false;
  }
  if (s_.clearing) {
    auto finished = [this] {
      arm_ = ArmPhase::None;
      s_.clearing = s_.authorized = s_.switching = false;
      await_stop_ack_ = false;
      s_.reason = "fault_cleared";
    };
    if (s_.last_req == expected_req_ && result != 7) {
      if (arm_ == ArmPhase::WaitClearStop) {
        if (result == 0 && state == 3) arm_ = ArmPhase::ClearHello;
        else if (result == 0 && state == 0 && !s_.fault) finished();
        else Stop("clear_rejected", now);
      } else if (arm_ == ArmPhase::WaitClearHello) {
        if (result == 0 && state == 3) arm_ = ArmPhase::Clear;
        else if (result == 0 && state == 0 && !s_.fault) finished();
        else Stop("clear_rejected", now);
      } else if (arm_ == ArmPhase::WaitClear) {
        if (result == 0 && state == 0 && !s_.fault) finished();
        else Stop("clear_rejected", now);
      }
    }
    return;
  }
  if (s_.fault || state == 3) {
    if (s_.authorized || arm_ != ArmPhase::None) Stop("motion_fault", now);
    return;
  }
  if ((arm_ == ArmPhase::WaitHello || arm_ == ArmPhase::WaitArm) &&
      s_.last_req == expected_req_ && result != 0 && result != 7) {
    Stop("arm_rejected", now);
    return;
  }
  if (arm_ == ArmPhase::WaitHello && f.session == session_ &&
      s_.last_req == expected_req_ && result == 0 && state == 0)
    arm_ = ArmPhase::Arm;
  else if (arm_ == ArmPhase::WaitArm && f.session == session_ &&
           s_.last_req == expected_req_ && result == 0 && state == 2) {
    arm_ = ArmPhase::None;
    s_.authorized = true;
    s_.reason = "armed";
    last_manual_ = now;
    grant_until_ = s_.mode == Mode::AI ? now + 300000000 : 0;
    Target(0, 0);
  } else if (s_.authorized && (state != 2 || (s_.last_req == tx_seq_ &&
                                              result != 0 && result != 255)))
    Stop("motion_rejected", now);
}
bool ControlCore::TakeTx(bm::Frame& f, uint64_t now) {
  Tick(now);
  f = {};
  if (stop_pending_) {
    f.type = bm::Stop;
    stop_pending_ = false;
  } else if (arm_ == ArmPhase::Hello) {
    f.type = bm::Hello;
    arm_ = ArmPhase::WaitHello;
  } else if (arm_ == ArmPhase::Arm) {
    f.type = bm::Arm;
    arm_ = ArmPhase::WaitArm;
  } else if (arm_ == ArmPhase::ClearHello) {
    f.type = bm::Hello;
    arm_ = ArmPhase::WaitClearHello;
  } else if (arm_ == ArmPhase::Clear) {
    f.type = bm::Clear;
    arm_ = ArmPhase::WaitClear;
  } else if (s_.authorized &&
             (dirty_ || (now - last_tx_ >= 50000 &&
                         (s_.mode == Mode::AI || (!s_.v && !s_.omega))))) {
    f.type = bm::Twist;
    f.length = 7;
    bm::Put16(f.payload.data(), uint16_t(s_.v));
    bm::Put16(f.payload.data() + 2, uint16_t(s_.omega));
    f.payload[4] = s_.mode == Mode::AI ? 1 : 2;
    bm::Put16(f.payload.data() + 5, 120);
    dirty_ = false;
  } else
    return false;
  f.session = session_;
  f.seq = ++tx_seq_;
  expected_req_ = f.seq;
  if (f.type == bm::Stop) stop_ack_seq_ = f.seq;
  last_tx_ = now;
  return true;
}
State ControlCore::GetState(uint64_t now) const {
  State out = s_;
  out.telemetry_age_ms =
      have_status_ ? int64_t((now - last_status_) / 1000) : -1;
  out.ai_remaining_ms =
      s_.authorized && grant_until_ > now ? (grant_until_ - now) / 1000 : 0;
  out.action_remaining_ms =
      s_.authorized && action_until_ > now ? (action_until_ - now) / 1000 : 0;
  return out;
}
}  // namespace awcar
