#pragma once
#include <cJSON.h>
#include <esp_netif.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>

#include <atomic>
#include <mutex>
#include <string>

#include "board.h"
#include "network_policy.h"
namespace awcar {
class Network {
 public:
  void Start(NetworkEventCallback callback);
  bool Configure(const std::string& ssid, const std::string& password);
  bool Connected() const { return connected_; }
  esp_netif_t* Ap() const { return ap_; }
  const std::string& Password() const { return password_; }
  const std::string& Ssid() const { return ap_ssid_; }
  std::string Json() const;
  cJSON* Diagnostics() const;

 private:
  struct Event {
    int id = 0;
    uint16_t reason = 0;
    uint8_t channel = 0;
    esp_netif_ip_info_t ip{};
    char ssid[33]{}, password[64]{};
  };
  struct Stats {
    StaPhase phase = StaPhase::NoCredentials;
    uint32_t attempts = 0, failures = 0, burst = 0, sta_disconnects = 0,
             ap_disconnects = 0;
    uint32_t errors = 0, ap_clients = 0, queue_drops = 0;
    uint16_t sta_reason = 0, ap_reason = 0;
    int channel = 0, rssi = 0, dhcpc = -1, dhcps = -1, last_error = 0;
    bool associated = false, ap_started = false, ip_valid = false,
         radio_valid = false;
    uint64_t retry_at = 0;
    char ip[20]{}, ap_ip[20]{}, operation[40]{}, ssid[33]{};
  };
  esp_netif_t* ap_ = nullptr;
  esp_netif_t* sta_ = nullptr;
  NetworkEventCallback callback_;
  std::atomic<bool> connected_{false};
  std::atomic<uint32_t> queue_drops_{0};
  QueueHandle_t events_ = nullptr;
  std::string ap_ssid_, password_;
  mutable std::mutex stats_mutex_;
  Stats stats_{};
  ReconnectPolicy policy_;
  void Enqueue(const Event& event);
  void Run();
  bool Check(const char* operation, esp_err_t code, esp_err_t allowed = ESP_OK);
  void Notify(bool online);
  void Refresh();
};
}  // namespace awcar
