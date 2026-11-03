#include "brain_runtime.h"

#include <driver/gptimer.h>
#include <driver/uart.h>
#include <esp_heap_caps.h>
#include <esp_log.h>
#include <esp_random.h>
#include <esp_timer.h>
#include <net/if.h>
#include <unistd.h>

#include <algorithm>
#include <cmath>
#include <cstring>
#include <new>

#include "application.h"
#include "aw_car_network.h"
#include "aw_car_web_assets.h"
#include "boards/aw-car-ai-rgb/rgb_light.h"
#include "display.h"
#include "mcp_server.h"
#include "websocket_transport.h"

namespace awcar {
namespace {
uint64_t Now() { return uint64_t(esp_timer_get_time()); }
bool Int(const cJSON* obj, const char* name, int64_t lo, int64_t hi,
         int64_t& out) {
  auto* v = cJSON_GetObjectItemCaseSensitive(obj, name);
  if (!cJSON_IsNumber(v) || !std::isfinite(v->valuedouble) ||
      v->valuedouble < double(lo) || v->valuedouble > double(hi) ||
      std::floor(v->valuedouble) != v->valuedouble)
    return false;
  out = int64_t(v->valuedouble);
  return true;
}
std::string Json(cJSON* obj) {
  char* p = cJSON_PrintUnformatted(obj);
  std::string out = p ? p : "{}";
  cJSON_free(p);
  cJSON_Delete(obj);
  return out;
}
const char* String(const cJSON* obj, const char* name) {
  auto* p = cJSON_GetObjectItemCaseSensitive(obj, name);
  return cJSON_IsString(p) ? p->valuestring : "";
}
}  // namespace
BrainRuntime::BrainRuntime() : core_(Config{200, 1000, esp_random()}) {}
void BrainRuntime::Start(AwCarRgbLight* rgb, Display* display, Network* net) {
  if (running_.exchange(true)) return;
  rgb_ = rgb;
  display_ = display;
  network_ = net;
  snprintf(pin_, sizeof(pin_), "%06lu",
           (unsigned long)(esp_random() % 1000000));
  for (size_t i = 0; i < 32; i++)
    snprintf(cookie_ + 2 * i, 3, "%02x", unsigned(esp_random() & 255));
  events_ = static_cast<Event*>(heap_caps_calloc(
      100, sizeof(Event), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  auto task_result = xTaskCreatePinnedToCore(
      [](void* p) { static_cast<BrainRuntime*>(p)->ControlTask(); },
      "car_control", 4096, this, 12, &control_task_, 1);
  ESP_ERROR_CHECK(task_result == pdPASS ? ESP_OK : ESP_ERR_NO_MEM);
  task_result = xTaskCreatePinnedToCore(
      [](void* p) { static_cast<BrainRuntime*>(p)->UartTask(); }, "car_uart",
      4096, this, 11, &uart_task_, 1);
  ESP_ERROR_CHECK(task_result == pdPASS ? ESP_OK : ESP_ERR_NO_MEM);
  gptimer_handle_t timer = nullptr;
  gptimer_config_t config{};
  config.clk_src = GPTIMER_CLK_SRC_DEFAULT;
  config.direction = GPTIMER_COUNT_UP;
  config.resolution_hz = 1000000;
  ESP_ERROR_CHECK(gptimer_new_timer(&config, &timer));
  gptimer_event_callbacks_t callbacks{};
  callbacks.on_alarm = [](gptimer_handle_t, const gptimer_alarm_event_data_t*,
                          void* ctx) -> bool {
    auto* self = static_cast<BrainRuntime*>(ctx);
    BaseType_t wake = pdFALSE;
    vTaskNotifyGiveFromISR(self->control_task_, &wake);
    return wake == pdTRUE;
  };
  ESP_ERROR_CHECK(gptimer_register_event_callbacks(timer, &callbacks, this));
  gptimer_alarm_config_t alarm{};
  alarm.alarm_count = 5000;
  alarm.flags.auto_reload_on_alarm = true;
  ESP_ERROR_CHECK(gptimer_set_alarm_action(timer, &alarm));
  ESP_ERROR_CHECK(gptimer_enable(timer));
  ESP_ERROR_CHECK(gptimer_start(timer));
  RegisterTools();
  StartWeb();
  ShowPairing();
}
void BrainRuntime::Wake() {
  if (control_task_) xTaskNotifyGive(control_task_);
  if (uart_task_) xTaskNotifyGive(uart_task_);
}
void BrainRuntime::Stop() {
  stop_requested_ = true;
  Wake();
}
void BrainRuntime::TickLocked(uint64_t now) {
  if (stop_requested_.exchange(false)) core_.Stop("user_stop", now);
  core_.Tick(now);
  auto state = core_.GetState(now);
  if (state.epoch != observed_epoch_) {
    voice_.Epoch(state.epoch);
    pending_web_at_ = 0;
    if (state.mode == Mode::AI || observed_mode_ == Mode::AI)
      Application::GetInstance().InvalidateCarConversation();
    observed_epoch_ = state.epoch;
    observed_mode_ = state.mode;
  }
}
void BrainRuntime::ControlTask() {
  for (;;) {
    ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
    {
      std::lock_guard<std::mutex> lock(mutex_);
      TickLocked(Now());
    }
    if (uart_task_) xTaskNotifyGive(uart_task_);
  }
}
void BrainRuntime::UartTask() {
  constexpr uart_port_t port = UART_NUM_1;
  uart_config_t cfg{};
  cfg.baud_rate = 115200;
  cfg.data_bits = UART_DATA_8_BITS;
  cfg.parity = UART_PARITY_DISABLE;
  cfg.stop_bits = UART_STOP_BITS_1;
  cfg.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
  cfg.source_clk = UART_SCLK_DEFAULT;
  ESP_ERROR_CHECK(uart_param_config(port, &cfg));
  ESP_ERROR_CHECK(uart_set_pin(port, GPIO_NUM_17, GPIO_NUM_18,
                               UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
  // No TX ring: at most the one short frame already on the wire can precede
  // STOP.
  ESP_ERROR_CHECK(uart_driver_install(port, 256, 0, 0, nullptr, 0));
  uart_set_rx_full_threshold(port, 8);
  uart_set_rx_timeout(port, 2);
  bm::Parser parser;
  uint8_t in[64], out[32];
  for (;;) {
    ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(10));
    int n = uart_read_bytes(port, in, sizeof(in), 0);
    bm::Frame received;
    for (int i = 0; i < n; i++)
      if (parser.Feed(in[i], Now(), received)) {
        std::lock_guard<std::mutex> lock(mutex_);
        TickLocked(Now());
        core_.OnStatus(received, Now());
      }
    rx_errors_ = parser.errors;
    for (int count = 0; count < 3; count++) {
      if (uart_wait_tx_done(port, 0) != ESP_OK) break;
      bm::Frame f;
      bool pending;
      uint64_t web_at = 0;
      {
        std::lock_guard<std::mutex> lock(mutex_);
        TickLocked(Now());
        pending = core_.TakeTx(f, Now());
        if (pending && f.type == bm::Twist) {
          web_at = pending_web_at_;
          pending_web_at_ = 0;
        }
      }
      if (!pending) break;
      size_t size = bm::Encode(f, out, sizeof(out));
      if (size) {
        const auto enqueue_at = Now();
        uart_write_bytes(port, out, size);
        if (web_at) {
          std::lock_guard<std::mutex> lock(mutex_);
          web_latency_us_[web_latency_count_++ % web_latency_us_.size()] =
              uint32_t(enqueue_at - web_at);
        }
      }
    }
  }
}
void BrainRuntime::CloudOnline(bool online) {
  if (!running_) return;
  {
    std::lock_guard<std::mutex> lock(mutex_);
    core_.SetAiOnline(online, Now());
    TickLocked(Now());
  }
  Wake();
}
void BrainRuntime::CloudSession(const std::string& sid) {
  if (!running_) return;
  std::lock_guard<std::mutex> lock(mutex_);
  TickLocked(Now());
  voice_.Bind(sid.c_str());
}
void BrainRuntime::ChatEvent(const char* kind, const char* text,
                             const char* sid) {
  if (!running_) return;
  if (strcmp(kind, "stt") == 0) {
    std::lock_guard<std::mutex> lock(mutex_);
    voice_.Stt(sid, Now());
  }
  std::lock_guard<std::mutex> lock(event_mutex_);
  if (!events_) return;
  auto& event = events_[(event_head_ + event_count_) % 100];
  if (event_count_ == 100) {
    event_head_ = (event_head_ + 1) % 100;
  } else
    ++event_count_;
  strlcpy(event.kind, kind, sizeof(event.kind));
  strlcpy(event.text, text, sizeof(event.text));
}
VoiceTicket BrainRuntime::CaptureVoice(const std::string& name, int id,
                                       const std::string& sid) {
  if (name != "self.car.move") return {};
  std::lock_guard<std::mutex> lock(mutex_);
  TickLocked(Now());
  return voice_.Capture(core_.Epoch(), id, sid.c_str(), Now());
}
bool BrainRuntime::CheckVoice(const VoiceTicket& ticket) {
  std::lock_guard<std::mutex> lock(mutex_);
  TickLocked(Now());
  executing_ticket_ = ticket;
  return voice_.Check(ticket, core_.Epoch(), Now());
}
void BrainRuntime::RegisterTools() {
  auto& m = McpServer::GetInstance();
  m.SetInvocationGuard([this](const std::string& name, int id,
                              const std::string& sid) -> std::function<bool()> {
    if (name == "self.car.stop") Stop();
    ChatEvent("tool", name.c_str());
    if (name != "self.car.move") return {};
    auto ticket = CaptureVoice(name, id, sid);
    return [this, ticket] {
      bool valid = CheckVoice(ticket);
      if (!valid)
        ChatEvent(
            "tool_result",
            "self.car.move: missing/stale session or STT; movement locked");
      return valid;
    };
  });
  m.AddTool(
      "self.car.move",
      "控制小车短时移动。仅AI模式且网页已授权时可用。action: "
      "forward前进、backward后退、left向左前方转弯、right向右前方转弯、spin_"
      "left原地左转、spin_"
      "right原地右转。默认1秒，最长3秒，每次一句一个动作；不是按米定位。成功仅"
      "表示Brain接收请求，不证明电机实际运行。",
      PropertyList(
          {Property("action", kPropertyTypeString),
           Property("speed_pct", kPropertyTypeInteger, 30, 0, 100),
           Property("duration_ms", kPropertyTypeInteger, 1000, 100, 3000)}),
      [this](const PropertyList& p) -> ToolResult {
        static const char* actions[] = {"forward", "backward",  "left",
                                        "right",   "spin_left", "spin_right"};
        auto name = p["action"].value<std::string>();
        int action = -1;
        for (int i = 0; i < 6; i++)
          if (name == actions[i]) action = i;
        Result result;
        {
          std::lock_guard<std::mutex> lock(mutex_);
          TickLocked(Now());
          if (!voice_.Check(executing_ticket_, core_.Epoch(), Now()))
            return std::unexpected(
                "Stale/missing voice context; start a fresh conversation");
          result = core_.VoiceMove(executing_ticket_.epoch, action,
                                   p["speed_pct"].value<int>(),
                                   p["duration_ms"].value<int>(), Now());
          if (result == Result::OK) voice_.Consume(executing_ticket_);
        }
        Wake();
        ChatEvent(
            "tool_result",
            ("self.car.move: " + std::string(ResultName(result))).c_str());
        if (result != Result::OK) return std::unexpected(ResultName(result));
        return ReturnValue(std::string(
            "{\"accepted_by\":\"Brain\",\"motion_applied\":false}"));
      });
  m.AddTool(
      "self.car.stop",
      "停车、停止、停下：立即取消小车运动并撤销运行授权。Manual和AI模式都"
      "接受；再次移动必须在网页点击授权。",
      PropertyList(), [this](const PropertyList&) -> ToolResult {
        Stop();
        ChatEvent(
            "tool_result",
            "self.car.stop: STOP requested; await Motion acknowledgement");
        return ReturnValue(std::string(
            "STOP requested; authorization revoked asynchronously"));
      });
  m.AddTool("self.car.get_state",
            "读取小车控制模式、Motion反馈和授权状态。无传感器数据时返回null，不"
            "能把请求速度当成实际速度。",
            PropertyList(), [this](const PropertyList&) -> ToolResult {
              return ReturnValue(Snapshot());
            });
}
std::string BrainRuntime::Snapshot() {
  State s;
  bool voice_ready;
  std::array<uint32_t, 128> samples;
  uint32_t count, accepted, rejected;
  {
    std::lock_guard<std::mutex> lock(mutex_);
    s = core_.GetState(Now());
    voice_ready = voice_.Ready();
    samples = web_latency_us_;
    count = std::min<uint32_t>(web_latency_count_, samples.size());
    accepted = web_accepted_;
    rejected = web_rejected_;
  }
  auto* j = cJSON_CreateObject();
  cJSON_AddStringToObject(j, "type", "STATUS");
  cJSON_AddStringToObject(j, "mode", s.mode == Mode::AI ? "AI" : "Manual");
#if CONFIG_AWCAR_MOTION_IS_SIMULATED
  cJSON_AddStringToObject(j, "data_source", "mock");
#else
  cJSON_AddStringToObject(j, "data_source", "hardware");
#endif
  cJSON_AddStringToObject(j, "brain_source", "hardware");
  cJSON_AddNumberToObject(j, "heap_free_internal",
                          heap_caps_get_free_size(MALLOC_CAP_INTERNAL));
  cJSON_AddNumberToObject(j, "heap_min_internal",
                          heap_caps_get_minimum_free_size(MALLOC_CAP_INTERNAL));
  cJSON_AddNumberToObject(j, "heap_free_psram",
                          heap_caps_get_free_size(MALLOC_CAP_SPIRAM));
  cJSON_AddNumberToObject(j, "control_stack_headroom_bytes",
                          uxTaskGetStackHighWaterMark(control_task_));
  cJSON_AddNumberToObject(j, "uart_stack_headroom_bytes",
                          uxTaskGetStackHighWaterMark(uart_task_));
  cJSON_AddBoolToObject(j, "authorized", s.authorized);
  cJSON_AddBoolToObject(j, "switching", s.switching);
  cJSON_AddBoolToObject(j, "ai_online", s.ai_online);
  cJSON_AddBoolToObject(j, "voice_context_ready", voice_ready);
  cJSON_AddBoolToObject(j, "log_available", events_ != nullptr);
  cJSON_AddNumberToObject(j, "rx_errors", rx_errors_.load());
  cJSON_AddNumberToObject(j, "web_accepted", accepted);
  cJSON_AddNumberToObject(j, "web_rejected", rejected);
  if (count) {
    std::sort(samples.begin(), samples.begin() + count);
    cJSON_AddNumberToObject(j, "web_uart_p95_us",
                            samples[(count - 1) * 95 / 100]);
    cJSON_AddNumberToObject(j, "web_uart_p99_us",
                            samples[(count - 1) * 99 / 100]);
  } else {
    cJSON_AddNullToObject(j, "web_uart_p95_us");
    cJSON_AddNullToObject(j, "web_uart_p99_us");
  }
  cJSON_AddNumberToObject(j, "epoch", s.epoch);
  cJSON_AddNumberToObject(j, "challenge", s.challenge);
  cJSON_AddNumberToObject(j, "v", s.v);
  cJSON_AddNumberToObject(j, "omega", s.omega);
  cJSON_AddNumberToObject(j, "v_max", 200);
  cJSON_AddNumberToObject(j, "omega_max", 1000);
  cJSON_AddNumberToObject(j, "ai_remaining_ms", s.ai_remaining_ms);
  cJSON_AddNumberToObject(j, "action_remaining_ms", s.action_remaining_ms);
  cJSON_AddNumberToObject(j, "motion_state", s.motion_state);
  cJSON_AddNumberToObject(j, "fault_flags", s.fault);
  cJSON_AddNumberToObject(j, "status_flags", s.flags);
  cJSON_AddNumberToObject(j, "last_req_seq", s.last_req);
  cJSON_AddNumberToObject(j, "applied_seq", s.applied);
  cJSON_AddNumberToObject(j, "result_code", s.result);
  cJSON_AddNumberToObject(j, "telemetry_age_ms", s.telemetry_age_ms);
  cJSON_AddNumberToObject(j, "encoder_age_ms", s.encoder_age);
  cJSON_AddStringToObject(j, "reason", s.reason);
  auto value = [&](const char* key, int val, bool valid) {
    if (valid)
      cJSON_AddNumberToObject(j, key, val);
    else
      cJSON_AddNullToObject(j, key);
  };
  value("v_est_mm_s", s.v_est, s.flags & 1);
  value("omega_est_mrad_s", s.omega_est, s.flags & 2);
  value("battery_mv", s.battery, s.flags & 4);
  if (rgb_)
    cJSON_AddItemToObject(j, "rgb", cJSON_Parse(rgb_->SnapshotJson().c_str()));
  const char* chat = "Xiaozhi đang khởi động";
  switch (Application::GetInstance().GetDeviceState()) {
    case kDeviceStateIdle:
      chat = "Đang chờ · nhấn BOOT để nói";
      break;
    case kDeviceStateConnecting:
      chat = "Đang kết nối hội thoại";
      break;
    case kDeviceStateListening:
      chat = "Đang nghe";
      break;
    case kDeviceStateSpeaking:
      chat = "AI đang trả lời";
      break;
    case kDeviceStateNotifying:
      chat = "Đang phát thông báo";
      break;
    case kDeviceStateWifiConfiguring:
      chat = "Đang cấu hình Wi-Fi";
      break;
    case kDeviceStateUpgrading:
      chat = "Đang cập nhật";
      break;
    case kDeviceStateActivating:
      chat = "Đang kích hoạt Xiaozhi";
      break;
    case kDeviceStateAudioTesting:
      chat = "Đang kiểm tra âm thanh";
      break;
    case kDeviceStateFatalError:
      chat = "Lỗi Xiaozhi";
      break;
    default:
      break;
  }
  cJSON_AddStringToObject(j, "chat_state", chat);
  return Json(j);
}
bool BrainRuntime::CanConfigure() {
  std::lock_guard<std::mutex> lock(mutex_);
  auto s = core_.GetState(Now());
  return !s.authorized && !s.switching && s.motion_state == 0 &&
         strcmp(s.reason, "arming") != 0;
}
void BrainRuntime::ShowPairing() {
  auto now = Now();
  {
    std::lock_guard<std::mutex> lock(event_mutex_);
    if (now - last_pairing_ < 3000000 && last_pairing_) return;
    last_pairing_ = now;
  }
  if (display_ && network_) {
    // The OLED notification bar is only 16 pixels high. Keep the PIN on
    // one line and use the existing scrolling chat label for credentials.
    display_->SetChatMessage(
        "system", (network_->Ssid() + "  PASS:" + network_->Password() +
                   "  http://192.168.4.1")
                      .c_str());
    display_->ShowNotification((std::string("PIN:") + pin_).c_str(), 15000);
  }
}
bool BrainRuntime::Auth(httpd_req_t* req) {
  char header[160];
  if (httpd_req_get_hdr_value_str(req, "Cookie", header, sizeof(header)) !=
      ESP_OK)
    return false;
  const char* start = strstr(header, "awcar=");
  if (!start) return false;
  start += 6;
  if (strlen(start) < 64) return false;
  unsigned diff = 0;
  for (size_t i = 0; i < 64; i++) diff |= unsigned(start[i] ^ cookie_[i]);
  return diff == 0 && (start[64] == 0 || start[64] == ';');
}
bool BrainRuntime::Origin(httpd_req_t* req) {
  char value[80];
  return httpd_req_get_hdr_value_str(req, "Origin", value, sizeof(value)) ==
             ESP_OK &&
         (strcmp(value, "http://192.168.4.1") == 0 ||
          strcmp(value, "http://192.168.4.1:80") == 0);
}
std::string BrainRuntime::Dispatch(const cJSON* d) {
  const char* type = String(d, "type");
  Result result = Result::OK;
  int64_t epoch, seq, challenge, v, w, ttl;
  if (strcmp(type, "STOP") == 0)
    Stop();
  else if (strcmp(type, "HEARTBEAT") == 0)
    last_client_ms_ = uint32_t(Now() / 1000);
  else if (strcmp(type, "ARM") == 0) {
    if (!Int(d, "epoch", 0, UINT32_MAX, epoch))
      result = Result::BadRange;
    else {
      std::lock_guard<std::mutex> lock(mutex_);
      TickLocked(Now());
      result = core_.RequestArm(epoch, Now());
    }
  } else if (strcmp(type, "SET_MODE") == 0) {
    const char* mode = String(d, "mode");
    if (!Int(d, "epoch", 0, UINT32_MAX, epoch) ||
        (strcmp(mode, "Manual") && strcmp(mode, "AI")))
      result = Result::BadRange;
    else {
      std::lock_guard<std::mutex> lock(mutex_);
      TickLocked(Now());
      result =
          epoch != core_.Epoch()
              ? Result::Stale
              : core_.SetMode(strcmp(mode, "AI") == 0 ? Mode::AI : Mode::Manual,
                              Now());
    }
  } else if (strcmp(type, "MOVE") == 0) {
    auto* deadman = cJSON_GetObjectItemCaseSensitive(d, "deadman");
    if (!Int(d, "epoch", 0, UINT32_MAX, epoch) ||
        !Int(d, "challenge", 1, UINT32_MAX, challenge) ||
        !Int(d, "seq", 0, UINT32_MAX, seq) ||
        !Int(d, "v_mm_s", INT16_MIN, INT16_MAX, v) ||
        !Int(d, "omega_mrad_s", INT16_MIN, INT16_MAX, w) ||
        !Int(d, "ttl_ms", 1, 250, ttl) || !cJSON_IsBool(deadman))
      result = Result::BadRange;
    else {
      std::lock_guard<std::mutex> lock(mutex_);
      TickLocked(Now());
      result = core_.ManualMove(epoch, challenge, seq, v, w, ttl,
                                cJSON_IsTrue(deadman), Now());
      if (result == Result::OK) {
        last_client_ms_ = uint32_t(Now() / 1000);
        pending_web_at_ = Now();
        ++web_accepted_;
      } else
        ++web_rejected_;
    }
  } else if (strcmp(type, "RGB") == 0) {
    auto* on = cJSON_GetObjectItemCaseSensitive(d, "on");
    if (cJSON_IsBool(on)) {
      if (!rgb_->SetPower(cJSON_IsTrue(on))) result = Result::Unsafe;
    } else {
      int64_t r, g, b;
      if (!Int(d, "r", 0, 255, r) || !Int(d, "g", 0, 255, g) ||
          !Int(d, "b", 0, 255, b))
        result = Result::BadRange;
      else if (!rgb_->SetColor(r, g, b))
        result = Result::Unsafe;
    }
  } else if (strcmp(type, "CHAT_TOGGLE") == 0)
    Application::GetInstance().ToggleChatState();
  else
    result = Result::BadRange;
  Wake();
  auto* out = cJSON_CreateObject();
  cJSON_AddStringToObject(out, "type", "ACK");
  cJSON_AddStringToObject(out, "stage", "Brain");
  cJSON_AddStringToObject(out, "result", ResultName(result));
  if (Int(d, "seq", 0, UINT32_MAX, seq))
    cJSON_AddNumberToObject(out, "last_seq", seq);
  return Json(out);
}
esp_err_t BrainRuntime::WebSocketRequest(httpd_req_t* req) {
  if (req->method == HTTP_GET)
    ESP_LOGI("AwCarWeb", "WebSocket connected fd=%d", httpd_req_to_sockfd(req));
  auto result = ServeControlWebSocket(
      req, this, [](void* context, const char* body, size_t len) {
        auto* self = static_cast<BrainRuntime*>(context);
        auto* data = cJSON_ParseWithLength(body, len);
        auto reply = self->Dispatch(data);
        cJSON_Delete(data);
        return reply;
      });
  if (result != ESP_OK)
    ESP_LOGW("AwCarWeb", "WebSocket receive/send failed fd=%d error=%d",
             httpd_req_to_sockfd(req), result);
  return result;
}
esp_err_t BrainRuntime::Request(httpd_req_t* req) {
  if (req->method == HTTP_GET) {
    for (const auto& asset : web_assets)
      if (strcmp(req->uri, asset.path) == 0) {
        httpd_resp_set_type(req, asset.mime);
        return httpd_resp_send(req, asset.data, asset.size);
      }
    return httpd_resp_send_err(req, HTTPD_404_NOT_FOUND, "Not found");
  }
  if (strcmp(req->uri, "/api/pairing") == 0) {
    ShowPairing();
    return httpd_resp_send(req, "{}", 2);
  }
  if (req->content_len > 512)
    return httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Payload too large");
  char body[513];
  int total = 0;
  while (total < int(req->content_len)) {
    int n = httpd_req_recv(req, body + total, req->content_len - total);
    if (n <= 0) return ESP_FAIL;
    total += n;
  }
  body[total] = 0;
  auto* data = cJSON_ParseWithLength(body, total);
  bool success = false;
  if (strcmp(req->uri, "/api/login") == 0) {
    if (Now() - login_window_ >= 30000000) {
      login_window_ = Now();
      login_failures_ = 0;
    }
    if (login_failures_ >= 5) {
      cJSON_Delete(data);
      httpd_resp_set_status(req, "429 Too Many Requests");
      return httpd_resp_send(req, "Retry later", HTTPD_RESP_USE_STRLEN);
    }
    if (client_ >= 0) {
      cJSON_Delete(data);
      httpd_resp_set_status(req, "409 Conflict");
      return httpd_resp_send(req, "Dashboard busy", HTTPD_RESP_USE_STRLEN);
    }
    const char* supplied = String(data, "pin");
    unsigned diff = unsigned(strlen(supplied) ^ 6);
    for (size_t i = 0; i < 6 && i < strlen(supplied); i++)
      diff |= unsigned(supplied[i] ^ pin_[i]);
    success = diff == 0;
    if (!success) ++login_failures_;
    if (success) {
      char cookie[150];
      snprintf(cookie, sizeof(cookie),
               "awcar=%s; HttpOnly; SameSite=Strict; Path=/", cookie_);
      httpd_resp_set_hdr(req, "Set-Cookie", cookie);
    }
  } else if (strcmp(req->uri, "/api/wifi") == 0 && Auth(req) && Origin(req) &&
             CanConfigure())
    success =
        network_->Configure(String(data, "ssid"), String(data, "password"));
  cJSON_Delete(data);
  httpd_resp_set_type(req, "application/json");
  if (!success) httpd_resp_set_status(req, "403 Forbidden");
  return httpd_resp_send(req, success ? "{\"ok\":true}" : "{\"ok\":false}",
                         HTTPD_RESP_USE_STRLEN);
}
void BrainRuntime::StartWeb() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.task_priority = 4;
  config.core_id = 1;
  config.stack_size = 6144;
  config.max_open_sockets = 4;
  config.lru_purge_enable = true;
  config.max_uri_handlers = 12;
  config.recv_wait_timeout = 1;
  config.send_wait_timeout = 1;
  struct ifreq interface{};
  ESP_ERROR_CHECK(
      esp_netif_get_netif_impl_name(network_->Ap(), interface.ifr_name));
  config.if_name = &interface;
  config.close_fn = [](httpd_handle_t handle, int fd) {
    auto* self = &BrainRuntime::Get();
    int expected = fd;
    if (self->client_.compare_exchange_strong(expected, -1)) {
      ++self->client_generation_;
      std::lock_guard<std::mutex> lock(self->mutex_);
      self->core_.WebDisconnect(Now());
      self->Wake();
    }
    close(fd);
    (void)handle;
  };
  ESP_ERROR_CHECK(httpd_start(&server_, &config));
  for (const auto& asset : web_assets) {
    httpd_uri_t uri{};
    uri.uri = asset.path;
    uri.method = HTTP_GET;
    uri.handler = [](httpd_req_t* r) { return BrainRuntime::Get().Request(r); };
    ESP_ERROR_CHECK(httpd_register_uri_handler(server_, &uri));
  }
  for (const char* path : {"/api/login", "/api/pairing", "/api/wifi"}) {
    httpd_uri_t uri{};
    uri.uri = path;
    uri.method = HTTP_POST;
    uri.handler = [](httpd_req_t* r) { return BrainRuntime::Get().Request(r); };
    ESP_ERROR_CHECK(httpd_register_uri_handler(server_, &uri));
  }
  httpd_uri_t ws{};
  ws.uri = "/ws";
  ws.method = HTTP_GET;
  ws.is_websocket = true;
  ws.handler = [](httpd_req_t* r) {
    return BrainRuntime::Get().WebSocketRequest(r);
  };
  ws.ws_pre_handshake_cb = [](httpd_req_t* r) -> esp_err_t {
    auto& self = BrainRuntime::Get();
    int expected = -1;
    if (!self.Auth(r)) {
      ESP_LOGW("AwCarWeb",
               "WebSocket rejected: authentication missing/invalid");
      return ESP_FAIL;
    }
    if (!self.Origin(r)) {
      ESP_LOGW("AwCarWeb", "WebSocket rejected: origin mismatch");
      return ESP_FAIL;
    }
    int fd = httpd_req_to_sockfd(r);
    if (!self.client_.compare_exchange_strong(expected, fd)) {
      ESP_LOGW("AwCarWeb", "WebSocket rejected: another dashboard is active");
      return ESP_FAIL;
    }
    ++self.client_generation_;
    {
      std::lock_guard<std::mutex> lock(self.mutex_);
      self.core_.WebConnect(Now());
      self.last_client_ms_ = uint32_t(Now() / 1000);
    }
    self.Wake();
    return ESP_OK;
  };
  ESP_ERROR_CHECK(httpd_register_uri_handler(server_, &ws));
  auto result = xTaskCreatePinnedToCore(
      [](void* p) { static_cast<BrainRuntime*>(p)->WebTask(); }, "car_status",
      6144, this, 2, nullptr, 1);
  ESP_ERROR_CHECK(result == pdPASS ? ESP_OK : ESP_ERR_NO_MEM);
}
void BrainRuntime::WebTask() {
  bool alternate = false;
  struct Work {
    BrainRuntime* self;
    int fd;
    uint32_t generation;
    std::string status, event;
  };
  for (;;) {
    vTaskDelay(pdMS_TO_TICKS(50));
    int fd = client_;
    if (fd < 0) continue;
    if (uint32_t(uint32_t(Now() / 1000) - last_client_ms_.load()) > 500) {
      httpd_sess_trigger_close(server_, fd);
      continue;
    }
    std::string payload;
    if ((alternate = !alternate))
      payload = Snapshot();
    else {
      State s;
      {
        std::lock_guard<std::mutex> lock(mutex_);
        s = core_.GetState(Now());
      }
      payload = "{\"type\":\"CHALLENGE\",\"epoch\":" + std::to_string(s.epoch) +
                ",\"challenge\":" + std::to_string(s.challenge) + "}";
    }
    // SDK HTTP APIs are not generally thread-safe. All socket writes run
    // in the HTTP task; retain at most one queued status batch.
    if (send_pending_.exchange(true)) continue;
    auto* work = new (std::nothrow)
        Work{this, fd, client_generation_.load(), std::move(payload), {}};
    if (!work) {
      send_pending_ = false;
      continue;
    }
    Event event{};
    bool available = false;
    {
      std::lock_guard<std::mutex> lock(event_mutex_);
      if (event_count_) {
        event = events_[event_head_];
        event_head_ = (event_head_ + 1) % 100;
        --event_count_;
        available = true;
      }
    }
    if (available) {
      auto* j = cJSON_CreateObject();
      cJSON_AddStringToObject(j, "type", "EVENT");
      cJSON_AddStringToObject(j, "kind", event.kind);
      cJSON_AddStringToObject(j, "text", event.text);
      work->event = Json(j);
    }
    auto result = httpd_queue_work(
        server_,
        [](void* arg) {
          auto* w = static_cast<Work*>(arg);
          auto* self = w->self;
          if (self->client_ == w->fd &&
              self->client_generation_ == w->generation &&
              httpd_ws_get_fd_info(self->server_, w->fd) ==
                  HTTPD_WS_CLIENT_WEBSOCKET) {
            for (auto* data : {&w->status, &w->event})
              if (!data->empty()) {
                httpd_ws_frame_t f{};
                f.type = HTTPD_WS_TYPE_TEXT;
                f.payload = (uint8_t*)data->data();
                f.len = data->size();
                if (httpd_ws_send_frame_async(self->server_, w->fd, &f) !=
                    ESP_OK) {
                  httpd_sess_trigger_close(self->server_, w->fd);
                  break;
                }
              }
          }
          self->send_pending_ = false;
          delete w;
        },
        work);
    if (result != ESP_OK) {
      delete work;
      send_pending_ = false;
    }
  }
}
}  // namespace awcar
