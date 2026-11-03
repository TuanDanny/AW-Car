#include <cstdint>
#include <cstdio>
#include <string_view>

#include "motion_core.h"
using awcar::motion::MotionCore;
struct Host {
  MotionCore core;
  awcar::bm::Parser brain;
  awcar::fpga::Parser fpga;
  char view[1600]{};
  explicit Host(bool validated)
      : core(
            [validated] {
              awcar::motion::Config cfg;
              cfg.validated = validated;
              return cfg;
            }(),
            0x17346251) {}
};
#ifdef _WIN32
#define API extern "C" __declspec(dllexport)
#else
#define API extern "C"
#endif
API void* motion_new(int validated) { return new Host(validated != 0); }
API void motion_delete(void* p) { delete static_cast<Host*>(p); }
API void motion_tick(void* p, uint64_t now, unsigned inputs) {
  auto& core = static_cast<Host*>(p)->core;
  core.InputsNow(
      {bool(inputs & 1), bool(inputs & 2), bool(inputs & 4), bool(inputs & 8)},
      now);
  core.Tick(now);
}
API void motion_receive(void* p, int port, const uint8_t* bytes, size_t n,
                        uint64_t now) {
  auto& h = *static_cast<Host*>(p);
  for (size_t i = 0; i < n; ++i) {
    if (port == 1) {
      awcar::bm::Frame f;
      if (h.brain.Feed(bytes[i], now, f)) h.core.OnBrain(f, now);
    } else {
      awcar::fpga::Frame f;
      if (h.fpga.Feed(bytes[i], now, f)) h.core.OnFpga(f, now);
    }
  }
}
API size_t motion_transmit(void* p, int port, uint64_t now, uint8_t* bytes) {
  auto& h = *static_cast<Host*>(p);
  if (port == 1) {
    awcar::bm::Frame f;
    return h.core.TakeBrainTx(f, now) ? awcar::bm::Encode(f, bytes, 64) : 0;
  }
  awcar::fpga::Frame f;
  return h.core.TakeFpgaTx(f, now) ? awcar::fpga::Encode(f, bytes, 64) : 0;
}
API void motion_stop(void* p, uint64_t now) {
  static_cast<Host*>(p)->core.LocalStop(now);
}
API void motion_fault(void* p, unsigned fault, uint64_t now) {
  static_cast<Host*>(p)->core.RuntimeFault(uint16_t(fault), now);
}
API size_t motion_codec_echo(int version, const uint8_t* input, size_t size,
                             uint8_t* out) {
  awcar::bm::Parser brain;
  awcar::fpga::Parser fpga;
  awcar::bm::Frame b;
  awcar::fpga::Frame f;
  for (size_t i = 0; i < size; ++i) {
    if (version == 1 && brain.Feed(input[i], i * 100, b))
      return awcar::bm::Encode(b, out, 64);
    if (version == 2 && fpga.Feed(input[i], i * 100, f))
      return awcar::fpga::Encode(f, out, 64);
  }
  return 0;
}
API size_t motion_codec_command(uint32_t session, uint16_t seq, uint8_t dir,
                                uint16_t left, uint16_t right, uint8_t* out) {
  return awcar::fpga::Encode(
      awcar::fpga::CommandFrame(session, seq, dir, left, right), out, 64);
}
API int motion_config(void* p, const char* key, uint32_t value, uint64_t now) {
  auto& c = static_cast<Host*>(p)->core;
  auto cfg = c.Configuration();
  const struct {
    const char* key;
    uint32_t awcar::motion::Config::* member;
  } fields[] = {
      {"circumference_um", &awcar::motion::Config::circumference_um},
      {"pulses_per_rev", &awcar::motion::Config::pulses_per_rev},
      {"track_mm", &awcar::motion::Config::track_mm},
      {"full_speed_mm_s", &awcar::motion::Config::full_speed_mm_s},
      {"max_v", &awcar::motion::Config::max_v},
      {"max_omega", &awcar::motion::Config::max_omega},
      {"kick_ms", &awcar::motion::Config::kick_ms},
      {"rest_ms", &awcar::motion::Config::rest_ms},
      {"reverse_ms", &awcar::motion::Config::reverse_ms},
      {"slow_mm_s", &awcar::motion::Config::slow_mm_s},
      {"duty_limit", &awcar::motion::Config::duty_limit},
  };
  if (std::string_view(key) == "validated")
    cfg.validated = value == 1;
  else {
    bool found = false;
    for (const auto& f : fields)
      if (std::string_view(f.key) == key) {
        cfg.*(f.member) = value;
        found = true;
        break;
      }
    if (!found) return 0;
  }
  return c.Configure(cfg, now);
}
API const char* motion_view(void* p, uint64_t now) {
  auto& h = *static_cast<Host*>(p);
  const auto s = h.core.GetView(now);
  std::snprintf(
      h.view, sizeof(h.view),
      "{\"state\":%u,\"fault\":%u,\"fpga_fault\":%u,\"last_req\":%u,"
      "\"applied\":%u,"
      "\"result\":%u,\"epoch\":%u,\"driver\":%s,\"permit\":%s,\"req\":%s,"
      "\"configured\":%s,\"lease\":%s,\"fresh\":%s,\"link_phase\":%u,"
      "\"age\":%llu,\"left\":%u,\"right\":%u,\"dir\":%u,\"phase\":%u,"
      "\"left_target\":%d,\"right_target\":%d,\"left_speed_abs\":%u,\"right_"
      "speed_abs\":%u,"
      "\"speeds_valid\":%s,\"brain_errors\":%u,\"fpga_errors\":%u}",
      unsigned(s.state), s.fault, s.fpga_fault, s.last_req, s.applied,
      unsigned(s.result), s.epoch, s.driver_permit ? "true" : "false",
      s.motion_permit ? "true" : "false", s.recovery_req ? "true" : "false",
      s.configured ? "true" : "false", s.lease ? "true" : "false",
      s.fresh ? "true" : "false", unsigned(s.link_phase),
      static_cast<unsigned long long>(s.snapshot_age_us), s.drive.left,
      s.drive.right, s.drive.direction, unsigned(s.drive.phase),
      s.drive.left_target, s.drive.right_target, s.drive.left_speed_abs,
      s.drive.right_speed_abs, s.drive.speeds_valid ? "true" : "false",
      h.brain.errors, h.fpga.errors);
  return h.view;
}
