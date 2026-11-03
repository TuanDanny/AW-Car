#include <fcntl.h>
#include <unistd.h>

#include <array>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "board_config.h"
#include "nvs.h"
#include "runtime.h"

namespace awcar::motion {
namespace {
struct Field {
  const char* key;
  uint32_t Config::* member;
};
constexpr Field fields[] = {{"circumference_um", &Config::circumference_um},
                            {"pulses_per_rev", &Config::pulses_per_rev},
                            {"track_mm", &Config::track_mm},
                            {"full_speed_mm_s", &Config::full_speed_mm_s},
                            {"max_v", &Config::max_v},
                            {"max_omega", &Config::max_omega},
                            {"kick_ms", &Config::kick_ms},
                            {"rest_ms", &Config::rest_ms},
                            {"reverse_ms", &Config::reverse_ms},
                            {"slow_mm_s", &Config::slow_mm_s},
                            {"duty_limit", &Config::duty_limit}};
struct Stored {
  uint32_t magic = 0x41574d31, version = 1;
  std::array<uint32_t, 12> values{};
  uint16_t crc = 0;
};
static_assert(offsetof(Stored, crc) == 56);
void PrintConfig(const Config& cfg) {
  std::printf("CONFIG validated=%u driver_build=%s", unsigned(cfg.validated),
              board::allow_driver ? "ENABLED" : "LOCKED");
  for (const auto& f : fields)
    std::printf(" %s=%lu", f.key, static_cast<unsigned long>(cfg.*(f.member)));
  std::printf("\n");
}
void PrintStatus(Runtime& runtime) {
  const auto s = runtime.ReadSnapshot();
  const auto& v = s.view;
  char p95[16] = "null", p99[16] = "null", maximum[16] = "null";
  if (s.latency_count) {
    std::snprintf(p95, sizeof(p95), "%lu",
                  static_cast<unsigned long>(s.p95_us));
    std::snprintf(p99, sizeof(p99), "%lu",
                  static_cast<unsigned long>(s.p99_us));
    std::snprintf(maximum, sizeof(maximum), "%lu",
                  static_cast<unsigned long>(s.max_us));
  }
  std::printf(
      "STATUS "
      "{\"state\":%u,\"fault\":%u,\"fpga_fault\":%u,\"link_phase\":%u,"
      "\"epoch\":%lu,"
      "\"driver\":%s,\"logical_permit\":%s,\"driver_gpio\":%d,\"logical_gpio\":"
      "%d,"
      "\"configured\":%s,\"fresh\":%s,\"lease\":%s,\"left_duty\":%u,\"right_"
      "duty\":%u,"
      "\"direction\":%u,\"drive_phase\":%u,\"left_speed_abs\":%lu,\"right_"
      "speed_abs\":%lu,"
      "\"snapshot_seq\":%u,\"fpga_state\":%u,\"left_count\":%lu,\"right_"
      "count\":%lu,"
      "\"speeds_valid\":%s,\"v_est\":null,\"omega_est\":null,\"battery_mv\":"
      "null,"
      "\"rx_errors\":%lu,\"queue_drops\":%lu,\"tx_drops\":%lu,\"log_drops\":%"
      "lu,"
      "\"latency_samples\":%lu,\"rx_to_uart_p95_us\":%s,\"rx_to_uart_p99_us\":"
      "%s,"
      "\"rx_to_uart_max_us\":%s,\"heap_free\":%lu,\"heap_min\":%lu,\"control_"
      "stack\":%lu}\n",
      unsigned(v.state), v.fault, v.fpga_fault, unsigned(v.link_phase),
      static_cast<unsigned long>(v.epoch), v.driver_permit ? "true" : "false",
      v.motion_permit ? "true" : "false", gpio_get_level(board::driver),
      gpio_get_level(board::logical), v.configured ? "true" : "false",
      v.fresh ? "true" : "false", v.lease ? "true" : "false", v.drive.left,
      v.drive.right, v.drive.direction, unsigned(v.drive.phase),
      static_cast<unsigned long>(v.drive.left_speed_abs),
      static_cast<unsigned long>(v.drive.right_speed_abs), v.snapshot_seq,
      v.fpga_state, static_cast<unsigned long>(v.left_count),
      static_cast<unsigned long>(v.right_count),
      v.drive.speeds_valid ? "true" : "false",
      static_cast<unsigned long>(s.rx_errors),
      static_cast<unsigned long>(s.queue_drops),
      static_cast<unsigned long>(s.tx_drops),
      static_cast<unsigned long>(s.log_drops),
      static_cast<unsigned long>(s.latency_count), p95, p99, maximum,
      static_cast<unsigned long>(s.heap_free),
      static_cast<unsigned long>(s.heap_min),
      static_cast<unsigned long>(s.control_stack));
}
void Execute(Runtime& runtime, const char* line) {
  if (std::strcmp(line, "help") == 0) {
    std::printf(
        "help | status | config | set KEY UINT | save | load | defaults | "
        "stop\n"
        "Settings/storage require DISARMED. No USB ARM/MOVE/CLEAR command.\n"
        "validated=1 also requires a hardware-enabled build and verified "
        "gate.\n");
  } else if (std::strcmp(line, "status") == 0)
    PrintStatus(runtime);
  else if (std::strcmp(line, "config") == 0)
    PrintConfig(runtime.ReadSnapshot().config);
  else if (std::strcmp(line, "stop") == 0) {
    runtime.Stop();
    std::printf("OK STOP requested\n");
  } else if (std::strcmp(line, "save") == 0 || std::strcmp(line, "load") == 0) {
    Config cfg;
    if (!runtime.BeginStorage(cfg)) {
      std::printf("ERROR storage requires DISARMED and idle link\n");
      return;
    }
    const bool saving = std::strcmp(line, "save") == 0;
    const bool ok = saving ? SaveConfig(cfg) : LoadConfig(cfg);
    cfg.validated = cfg.validated && board::allow_driver;
    const bool restored = runtime.EndStorage(cfg);
    std::printf("%s %s\n", ok && restored ? "OK" : "ERROR",
                saving ? "save" : "load");
  } else if (std::strcmp(line, "defaults") == 0) {
    std::printf("%s defaults\n", runtime.Configure(Config{}) ? "OK" : "ERROR");
  } else if (std::strncmp(line, "set ", 4) == 0) {
    char key[40], value[32], extra[2];
    if (std::sscanf(line + 4, "%39s %31s %1s", key, value, extra) != 2 ||
        value[0] == '-' || value[0] == '+') {
      std::printf("ERROR set KEY unsigned_integer\n");
      return;
    }
    errno = 0;
    char* end;
    const unsigned long long parsed = std::strtoull(value, &end, 10);
    if (errno || *end || parsed > UINT32_MAX) {
      std::printf("ERROR integer range\n");
      return;
    }
    Config cfg = runtime.ReadSnapshot().config;
    bool found = false;
    if (std::strcmp(key, "validated") == 0 && parsed <= 1) {
      cfg.validated = parsed == 1;
      found = true;
    } else
      for (const auto& f : fields)
        if (std::strcmp(key, f.key) == 0) {
          cfg.*(f.member) = uint32_t(parsed);
          found = true;
          break;
        }
    std::printf("%s set %s\n", found && runtime.Configure(cfg) ? "OK" : "ERROR",
                key);
  } else if (*line)
    std::printf("ERROR unknown command; type help\n");
}
}  // namespace
bool LoadConfig(Config& config) {
  nvs_handle_t nvs;
  if (nvs_open_from_partition("motioncfg", "motion", NVS_READONLY, &nvs) !=
      ESP_OK)
    return false;
  Stored stored{};
  size_t size = sizeof(stored);
  const auto result = nvs_get_blob(nvs, "config", &stored, &size);
  nvs_close(nvs);
  if (result != ESP_OK || size != sizeof(stored) ||
      stored.magic != 0x41574d31 || stored.version != 1 ||
      bm::Crc(reinterpret_cast<const uint8_t*>(&stored),
              offsetof(Stored, crc)) != stored.crc ||
      stored.values[11] > 1)
    return false;
  Config cfg;
  for (size_t i = 0; i < std::size(fields); ++i)
    cfg.*(fields[i].member) = stored.values[i];
  cfg.validated = stored.values[11] == 1;
  if (!cfg.Valid()) return false;
  config = cfg;
  return true;
}
bool SaveConfig(const Config& config) {
  if (!config.Valid()) return false;
  Stored stored{};
  for (size_t i = 0; i < std::size(fields); ++i)
    stored.values[i] = config.*(fields[i].member);
  stored.values[11] = config.validated ? 1 : 0;
  stored.crc =
      bm::Crc(reinterpret_cast<const uint8_t*>(&stored), offsetof(Stored, crc));
  nvs_handle_t nvs;
  if (nvs_open_from_partition("motioncfg", "motion", NVS_READWRITE, &nvs) !=
      ESP_OK)
    return false;
  const bool ok =
      nvs_set_blob(nvs, "config", &stored, sizeof(stored)) == ESP_OK &&
      nvs_commit(nvs) == ESP_OK;
  nvs_close(nvs);
  return ok;
}
void ConsoleTask(void* pointer) {
  auto& runtime = *static_cast<Runtime*>(pointer);
  const int flags = fcntl(STDIN_FILENO, F_GETFL, 0);
  fcntl(STDIN_FILENO, F_SETFL, flags | O_NONBLOCK);
  std::printf(
      "Console ready; type help. Motor hardware remains locked by default.\n");
  char line[128]{};
  size_t size = 0;
  bool overflow = false;
  for (;;) {
    char c;
    while (read(STDIN_FILENO, &c, 1) == 1) {
      if (c == '\n' || c == '\r') {
        if (overflow)
          std::printf("ERROR line too long\n");
        else {
          line[size] = 0;
          Execute(runtime, line);
        }
        size = 0;
        overflow = false;
      } else if (c == '\b' || c == 127) {
        if (size) --size;
      } else if (c >= 32 && c < 127) {
        if (size + 1 < sizeof(line))
          line[size++] = c;
        else
          overflow = true;
      }
    }
    vTaskDelay(pdMS_TO_TICKS(10));
  }
}
}  // namespace awcar::motion
