#include <cstdio>
#include <new>
#include <string>

#include "control_core.h"
#include "voice_gate.h"
#ifdef _WIN32
#define API extern "C" __declspec(dllexport)
#else
#define API extern "C"
#endif
struct Host {
  awcar::ControlCore core;
  awcar::bm::Parser parser;
  awcar::VoiceGate gate;
  awcar::VoiceTicket ticket;
};
API void* aw_new() { return new Host; }
API void aw_delete(void* p) { delete static_cast<Host*>(p); }
API int aw_command(void* p, int op, uint64_t now, int64_t a, int64_t b,
                   int64_t c, int64_t d, int64_t e, int64_t f, int64_t g) {
  auto& x = static_cast<Host*>(p)->core;
  switch (op) {
    case 0:
      x.Tick(now);
      break;
    case 1:
      x.WebConnect(now);
      break;
    case 2:
      x.WebDisconnect(now);
      break;
    case 3:
      x.SetAiOnline(a != 0, now);
      break;
    case 4:
      return int(x.SetMode(a ? awcar::Mode::AI : awcar::Mode::Manual, now));
    case 5:
      return int(x.RequestArm(uint32_t(a), now));
    case 6:
      x.Stop("user_stop", now);
      break;
    case 7:
      return int(x.ManualMove(uint32_t(a), uint32_t(b), uint32_t(c), int(d),
                              int(e), int(f), g != 0, now));
    case 8:
      return int(x.VoiceMove(uint32_t(a), int(b), int(c), int(d), now));
    default:
      return -1;
  }
  return 0;
}
API size_t aw_tx(void* p, uint64_t now, uint8_t* out) {
  awcar::bm::Frame f;
  return static_cast<Host*>(p)->core.TakeTx(f, now)
             ? awcar::bm::Encode(f, out, 32)
             : 0;
}
API int aw_gate(void* p, int op, uint64_t now, int id, const char* session) {
  auto& h = *static_cast<Host*>(p);
  h.gate.Epoch(h.core.Epoch());
  if (op == 0) return h.gate.Bind(session);
  if (op == 1) {
    h.gate.Stt(session, now);
    return 1;
  }
  if (op == 2) {
    h.ticket = h.gate.Capture(h.core.Epoch(), id, session, now);
    return h.ticket.valid;
  }
  if (op == 3) {
    if (!h.gate.Check(h.ticket, h.core.Epoch(), now)) return 0;
    h.gate.Consume(h.ticket);
    return 1;
  }
  return 0;
}
API void aw_rx(void* p, uint64_t now, const uint8_t* bytes, size_t size) {
  auto& x = *static_cast<Host*>(p);
  awcar::bm::Frame f;
  for (size_t i = 0; i < size; i++)
    if (x.parser.Feed(bytes[i], now, f)) x.core.OnStatus(f, now);
}
API const char* aw_state(void* p, uint64_t now) {
  static thread_local char b[1800];
  auto& h = *static_cast<Host*>(p);
  auto s = h.core.GetState(now);
  std::snprintf(
      b, sizeof(b),
      "{\"mode\":\"%s\",\"web\":%s,\"ai_online\":%s,\"authorized\":%s,"
      "\"switching\":%s,"
      "\"epoch\":%u,\"challenge\":%u,\"ai_remaining_ms\":%llu,\"action_"
      "remaining_ms\":%llu,\"v\":%d,\"omega\":%d,"
      "\"motion_state\":%d,\"fault_flags\":%u,\"last_req_seq\":%u,\"applied_"
      "seq\":%u,\"result_code\":%u,\"status_flags\":%u,"
      "\"v_est_mm_s\":%s,\"omega_est_mrad_s\":%s,\"battery_mv\":%s,\"encoder_"
      "age_ms\":%d,\"telemetry_age_ms\":%lld,"
      "\"reason\":\"%s\",\"rx_errors\":%u}",
      s.mode == awcar::Mode::AI ? "AI" : "Manual", s.web ? "true" : "false",
      s.ai_online ? "true" : "false", s.authorized ? "true" : "false",
      s.switching ? "true" : "false", s.epoch, s.challenge,
      static_cast<unsigned long long>(s.ai_remaining_ms),
      static_cast<unsigned long long>(s.action_remaining_ms), s.v, s.omega,
      s.motion_state, s.fault, s.last_req, s.applied, s.result, s.flags,
      (s.flags & 1) ? std::to_string(s.v_est).c_str() : "null",
      (s.flags & 2) ? std::to_string(s.omega_est).c_str() : "null",
      (s.flags & 4) ? std::to_string(s.battery).c_str() : "null", s.encoder_age,
      static_cast<long long>(s.telemetry_age_ms), s.reason, h.parser.errors);
  return b;
}
