#pragma once
#include <cJSON.h>
#include <esp_http_server.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/task.h>

#include <array>
#include <atomic>
#include <mutex>
#include <string>

#include "control_core.h"
#include "voice_gate.h"

class AwCarStatusLed;
class Display;
namespace awcar {
class Network;
class BrainRuntime {
 public:
  static BrainRuntime& Get() {
    static BrainRuntime instance;
    return instance;
  }
  void Start(AwCarStatusLed* status_led, Display* display, Network* network);
  void CloudOnline(bool online);
  void CloudSession(const std::string& session);
  void ChatEvent(const char* kind, const char* text, const char* session = "");
  VoiceTicket CaptureVoice(const std::string& name, int id,
                           const std::string& session);
  bool CheckVoice(const VoiceTicket& ticket);
  bool StopRequested() const { return stop_requested_; }
  void Stop();
  std::string Snapshot();
  void ShowPairing();
  bool CanConfigure();

 private:
  BrainRuntime();
  ControlCore core_;
  std::mutex mutex_, event_mutex_, web_mutex_;
  AwCarStatusLed* status_led_ = nullptr;
  Display* display_ = nullptr;
  Network* network_ = nullptr;
  TaskHandle_t control_task_ = nullptr, uart_task_ = nullptr,
               uart_rx_task_ = nullptr;
  httpd_handle_t server_ = nullptr;
  std::atomic<int> client_{-1};
  std::atomic<bool> stop_requested_{false};
  std::atomic<bool> running_{false};
  uint32_t observed_epoch_ = 1;
  Mode observed_mode_ = Mode::Manual;
  VoiceGate voice_;
  VoiceTicket executing_ticket_;
  uint64_t last_pairing_ = 0, last_client_ = 0;
  struct Event {
    char kind[24];
    char text[512];
  };
  Event* events_ = nullptr;
  size_t event_head_ = 0, event_count_ = 0;
  char pin_[7]{}, cookie_[65]{};
  std::atomic<uint32_t> last_client_ms_{0};
  std::atomic<uint32_t> client_generation_{0};
  std::atomic<bool> send_pending_{false};
  std::atomic<uint32_t> rx_errors_{0}, uart_status_frames_{0},
      uart_rx_bytes_{0}, uart_driver_errors_{0};
  std::array<uint32_t, 128> web_latency_us_{};
  uint32_t web_latency_count_ = 0, web_accepted_ = 0, web_rejected_ = 0;
  uint64_t pending_web_at_ = 0, login_window_ = 0;
  unsigned login_failures_ = 0;
  void TickLocked(uint64_t now);
  void Wake();
  void ControlTask();
  void UartTask();
  void UartReceiveTask(QueueHandle_t events);
  struct WebStats {
    uint32_t handshakes = 0, closes = 0, heartbeats = 0, pongs = 0;
    uint32_t auth_rejects = 0, origin_rejects = 0, busy_rejects = 0;
    uint32_t send_failures = 0, receive_failures = 0, protocol_errors = 0,
             peer_closes = 0;
    uint32_t queue_failures = 0, queue_skips = 0, stale_work = 0,
             queue_max_us = 0;
    uint32_t heartbeat_timeouts = 0, open_sockets = 0, peak_sockets = 0;
    int close_code = 0, socket_error = 0;
    const char* close_reason = "none";
  } web_stats_;
  struct WebWork {
    int fd = -1;
    uint32_t generation = 0;
    uint64_t at = 0;
  } web_work_;
  bool dashboard_revoked_ = true;
  uint64_t next_ping_ = 0;
  void CloseDashboard(const char* reason, int code = 1001, bool frame = true);
  void SocketClosed(int fd);
  void ObserveSocket(const char* event, int value);
  void PumpWeb(int fd, uint32_t generation, uint64_t queued_at);
  void WebTask();
  void StartWeb();
  void RegisterTools();
  bool Auth(httpd_req_t* req);
  bool Origin(httpd_req_t* req);
  esp_err_t Request(httpd_req_t* req);
  esp_err_t WebSocketRequest(httpd_req_t* req);
  std::string Dispatch(const cJSON* data);
};
}  // namespace awcar
