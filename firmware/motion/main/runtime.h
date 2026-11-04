#pragma once
#include <array>
#include <atomic>

#include "esp_attr.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "motion_core.h"
#include "status_indicator.h"

namespace awcar::motion {
struct Snapshot {
  View view;
  Config config;
  uint32_t rx_errors = 0, queue_drops = 0, log_drops = 0, tx_drops = 0;
  uint32_t latency_count = 0, p95_us = 0, p99_us = 0, max_us = 0;
  uint32_t heap_free = 0, heap_min = 0, control_stack = 0;
  indicator::State indicator{};
  bool led_known = false;
  uint32_t led_writes = 0, led_errors = 0, led_max_us = 0;
};
class Runtime {
 public:
  static Runtime& Get();
  void Start();
  Snapshot ReadSnapshot();
  bool Configure(const Config& config);
  bool BeginStorage(Config& config);
  bool EndStorage(const Config& config);
  void Stop();
  void PrintUartDiagnostics();
  static uint64_t Now();
  void Inhibit(bool hard);
  void NotifyFromIsr(BaseType_t* wake);
  void GpioInterrupt();
  void TimerInterrupt();

 private:
  Runtime();
  enum class EventType : uint8_t { Brain, Fpga };
  struct Event {
    EventType type;
    uint32_t epoch, generation;
    uint64_t at;
    bm::Frame brain;
    fpga::Frame fpga;
  };
  struct Packet {
    std::array<uint8_t, 64> bytes{};
    size_t size = 0;
    uint32_t epoch = 0, generation = 0;
    uint64_t at = 0, brain_at = 0;
    uint8_t type = 0;
  };
  struct ConfigRequest {
    Config config;
    int operation;
    uint32_t id = 0;
  };
  struct ConfigReply {
    Config config;
    bool accepted;
    uint32_t id;
  };
  struct LogEvent {
    uint64_t at;
    uint16_t fault;
    uint8_t state, link, drive;
  };
  MotionCore core_;
  TaskHandle_t control_ = nullptr;
  QueueHandle_t events_ = nullptr, tx_[2]{}, config_requests_ = nullptr,
                config_replies_ = nullptr;
  QueueHandle_t logs_ = nullptr;
  std::atomic<uint32_t> heartbeat_{0}, epoch_{1}, generation_{1};
  std::atomic<uint32_t> fault_pending_{0}, rx_errors_{0}, queue_drops_{0},
      tx_drops_{0};
  std::atomic<uint32_t> log_drops_{0};
  std::atomic<bool> driver_live_{false}, stop_pending_{false},
      local_stop_{false};
  std::atomic<unsigned> uart_ready_{0};
  std::atomic<uint32_t> uart_bytes_[2]{}, uart_frames_[2]{},
      uart_hw_errors_[2]{}, uart_parse_errors_[2]{}, uart_tx_frames_[2]{};
  portMUX_TYPE snapshot_mux_ = portMUX_INITIALIZER_UNLOCKED;
  portMUX_TYPE stop_mux_ = portMUX_INITIALIZER_UNLOCKED;
  portMUX_TYPE driver_mux_ = portMUX_INITIALIZER_UNLOCKED;
  bm::Frame stop_frame_{};
  Snapshot snapshot_{};
  bool storage_busy_ = false;
  uint32_t config_id_ = 0;
  std::array<uint32_t, 128> latency_{};
  uint32_t latency_count_ = 0, latency_max_ = 0;
  uint64_t brain_at_ = 0;
  void ControlTask();
  void ReceiveTask(int index);
  void TransmitTask();
  void StatsTask();
  void Wake();
  void Submit(const Event& event);
  void Publish(uint64_t now);
  bool ExchangeConfig(ConfigRequest request, ConfigReply& reply);
};
void ConsoleTask(void*);
bool LoadConfig(Config& config);
bool SaveConfig(const Config& config);
}  // namespace awcar::motion
