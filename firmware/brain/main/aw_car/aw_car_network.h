#pragma once
#include <esp_netif.h>

#include <atomic>
#include <mutex>
#include <string>

#include "board.h"

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

 private:
  esp_netif_t* ap_ = nullptr;
  esp_netif_t* sta_ = nullptr;
  NetworkEventCallback callback_;
  std::atomic<bool> connected_{false}, reconnect_{true};
  std::string ap_ssid_, password_;
  mutable std::mutex settings_mutex_;
  void ConnectSaved();
};
}  // namespace awcar
