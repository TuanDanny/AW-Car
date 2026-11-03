#pragma once
#include <cJSON.h>
#include <esp_http_server.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#include <array>
#include <atomic>
#include <mutex>
#include <string>

#include "control_core.h"
#include "voice_gate.h"

class AwCarRgbLight;
class Display;
namespace awcar {
class Network;
class BrainRuntime {
 public:
  static BrainRuntime& Get() {
    static BrainRuntime instance;
    return instance;
  }
  void Start(AwCarRgbLight* rgb, Display* display, Network* network);
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
  std::mutex mutex_, event_mutex_;
  AwCarRgbLight* rgb_ = nullptr;
  Display* display_ = nullptr;
  Network* network_ = nullptr;
  TaskHandle_t control_task_ = nullptr, uart_task_ = nullptr;
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
  std::atomic<uint32_t> rx_errors_{0};
  std::array<uint32_t, 128> web_latency_us_{};
  uint32_t web_latency_count_ = 0, web_accepted_ = 0, web_rejected_ = 0;
  uint64_t pending_web_at_ = 0, login_window_ = 0;
  unsigned login_failures_ = 0;
  void TickLocked(uint64_t now);
  void Wake();
  void ControlTask();
  void UartTask();
  void WebTask();
  void StartWeb();
  void RegisterTools();
  bool Auth(httpd_req_t* req);
  bool Origin(httpd_req_t* req);
  esp_err_t Request(httpd_req_t* req);
  std::string Dispatch(const cJSON* data);
};
}  // namespace awcar
