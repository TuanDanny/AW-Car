#pragma once
#include <algorithm>
#include <cstdint>
namespace awcar {
enum class StaPhase {
  NoCredentials,
  Waiting,
  Connecting,
  Dhcp,
  Online,
  Backoff,
  Cooldown
};
enum class StaFailure { MissingAp, Authentication, Transient };
// Worker-owned, monotonic milliseconds. Cloud failure is deliberately not an
// input.
class ReconnectPolicy {
 public:
  StaPhase phase = StaPhase::NoCredentials;
  uint32_t attempts = 0, failures = 0, burst = 0;
  uint64_t due = 0, deadline = 0, online_since = 0, last_attempt = 0;
  bool attempted_since_config = false;
  StaFailure last_failure = StaFailure::Transient;
  void Configure(bool saved, uint64_t now) {
    phase = saved ? StaPhase::Waiting : StaPhase::NoCredentials;
    burst = 0;
    attempted_since_config = false;
    last_failure = StaFailure::Transient;
    due = now;
    deadline = 0;
  }
  uint64_t NextAttempt(bool ap_client = false) const {
    return ap_client && attempted_since_config &&
                   last_failure == StaFailure::MissingAp
               ? std::max(due, last_attempt + 60000)
               : due;
  }
  bool StartDue(uint64_t now, bool ap_client = false) {
    if ((phase != StaPhase::Waiting && phase != StaPhase::Backoff &&
         phase != StaPhase::Cooldown) ||
        now < NextAttempt(ap_client))
      return false;
    if (phase == StaPhase::Cooldown) burst = 0;
    phase = StaPhase::Connecting;
    ++attempts;
    last_attempt = now;
    attempted_since_config = true;
    deadline = now + 15000;
    return true;
  }
  void Associated(uint64_t now) {
    if (phase == StaPhase::Connecting || phase == StaPhase::Online) {
      phase = StaPhase::Dhcp;
      deadline = now + 15000;
    }
  }
  bool GotIp(uint64_t now) {
    if (phase != StaPhase::Connecting && phase != StaPhase::Dhcp) return false;
    phase = StaPhase::Online;
    online_since = now;
    deadline = 0;
    return true;
  }
  void Failed(StaFailure reason, uint64_t now) {
    if (phase == StaPhase::NoCredentials) return;
    if (phase == StaPhase::Online && now - online_since >= 30000) burst = 0;
    ++failures;
    last_failure = reason;
    ++burst;
    deadline = 0;
    const bool cool = burst >= 3 || reason == StaFailure::Authentication;
    phase = cool ? StaPhase::Cooldown : StaPhase::Backoff;
    due = now + (cool ? (reason == StaFailure::Authentication ? 300000 : 60000)
                      : (1000u << std::min<uint32_t>(burst - 1, 4)));
  }
  bool TimedOut(uint64_t now) const {
    return (phase == StaPhase::Connecting || phase == StaPhase::Dhcp) &&
           now >= deadline;
  }
  static const char* Name(StaPhase p) {
    switch (p) {
      case StaPhase::NoCredentials:
        return "no_credentials";
      case StaPhase::Waiting:
        return "waiting";
      case StaPhase::Connecting:
        return "connecting";
      case StaPhase::Dhcp:
        return "dhcp";
      case StaPhase::Online:
        return "online";
      case StaPhase::Backoff:
        return "backoff";
      case StaPhase::Cooldown:
        return "cooldown";
    }
    return "unknown";
  }
};
}  // namespace awcar
