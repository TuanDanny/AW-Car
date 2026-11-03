#include "aw_car_network.h"

#include <cJSON.h>
#include <esp_event.h>
#include <esp_log.h>
#include <esp_random.h>
#include <esp_wifi.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <lwip/inet.h>

#include <cstring>

#include "brain_runtime.h"
#include "settings.h"
#include "ssid_manager.h"
#include "system_info.h"

namespace awcar {
void Network::Start(NetworkEventCallback cb) {
  callback_ = std::move(cb);
  Settings settings("aw_car", true);
  const auto saved_password = settings.GetString("ap_password");
  password_ = CONFIG_AWCAR_AP_PASSWORD;
  if (password_.empty()) password_ = saved_password;
  if (password_.size() < 8 || password_.size() > 63) {
    char p[17];
    snprintf(p, sizeof(p), "%08lx%08lx", (unsigned long)esp_random(),
             (unsigned long)esp_random());
    password_ = p;
  }
  if (password_ != saved_password) settings.SetString("ap_password", password_);
  ap_ssid_ = "AW-CAR";
  ESP_ERROR_CHECK(esp_netif_init());
  auto err = esp_event_loop_create_default();
  if (err != ESP_ERR_INVALID_STATE) ESP_ERROR_CHECK(err);
  sta_ = esp_netif_create_default_wifi_sta();
  ap_ = esp_netif_create_default_wifi_ap();
  esp_netif_ip_info_t ip{};
  ip.ip.addr = ipaddr_addr("192.168.4.1");
  ip.gw = ip.ip;
  ip.netmask.addr = ipaddr_addr("255.255.255.0");
  esp_netif_dhcps_stop(ap_);
  ESP_ERROR_CHECK(esp_netif_set_ip_info(ap_, &ip));
  ESP_ERROR_CHECK(esp_netif_dhcps_start(ap_));
  wifi_init_config_t init = WIFI_INIT_CONFIG_DEFAULT();
  ESP_ERROR_CHECK(esp_wifi_init(&init));
  ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
  ESP_ERROR_CHECK(esp_event_handler_register(
      WIFI_EVENT, ESP_EVENT_ANY_ID,
      [](void* arg, esp_event_base_t, int32_t id, void*) {
        auto* self = static_cast<Network*>(arg);
        if (id == WIFI_EVENT_STA_DISCONNECTED) {
          self->connected_ = false;
          self->reconnect_ = true;
          BrainRuntime::Get().CloudOnline(false);
          if (self->callback_) self->callback_(NetworkEvent::Disconnected, "");
        }
      },
      this));
  ESP_ERROR_CHECK(esp_event_handler_register(
      IP_EVENT, IP_EVENT_STA_GOT_IP,
      [](void* arg, esp_event_base_t, int32_t, void* data) {
        auto* self = static_cast<Network*>(arg);
        auto* event = static_cast<ip_event_got_ip_t*>(data);
        if ((event->ip_info.ip.addr & event->ip_info.netmask.addr) ==
            (ipaddr_addr("192.168.4.1") & event->ip_info.netmask.addr)) {
          ESP_LOGE(
              "AwCarNetwork",
              "STA subnet overlaps car AP; choose another Internet network");
          self->connected_ = false;
          return;
        }
        self->connected_ = true;
        self->reconnect_ = false;
        if (self->callback_) self->callback_(NetworkEvent::Connected, "");
      },
      this));
  wifi_config_t ap{};
  strncpy((char*)ap.ap.ssid, ap_ssid_.c_str(), sizeof(ap.ap.ssid));
  ap.ap.ssid_len = ap_ssid_.size();
  strncpy((char*)ap.ap.password, password_.c_str(), sizeof(ap.ap.password));
  ap.ap.authmode = WIFI_AUTH_WPA2_PSK;
  ap.ap.max_connection = 2;
  ap.ap.channel = 1;
  ap.ap.pmf_cfg.required = false;
  ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_APSTA));
  ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &ap));
  ESP_ERROR_CHECK(esp_wifi_start());
  ESP_ERROR_CHECK(esp_wifi_set_ps(WIFI_PS_NONE));
  xTaskCreate(
      [](void* arg) {
        auto* self = static_cast<Network*>(arg);
        for (;;) {
          if (self->reconnect_.exchange(false)) self->ConnectSaved();
          vTaskDelay(pdMS_TO_TICKS(3000));
          if (!self->connected_) self->reconnect_ = true;
        }
      },
      "car_wifi_retry", 4096, this, 2, nullptr);
}
void Network::ConnectSaved() {
  wifi_config_t cfg{};
  bool found = false;
  {
    std::lock_guard<std::mutex> lock(settings_mutex_);
    auto& list = SsidManager::GetInstance().GetSsidList();
    if (!list.empty()) {
      strncpy((char*)cfg.sta.ssid, list.front().ssid.c_str(),
              sizeof(cfg.sta.ssid));
      strncpy((char*)cfg.sta.password, list.front().password.c_str(),
              sizeof(cfg.sta.password));
      found = true;
    }
  }
  if (!found) return;
  cfg.sta.scan_method = WIFI_ALL_CHANNEL_SCAN;
  cfg.sta.failure_retry_cnt = 3;
  esp_wifi_set_config(WIFI_IF_STA, &cfg);
  esp_wifi_connect();
}
bool Network::Configure(const std::string& ssid, const std::string& password) {
  if (ssid.empty() || ssid.size() > 32 || password.size() > 63) return false;
  {
    std::lock_guard<std::mutex> lock(settings_mutex_);
    SsidManager::GetInstance().AddSsid(ssid, password);
  }
  esp_wifi_disconnect();
  connected_ = false;
  reconnect_ = true;
  return true;
}
std::string Network::Json() const {
  auto* root = cJSON_CreateObject();
  cJSON_AddStringToObject(root, "type", BOARD_TYPE);
  cJSON_AddStringToObject(root, "name", BOARD_NAME);
  cJSON_AddStringToObject(root, "manufacturer", "AW-Car");
  cJSON_AddStringToObject(root, "mac", SystemInfo::GetMacAddress().c_str());
  esp_netif_ip_info_t ip{};
  esp_netif_get_ip_info(sta_, &ip);
  char address[20];
  snprintf(address, sizeof(address), IPSTR, IP2STR(&ip.ip));
  cJSON_AddStringToObject(root, "ip", address);
  wifi_ap_record_t record{};
  if (esp_wifi_sta_get_ap_info(&record) == ESP_OK) {
    cJSON_AddStringToObject(root, "ssid", (char*)record.ssid);
    cJSON_AddNumberToObject(root, "rssi", record.rssi);
    cJSON_AddNumberToObject(root, "channel", record.primary);
  }
  char* text = cJSON_PrintUnformatted(root);
  std::string result = text ? text : "{}";
  cJSON_free(text);
  cJSON_Delete(root);
  return result;
}
}  // namespace awcar
