#include "runtime.h"

#include <algorithm>
#include <cstdio>

#include "board_config.h"
#include "driver/gptimer.h"
#include "esp_heap_caps.h"
#include "esp_intr_alloc.h"
#include "esp_random.h"
#include "esp_timer.h"
#include "nvs_flash.h"
#include "status_led.h"

namespace awcar::motion {
static_assert(std::atomic<uint32_t>::is_always_lock_free);
Runtime::Runtime() : core_(Config{}, esp_random()) {}
Runtime& Runtime::Get() {
  static Runtime runtime;
  return runtime;
}
uint64_t Runtime::Now() { return uint64_t(esp_timer_get_time()); }
void IRAM_ATTR Runtime::Inhibit(bool hard) {
  portENTER_CRITICAL_SAFE(&driver_mux_);
  gpio_set_level(board::driver, 0);
  driver_live_.store(false, std::memory_order_relaxed);
  if (hard) gpio_set_level(board::logical, 0);
  portEXIT_CRITICAL_SAFE(&driver_mux_);
}
void IRAM_ATTR Runtime::NotifyFromIsr(BaseType_t* wake) {
  if (control_) vTaskNotifyGiveFromISR(control_, wake);
}
void IRAM_ATTR Runtime::GpioInterrupt() {
  if (!gpio_get_level(board::safety) || !gpio_get_level(board::gate)) {
    if (driver_live_.load(std::memory_order_relaxed)) {
      fault_pending_.fetch_or(Gate, std::memory_order_relaxed);
      Inhibit(true);
    }
  }
  if (!gpio_get_level(board::fpga_permit) &&
      driver_live_.load(std::memory_order_relaxed)) {
    fault_pending_.fetch_or(FpgaStale, std::memory_order_relaxed);
    Inhibit(true);
  }
  if (!gpio_get_level(board::boot)) {
    local_stop_.store(true, std::memory_order_relaxed);
    Inhibit(false);
  }
  BaseType_t wake = pdFALSE;
  NotifyFromIsr(&wake);
  if (wake) portYIELD_FROM_ISR();
}
void IRAM_ATTR Runtime::TimerInterrupt() {
  const uint32_t now = uint32_t(esp_timer_get_time());
  if (driver_live_.load(std::memory_order_relaxed) &&
      uint32_t(now - heartbeat_.load(std::memory_order_relaxed)) >= 20000) {
    fault_pending_.fetch_or(Internal, std::memory_order_relaxed);
    Inhibit(true);
  }
}
void Runtime::Wake() {
  if (control_) xTaskNotifyGive(control_);
}
void Runtime::Stop() {
  local_stop_ = true;
  Inhibit(false);
  Wake();
}
static void IRAM_ATTR GpioCallback(void* p) {
  static_cast<Runtime*>(p)->GpioInterrupt();
}
static bool IRAM_ATTR TimerCallback(gptimer_handle_t,
                                    const gptimer_alarm_event_data_t*,
                                    void* p) {
  auto* self = static_cast<Runtime*>(p);
  self->TimerInterrupt();
  BaseType_t wake = pdFALSE;
  self->NotifyFromIsr(&wake);
  return wake == pdTRUE;
}
void Runtime::Start() {
  const int pins[] = {board::logical,  board::driver,      board::req,
                      board::ack,      board::fpga_permit, board::safety,
                      board::gate,     board::boot,        board::brain_tx,
                      board::brain_rx, board::fpga_tx,     board::fpga_rx,
                      board::status_led};
  for (size_t i = 0; i < std::size(pins); ++i) {
    ESP_ERROR_CHECK(GPIO_IS_VALID_GPIO(pins[i]) ? ESP_OK : ESP_ERR_INVALID_ARG);
    // UART0 console and module flash/PSRAM/USB/strap pins are not reassigned.
    ESP_ERROR_CHECK((pins[i] != 3 && pins[i] != 19 && pins[i] != 20 &&
                     !(pins[i] >= 26 && pins[i] <= 37) && pins[i] != 43 &&
                     pins[i] != 44 && pins[i] != 45 && pins[i] != 46)
                        ? ESP_OK
                        : ESP_ERR_INVALID_ARG);
    for (size_t j = 0; j < i; ++j)
      ESP_ERROR_CHECK(pins[i] != pins[j] ? ESP_OK : ESP_ERR_INVALID_ARG);
  }
  for (gpio_num_t pin : {board::logical, board::driver, board::req}) {
    ESP_ERROR_CHECK(GPIO_IS_VALID_OUTPUT_GPIO(pin) ? ESP_OK
                                                   : ESP_ERR_INVALID_ARG);
    gpio_set_level(pin, 0);
    gpio_set_direction(pin, GPIO_MODE_INPUT_OUTPUT);
    gpio_set_level(pin, 0);
  }
  for (gpio_num_t pin :
       {board::ack, board::fpga_permit, board::safety, board::gate}) {
    gpio_set_direction(pin, GPIO_MODE_INPUT);
    gpio_set_pull_mode(pin, GPIO_PULLDOWN_ONLY);
    gpio_set_intr_type(pin, GPIO_INTR_ANYEDGE);
  }
  gpio_set_direction(board::boot, GPIO_MODE_INPUT);
  gpio_set_pull_mode(board::boot, GPIO_PULLUP_ONLY);
  gpio_set_intr_type(board::boot, GPIO_INTR_NEGEDGE);
  auto nvs_result = nvs_flash_init_partition("motioncfg");
  if (nvs_result == ESP_ERR_NVS_NO_FREE_PAGES ||
      nvs_result == ESP_ERR_NVS_NEW_VERSION_FOUND) {
    // Only this firmware's dedicated partition, never unrelated NVS/flash.
    ESP_ERROR_CHECK(nvs_flash_erase_partition("motioncfg"));
    nvs_result = nvs_flash_init_partition("motioncfg");
  }
  Config cfg;
  if (nvs_result == ESP_OK) LoadConfig(cfg);
  cfg.validated = cfg.validated && board::allow_driver;
  ESP_ERROR_CHECK(core_.Configure(cfg, Now()) ? ESP_OK : ESP_ERR_INVALID_ARG);
  static StaticQueue_t event_meta, tx_meta[2], request_meta, reply_meta,
      log_meta;
  static uint8_t event_storage[sizeof(Event) * 16],
      tx_storage[2][sizeof(Packet)];
  static uint8_t request_storage[sizeof(ConfigRequest)],
      reply_storage[sizeof(ConfigReply)];
  static uint8_t log_storage[sizeof(LogEvent) * 32];
  events_ = xQueueCreateStatic(16, sizeof(Event), event_storage, &event_meta);
  for (int i = 0; i < 2; ++i)
    tx_[i] = xQueueCreateStatic(1, sizeof(Packet), tx_storage[i], &tx_meta[i]);
  config_requests_ = xQueueCreateStatic(1, sizeof(ConfigRequest),
                                        request_storage, &request_meta);
  config_replies_ =
      xQueueCreateStatic(1, sizeof(ConfigReply), reply_storage, &reply_meta);
  logs_ = xQueueCreateStatic(32, sizeof(LogEvent), log_storage, &log_meta);
  auto task = [](TaskFunction_t function, const char* name, uint32_t stack,
                 void* arg, UBaseType_t priority, TaskHandle_t* handle,
                 BaseType_t cpu) {
    ESP_ERROR_CHECK(xTaskCreatePinnedToCore(function, name, stack, arg,
                                            priority, handle, cpu) == pdPASS
                        ? ESP_OK
                        : ESP_ERR_NO_MEM);
  };
  heartbeat_ = uint32_t(Now());
  task([](void* p) { static_cast<Runtime*>(p)->ControlTask(); },
       "motion_control", 6144, this, 20, &control_, 1);
  ESP_ERROR_CHECK(gpio_install_isr_service(ESP_INTR_FLAG_IRAM));
  for (auto pin : {board::ack, board::fpga_permit, board::safety, board::gate,
                   board::boot})
    ESP_ERROR_CHECK(gpio_isr_handler_add(pin, GpioCallback, this));
  gptimer_handle_t timer;
  gptimer_config_t timer_cfg{};
  timer_cfg.clk_src = GPTIMER_CLK_SRC_DEFAULT;
  timer_cfg.direction = GPTIMER_COUNT_UP;
  timer_cfg.resolution_hz = 1000000;
  ESP_ERROR_CHECK(gptimer_new_timer(&timer_cfg, &timer));
  gptimer_event_callbacks_t callbacks{};
  callbacks.on_alarm = TimerCallback;
  ESP_ERROR_CHECK(gptimer_register_event_callbacks(timer, &callbacks, this));
  gptimer_alarm_config_t alarm{};
  alarm.alarm_count = 1000;
  alarm.reload_count = 0;
  alarm.flags.auto_reload_on_alarm = true;
  ESP_ERROR_CHECK(gptimer_set_alarm_action(timer, &alarm));
  ESP_ERROR_CHECK(gptimer_enable(timer));
  ESP_ERROR_CHECK(gptimer_start(timer));
  task([](void*) { Runtime::Get().ReceiveTask(0); }, "brain_rx", 4096, nullptr,
       18, nullptr, 0);
  task([](void*) { Runtime::Get().ReceiveTask(1); }, "fpga_rx", 4096, nullptr,
       18, nullptr, 0);
  task([](void* p) { static_cast<Runtime*>(p)->TransmitTask(); }, "motion_tx",
       4096, this, 19, nullptr, 1);
  task(ConsoleTask, "motion_console", 6144, this, 3, nullptr, 0);
  task([](void* p) { static_cast<Runtime*>(p)->StatsTask(); }, "motion_stats",
       4096, this, 2, nullptr, 0);
  std::printf("\nAW-CAR MOTION 0.1.0; physical_driver_build=%s; WiFi/BLE=OFF\n",
              board::allow_driver ? "ENABLED" : "LOCKED");
  std::printf("UART1 Brain TX=%d RX=%d; UART2 FPGA TX=%d RX=%d; 115200 8N1\n",
              board::brain_tx, board::brain_rx, board::fpga_tx, board::fpga_rx);
  std::printf(
      "DriverPermit=%d LogicalPermit=%d Req=%d Ack=%d FpgaPermit=%d Safety=%d "
      "Gate=%d\n",
      board::driver, board::logical, board::req, board::ack, board::fpga_permit,
      board::safety, board::gate);
}
void Runtime::Submit(const Event& event) {
  if (xQueueSend(events_, &event, 0) != pdTRUE) {
    ++queue_drops_;
    fault_pending_.fetch_or(Internal);
    Inhibit(true);
  }
  Wake();
}
void Runtime::ReceiveTask(int index) {
  const uart_port_t port = index == 0 ? UART_NUM_1 : UART_NUM_2;
  uart_config_t cfg{};
  cfg.baud_rate = 115200;
  cfg.data_bits = UART_DATA_8_BITS;
  cfg.parity = UART_PARITY_DISABLE;
  cfg.stop_bits = UART_STOP_BITS_1;
  cfg.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
  cfg.source_clk = UART_SCLK_DEFAULT;
  ESP_ERROR_CHECK(uart_param_config(port, &cfg));
  ESP_ERROR_CHECK(uart_set_pin(port,
                               index == 0 ? board::brain_tx : board::fpga_tx,
                               index == 0 ? board::brain_rx : board::fpga_rx,
                               UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
  ESP_ERROR_CHECK(gpio_set_pull_mode(
      gpio_num_t(index == 0 ? board::brain_rx : board::fpga_rx),
      GPIO_PULLUP_ONLY));
  QueueHandle_t uart_events;
  ESP_ERROR_CHECK(uart_driver_install(port, 256, 0, 16, &uart_events, 0));
  ESP_ERROR_CHECK(uart_set_rx_full_threshold(port, 8));
  ESP_ERROR_CHECK(uart_set_rx_timeout(port, 2));
  uart_flush_input(port);
  uart_ready_.fetch_or(1u << index);
  bm::Parser brain_parser;
  fpga::Parser fpga_parser;
  uint32_t seen_generation = generation_.load(), seen_epoch = epoch_.load();
  uint8_t bytes[64];
  for (;;) {
    uart_event_t event;
    // Wait on ISR notifications, not inside a length-based read. IDF's
    // uart_read_bytes(..., 1 tick) can wait again for every ring-buffer item;
    // a 64-byte request can delay a short batch past the parser's 2ms limit.
    // The bounded wait also observes epoch changes when the wire is silent.
    if (xQueueReceive(uart_events, &event, pdMS_TO_TICKS(1)) == pdTRUE) {
      do {
        if (event.type == UART_FIFO_OVF || event.type == UART_BUFFER_FULL) {
          ++rx_errors_;
          ++uart_hw_errors_[index];
          uart_flush_input(port);
          brain_parser.Reset();
          fpga_parser.Reset();
          fault_pending_.fetch_or(Internal);
          Inhibit(true);
          Wake();
        } else if (event.type == UART_FRAME_ERR ||
                   event.type == UART_PARITY_ERR) {
          ++rx_errors_;
          ++uart_hw_errors_[index];
          brain_parser.Reset();
          fpga_parser.Reset();
        }
      } while (xQueueReceive(uart_events, &event, 0) == pdTRUE);
    }
    // Recheck after the wait: never finish an old partial frame in a new
    // control epoch or recovery generation.
    const uint32_t generation = generation_.load(), epoch = epoch_.load();
    if ((index == 1 && generation != seen_generation) ||
        (index == 0 && epoch != seen_epoch)) {
      brain_parser.Reset();
      fpga_parser.Reset();
      if (uart_flush_input(port) != ESP_OK) {
        fault_pending_.fetch_or(Internal);
        Inhibit(true);
        Wake();
        continue;
      }
      seen_generation = generation;
      seen_epoch = epoch;
    }
    const int n = uart_read_bytes(port, bytes, sizeof(bytes), 0);
    if (n > 0) uart_bytes_[index].fetch_add(uint32_t(n));
    for (int i = 0; i < n; ++i) {
      Event message{};
      message.at = Now();
      message.epoch = epoch_.load();
      message.generation = generation_.load();
      bool complete;
      if (index == 0) {
        message.type = EventType::Brain;
        complete = brain_parser.Feed(bytes[i], message.at, message.brain);
        if (complete) ++uart_frames_[index];
        if (complete && message.brain.type == bm::Stop) {
          portENTER_CRITICAL(&stop_mux_);
          stop_frame_ = message.brain;
          stop_pending_ = true;
          portEXIT_CRITICAL(&stop_mux_);
          Inhibit(false);
          Wake();
          complete = false;
        }
      } else {
        message.type = EventType::Fpga;
        complete = fpga_parser.Feed(bytes[i], message.at, message.fpga);
        if (complete) ++uart_frames_[index];
      }
      if (complete) Submit(message);
    }
    // Parsers count rejected frames without treating every CRC error as FAULT.
    static std::atomic<uint32_t> parser_errors[2];
    const uint32_t count =
        index == 0 ? brain_parser.errors : fpga_parser.errors;
    const auto previous = parser_errors[index].exchange(count);
    rx_errors_.fetch_add(count - previous);
    uart_parse_errors_[index] = count;
    if (index == 1 && count != previous) {
      // Publish one coherent error context. Only this small copy is inside
      // the critical section; formatting and console I/O stay outside RX.
      portENTER_CRITICAL(&parser_diag_mux_);
      fpga_diagnostics_ = fpga_parser.GetDiagnostics();
      portEXIT_CRITICAL(&parser_diag_mux_);
    }
  }
}
void Runtime::ControlTask() {
  uint8_t previous_state = 255, previous_link = 255, previous_drive = 255;
  uint16_t previous_fault = 0xffff;
  for (;;) {
    ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(1));
    uint64_t now = Now();
    core_.InputsNow({bool(gpio_get_level(board::ack)),
                     bool(gpio_get_level(board::fpga_permit)),
                     bool(gpio_get_level(board::safety)),
                     bool(gpio_get_level(board::gate))},
                    now);
    if (const auto fault = fault_pending_.exchange(0))
      core_.RuntimeFault(uint16_t(fault), now);
    if (local_stop_.exchange(false)) core_.LocalStop(now);
    bool stopped = false;
    portENTER_CRITICAL(&stop_mux_);
    bm::Frame stop = stop_frame_;
    if (stop_pending_.exchange(false)) stopped = true;
    portEXIT_CRITICAL(&stop_mux_);
    if (stopped) core_.OnBrain(stop, now);
    core_.Tick(now);
    epoch_ = core_.GetView(now).epoch;
    generation_ = core_.LinkGeneration();
    Event event;
    for (int count = 0; count < 16 && xQueueReceive(events_, &event, 0);
         ++count) {
      // RX can enqueue after this iteration's first timestamp. Sample after
      // dequeue so a newly arrived event is not mistaken for future data.
      now = Now();
      if (event.epoch != epoch_.load()) continue;
      if (now < event.at || now - event.at >= 10000) {
        ++queue_drops_;
        if (core_.GetView(now).driver_permit) core_.RuntimeFault(Internal, now);
        continue;
      }
      if (event.type == EventType::Brain) {
        if (!gpio_get_level(board::boot) && event.brain.type != bm::Stop)
          continue;
        core_.OnBrain(event.brain, now);
        const auto view = core_.GetView(now);
        if (event.brain.type == bm::Twist && view.applied == event.brain.seq &&
            view.result == Result::OK)
          brain_at_ = event.at;
      } else if (event.generation == core_.LinkGeneration())
        core_.OnFpga(event.fpga, now);
      epoch_ = core_.GetView(now).epoch;
      generation_ = core_.LinkGeneration();
    }
    ConfigRequest request;
    if (xQueueReceive(config_requests_, &request, 0)) {
      ConfigReply reply{core_.Configuration(), false, request.id};
      if (request.operation == 0 && !storage_busy_)
        reply.accepted = core_.Configure(request.config, now);
      else if (request.operation == 1 && !storage_busy_) {
        Config locked = reply.config;
        locked.validated = false;
        reply.accepted = core_.Configure(locked, now);
        storage_busy_ = reply.accepted;
      } else if (request.operation == 2 && storage_busy_) {
        reply.accepted = core_.Configure(request.config, now);
        storage_busy_ = false;
      }
      Publish(now);
      xQueueOverwrite(config_replies_, &reply);
    }
    now = Now();
    core_.Tick(now);
    if (!gpio_get_level(board::boot) &&
        (core_.GetView(now).state == State::Arming ||
         core_.GetView(now).state == State::Armed))
      core_.LocalStop(now);
    auto view = core_.GetView(now);
    epoch_ = view.epoch;
    generation_ = core_.LinkGeneration();
    portENTER_CRITICAL(&driver_mux_);
    const bool hard_ok = !fault_pending_.load() &&
                         gpio_get_level(board::safety) &&
                         gpio_get_level(board::gate);
    gpio_set_level(board::logical, view.motion_permit && hard_ok);
    gpio_set_level(board::req, view.recovery_req && !stop_pending_.load() &&
                                   !local_stop_.load());
    const bool allow = board::allow_driver && view.driver_permit && hard_ok &&
                       gpio_get_level(board::fpga_permit) &&
                       gpio_get_level(board::boot) && !stop_pending_.load() &&
                       !local_stop_.load();
    driver_live_ = allow;
    gpio_set_level(board::driver, allow);
    portEXIT_CRITICAL(&driver_mux_);
    heartbeat_ = uint32_t(now);
    if (uart_ready_.load() == 3) {
      Packet packet{};
      packet.epoch = view.epoch;
      packet.generation = generation_.load();
      packet.at = now;
      fpga::Frame outgoing;
      if (core_.TakeFpgaTx(outgoing, now)) {
        packet.type = outgoing.type;
        packet.brain_at = outgoing.type == fpga::Command ? brain_at_ : 0;
        packet.size =
            fpga::Encode(outgoing, packet.bytes.data(), packet.bytes.size());
        xQueueOverwrite(tx_[1], &packet);
        brain_at_ = 0;
      }
      bm::Frame status;
      if (core_.TakeBrainTx(status, now)) {
        packet.brain_at = 0;
        packet.type = status.type;
        packet.size =
            bm::Encode(status, packet.bytes.data(), packet.bytes.size());
        xQueueOverwrite(tx_[0], &packet);
      }
    }
    if (uint8_t(view.state) != previous_state ||
        uint8_t(view.link_phase) != previous_link ||
        uint8_t(view.drive.phase) != previous_drive ||
        view.fault != previous_fault) {
      const LogEvent entry{now, view.fault, uint8_t(view.state),
                           uint8_t(view.link_phase), uint8_t(view.drive.phase)};
      if (xQueueSend(logs_, &entry, 0) != pdTRUE) ++log_drops_;
      previous_state = uint8_t(view.state);
      previous_link = uint8_t(view.link_phase);
      previous_drive = uint8_t(view.drive.phase);
      previous_fault = view.fault;
    }
    Publish(now);
  }
}
void Runtime::TransmitTask() {
  for (;;) {
    if (uart_ready_.load() == 3)
      for (int i = 0; i < 2; ++i) {
        const uart_port_t port = i == 0 ? UART_NUM_1 : UART_NUM_2;
        if (uart_wait_tx_done(port, 0) != ESP_OK) continue;
        Packet packet;
        if (!xQueueReceive(tx_[i], &packet, 0)) continue;
        const uint64_t now = Now();
        const bool disable = i == 1 && packet.type == fpga::Disable;
        if (!disable && (packet.epoch != epoch_.load() ||
                         (i == 1 && packet.generation != generation_.load()) ||
                         now - packet.at >= 20000 || stop_pending_.load() ||
                         local_stop_.load() || fault_pending_.load())) {
          ++tx_drops_;
          continue;
        }
        if (i == 1 && packet.type == fpga::Command &&
            uint32_t(uint32_t(now) - heartbeat_.load()) >= 20000) {
          fault_pending_.fetch_or(Internal);
          Inhibit(true);
          Wake();
          ++tx_drops_;
          continue;
        }
        const auto start = Now();
        if (uart_write_bytes(port, packet.bytes.data(), packet.size) !=
            int(packet.size)) {
          fault_pending_.fetch_or(Internal);
          Inhibit(true);
          Wake();
          ++tx_drops_;
        } else
          ++uart_tx_frames_[i];
        if (packet.brain_at && start >= packet.brain_at) {
          const uint32_t us = uint32_t(start - packet.brain_at);
          portENTER_CRITICAL(&snapshot_mux_);
          latency_[latency_count_++ % latency_.size()] = us;
          latency_max_ = std::max(latency_max_, us);
          portEXIT_CRITICAL(&snapshot_mux_);
        }
      }
    vTaskDelay(pdMS_TO_TICKS(1));
  }
}
void Runtime::Publish(uint64_t now) {
  const auto view = core_.GetView(now);
  const auto config = core_.Configuration();
  portENTER_CRITICAL(&snapshot_mux_);
  snapshot_.view = view;
  snapshot_.config = config;
  snapshot_.rx_errors = rx_errors_;
  snapshot_.queue_drops = queue_drops_;
  snapshot_.tx_drops = tx_drops_;
  snapshot_.log_drops = log_drops_;
  portEXIT_CRITICAL(&snapshot_mux_);
}
Snapshot Runtime::ReadSnapshot() {
  portENTER_CRITICAL(&snapshot_mux_);
  Snapshot result = snapshot_;
  portEXIT_CRITICAL(&snapshot_mux_);
  return result;
}
bool Runtime::Configure(const Config& config) {
  if (config.validated && !board::allow_driver) return false;
  ConfigReply reply{};
  return ExchangeConfig({config, 0}, reply) && reply.accepted;
}
bool Runtime::BeginStorage(Config& config) {
  ConfigReply reply{};
  if (!ExchangeConfig({{}, 1}, reply) || !reply.accepted) return false;
  config = reply.config;
  return true;
}
bool Runtime::EndStorage(const Config& config) {
  ConfigReply reply{};
  return ExchangeConfig({config, 2}, reply) && reply.accepted;
}
bool Runtime::ExchangeConfig(ConfigRequest request, ConfigReply& reply) {
  // Only the console task calls this method. IDs prevent a late reply from a
  // timed-out request authorizing a later flash write before its lock exists.
  request.id = ++config_id_;
  if (xQueueSend(config_requests_, &request, pdMS_TO_TICKS(100)) != pdTRUE)
    return false;
  Wake();
  const uint64_t until = Now() + 1000000;
  while (Now() < until) {
    if (xQueueReceive(config_replies_, &reply, pdMS_TO_TICKS(10)) &&
        reply.id == request.id)
      return true;
  }
  return false;
}
void Runtime::PrintUartDiagnostics() {
  for (int i = 0; i < 2; ++i) {
    uint32_t baud = 0;
    const auto code =
        uart_get_baudrate(i == 0 ? UART_NUM_1 : UART_NUM_2, &baud);
    std::printf(
        "UART_DIAG peer=%s tx=%d rx=%d baud=%lu get_baud_rc=%d rx_bytes=%lu "
        "frames=%lu hw_errors=%lu parser_errors=%lu tx_frames=%lu "
        "rx_level=%d\n",
        i == 0 ? "Brain" : "FPGA", i == 0 ? board::brain_tx : board::fpga_tx,
        i == 0 ? board::brain_rx : board::fpga_rx, (unsigned long)baud,
        int(code), (unsigned long)uart_bytes_[i].load(),
        (unsigned long)uart_frames_[i].load(),
        (unsigned long)uart_hw_errors_[i].load(),
        (unsigned long)uart_parse_errors_[i].load(),
        (unsigned long)uart_tx_frames_[i].load(),
        gpio_get_level(gpio_num_t(i == 0 ? board::brain_rx : board::fpga_rx)));
  }
  fpga::Parser::Diagnostics d;
  portENTER_CRITICAL(&parser_diag_mux_);
  d = fpga_diagnostics_;
  portEXIT_CRITICAL(&parser_diag_mux_);
  std::printf(
      "UART_PARSE_DIAG peer=FPGA timeouts=%lu header_errors=%lu crc_errors=%lu "
      "last_reason=%lu last_gap_us=%lu last_frame_us=%lu last_size=%lu\n",
      (unsigned long)d.timeout_errors,
      (unsigned long)d.header_errors,
      (unsigned long)d.crc_errors,
      (unsigned long)d.last_reason,
      (unsigned long)d.last_gap_us,
      (unsigned long)d.last_frame_us,
      (unsigned long)d.last_size);
}
void Runtime::StatsTask() {
  StatusLed led;
  led.Init(board::status_led);
  for (;;) {
    const auto current = ReadSnapshot();
    // Load the other core's heartbeat before sampling time; it must not
    // appear to come from the future and underflow the unsigned age.
    const uint32_t control_at = heartbeat_.load();
    const uint64_t now = Now();
    const auto desired_indicator = indicator::Motion(current.view.fault,
        current.view.fpga_fault, current.view.configured, current.view.fresh,
        gpio_get_level(board::safety), gpio_get_level(board::gate),
        !fault_pending_.load() && uint32_t(uint32_t(now) - control_at) < 20000);
    led.Update(desired_indicator, now);
    portENTER_CRITICAL(&snapshot_mux_);
    snapshot_.indicator = desired_indicator;
    snapshot_.led_known = led.Output().Known();
    snapshot_.led_writes = led.Output().Writes();
    snapshot_.led_errors = led.Output().Errors();
    snapshot_.led_max_us = led.MaxWriteUs();
    portEXIT_CRITICAL(&snapshot_mux_);
    for (int n = 0; n < 10; ++n) {
      LogEvent event;
      if (!xQueueReceive(logs_, &event, 0)) break;
      std::printf("EVENT t=%llu state=%u fault=0x%04x link=%u drive=%u\n",
                  static_cast<unsigned long long>(event.at), event.state,
                  event.fault, event.link, event.drive);
    }
    std::array<uint32_t, 128> samples;
    uint32_t count, maximum;
    portENTER_CRITICAL(&snapshot_mux_);
    samples = latency_;
    count = std::min<uint32_t>(latency_count_, samples.size());
    maximum = latency_max_;
    portEXIT_CRITICAL(&snapshot_mux_);
    std::sort(samples.begin(), samples.begin() + count);
    const auto heap = heap_caps_get_free_size(MALLOC_CAP_INTERNAL);
    const auto min_heap = heap_caps_get_minimum_free_size(MALLOC_CAP_INTERNAL);
    const auto stack = uxTaskGetStackHighWaterMark(control_);
    portENTER_CRITICAL(&snapshot_mux_);
    snapshot_.latency_count = latency_count_;
    snapshot_.max_us = maximum;
    if (count) {
      snapshot_.p95_us = samples[(count - 1) * 95 / 100];
      snapshot_.p99_us = samples[(count - 1) * 99 / 100];
    }
    snapshot_.heap_free = heap;
    snapshot_.heap_min = min_heap;
    snapshot_.control_stack = stack;
    portEXIT_CRITICAL(&snapshot_mux_);
    vTaskDelay(pdMS_TO_TICKS(100));
  }
}
}  // namespace awcar::motion
