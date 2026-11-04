#include "aw_car_network.h"

#include <esp_event.h>
#include <esp_log.h>
#include <esp_random.h>
#include <esp_timer.h>
#include <esp_wifi.h>
#include <freertos/task.h>
#include <lwip/inet.h>

#include <cstring>

#include "brain_runtime.h"
#include "settings.h"
#include "ssid_manager.h"
#include "system_info.h"
namespace awcar {
namespace {
constexpr int kGotIp = 1000, kLostIp = 1001, kConfigure = 1002;
uint64_t Millis() { return uint64_t(esp_timer_get_time()) / 1000; }
StaFailure Classify(uint16_t reason) {
  if (reason == WIFI_REASON_AUTH_FAIL ||
      reason == WIFI_REASON_4WAY_HANDSHAKE_TIMEOUT ||
      reason == WIFI_REASON_HANDSHAKE_TIMEOUT)
    return StaFailure::Authentication;
  if (reason == WIFI_REASON_NO_AP_FOUND) return StaFailure::MissingAp;
  return StaFailure::Transient;
}
}  // namespace
bool Network::Check(const char* operation, esp_err_t code, esp_err_t allowed) {
  if (code == ESP_OK || code == allowed) return true;
  {
    std::lock_guard<std::mutex> lock(stats_mutex_);
    ++stats_.errors;
    stats_.last_error = code;
    snprintf(stats_.operation, sizeof(stats_.operation), "%s", operation);
  }
  ESP_LOGW("AwCarNetwork", "op=%s error=%s (%d)", operation,
           esp_err_to_name(code), code);
  return false;
}
void Network::Enqueue(const Event& event) {
  if (xQueueSend(events_, &event, 0) != pdTRUE) ++queue_drops_;
}
void Network::Start(NetworkEventCallback cb) {
  callback_ = std::move(cb);
  Settings settings("aw_car", true);
  const auto saved = settings.GetString("ap_password");
  password_ = CONFIG_AWCAR_AP_PASSWORD;
  if (password_.empty()) password_ = saved;
  if (password_.size() < 8 || password_.size() > 63) {
    char value[17];
    snprintf(value, sizeof(value), "%08lx%08lx", (unsigned long)esp_random(),
             (unsigned long)esp_random());
    password_ = value;
  }
  if (password_ != saved) settings.SetString("ap_password", password_);
  ap_ssid_ = "AW-CAR";
  events_ = xQueueCreate(16, sizeof(Event));
  ESP_ERROR_CHECK(events_ ? ESP_OK : ESP_ERR_NO_MEM);
  ESP_ERROR_CHECK(esp_netif_init());
  auto err = esp_event_loop_create_default();
  if (err != ESP_ERR_INVALID_STATE) ESP_ERROR_CHECK(err);
  sta_ = esp_netif_create_default_wifi_sta();
  ap_ = esp_netif_create_default_wifi_ap();
  ESP_ERROR_CHECK(sta_ && ap_ ? ESP_OK : ESP_ERR_NO_MEM);
  esp_netif_ip_info_t ip{};
  ip.ip.addr = ipaddr_addr("192.168.4.1");
  ip.gw = ip.ip;
  ip.netmask.addr = ipaddr_addr("255.255.255.0");
  const auto dhcps_stop = esp_netif_dhcps_stop(ap_);
  if (!Check("dhcps_stop", dhcps_stop, ESP_ERR_ESP_NETIF_DHCP_ALREADY_STOPPED))
    ESP_ERROR_CHECK(dhcps_stop);
  ESP_ERROR_CHECK(esp_netif_set_ip_info(ap_, &ip));
  ESP_ERROR_CHECK(esp_netif_dhcps_start(ap_));
  wifi_init_config_t init = WIFI_INIT_CONFIG_DEFAULT();
  ESP_ERROR_CHECK(esp_wifi_init(&init));
  ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
  ESP_ERROR_CHECK(esp_event_handler_register(
      WIFI_EVENT, ESP_EVENT_ANY_ID,
      [](void* p, esp_event_base_t, int32_t id, void* data) {
        auto* self = static_cast<Network*>(p);
        Event e;
        e.id = id;
        switch (id) {
          case WIFI_EVENT_STA_CONNECTED:
            e.channel = static_cast<wifi_event_sta_connected_t*>(data)->channel;
            break;
          case WIFI_EVENT_STA_DISCONNECTED:
            e.reason =
                static_cast<wifi_event_sta_disconnected_t*>(data)->reason;
            break;
          case WIFI_EVENT_AP_STADISCONNECTED:
            e.reason =
                static_cast<wifi_event_ap_stadisconnected_t*>(data)->reason;
            break;
          case WIFI_EVENT_AP_START:
          case WIFI_EVENT_AP_STOP:
          case WIFI_EVENT_AP_STACONNECTED:
            break;
          default:
            return;
        }
        self->Enqueue(e);
      },
      this));
  ESP_ERROR_CHECK(esp_event_handler_register(
      IP_EVENT, ESP_EVENT_ANY_ID,
      [](void* p, esp_event_base_t, int32_t id, void* data) {
        Event e;
        if (id == IP_EVENT_STA_GOT_IP) {
          e.id = kGotIp;
          e.ip = static_cast<ip_event_got_ip_t*>(data)->ip_info;
        } else if (id == IP_EVENT_STA_LOST_IP)
          e.id = kLostIp;
        else
          return;
        static_cast<Network*>(p)->Enqueue(e);
      },
      this));
  wifi_config_t ap{};
  memcpy(ap.ap.ssid, ap_ssid_.data(), ap_ssid_.size());
  ap.ap.ssid_len = ap_ssid_.size();
  memcpy(ap.ap.password, password_.data(), password_.size());
  ap.ap.authmode = WIFI_AUTH_WPA2_PSK;
  ap.ap.max_connection = 2;
  ap.ap.channel = 1;
  ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_APSTA));
  ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &ap));
  ESP_ERROR_CHECK(esp_wifi_start());
  ESP_ERROR_CHECK(esp_wifi_set_ps(WIFI_PS_NONE));
  ESP_ERROR_CHECK(xTaskCreate([](void* p) { static_cast<Network*>(p)->Run(); },
                              "car_network", 6144, this, 2, nullptr) == pdPASS
                      ? ESP_OK
                      : ESP_ERR_NO_MEM);
}
void Network::Notify(bool online) {
  const bool previous = connected_.exchange(online);
  if (!online) BrainRuntime::Get().CloudOnline(false);
  if (previous != online && callback_)
    callback_(online ? NetworkEvent::Connected : NetworkEvent::Disconnected,
              "");
}
void Network::Run() {
  wifi_config_t cfg{};
  auto& list = SsidManager::GetInstance().GetSsidList();
  if (!list.empty()) {
    strncpy((char*)cfg.sta.ssid, list.front().ssid.c_str(),
            sizeof(cfg.sta.ssid));
    strncpy((char*)cfg.sta.password, list.front().password.c_str(),
            sizeof(cfg.sta.password));
  }
  policy_.Configure(cfg.sta.ssid[0] != 0, Millis());
  bool configuring = false, cancel_wait = false;
  uint64_t cancel_until = 0, refresh_at = 0, report_at = 0;
  uint32_t observed_drops = 0;
  for (;;) {
    Event e;
    const bool available =
        xQueueReceive(events_, &e, pdMS_TO_TICKS(100)) == pdTRUE;
    const uint64_t now = Millis();
    if (available) {
      if (e.id == kConfigure) {
        Notify(false);
        cfg = {};
        memcpy(cfg.sta.ssid, e.ssid, strlen(e.ssid));
        memcpy(cfg.sta.password, e.password, strlen(e.password));
        SsidManager::GetInstance().AddSsid(e.ssid, e.password);
        configuring = true;
        cancel_wait = true;
        cancel_until = now + 3000;
        const auto code = esp_wifi_disconnect();
        if (code == ESP_ERR_WIFI_NOT_CONNECT) cancel_wait = false;
        Check("disconnect_configure", code, ESP_ERR_WIFI_NOT_CONNECT);
      } else if (e.id == WIFI_EVENT_STA_DISCONNECTED) {
        Notify(false);
        {
          std::lock_guard<std::mutex> lock(stats_mutex_);
          ++stats_.sta_disconnects;
          stats_.sta_reason = e.reason;
          stats_.associated = stats_.ip_valid = false;
        }
        ESP_LOGI("AwCarNetwork",
                 "sta_disconnect reason=%u attempt=%lu since_attempt_ms=%llu",
                 e.reason, (unsigned long)policy_.attempts,
                 (unsigned long long)(now - policy_.last_attempt));
        if (cancel_wait)
          cancel_wait = false;
        else if (!configuring)
          policy_.Failed(Classify(e.reason), now);
      } else if (e.id == WIFI_EVENT_STA_CONNECTED && !configuring &&
                 !cancel_wait) {
        policy_.Associated(now);
        cfg.sta.channel = e.channel;
        std::lock_guard<std::mutex> lock(stats_mutex_);
        stats_.associated = true;
      } else if (e.id == kGotIp && !configuring && !cancel_wait) {
        if ((e.ip.ip.addr & e.ip.netmask.addr) ==
            (ipaddr_addr("192.168.4.1") & e.ip.netmask.addr)) {
          Notify(false);
          policy_.Failed(StaFailure::Authentication, now);
          cancel_wait = true;
          cancel_until = now + 3000;
          Check("disconnect_subnet_overlap", esp_wifi_disconnect(),
                ESP_ERR_WIFI_NOT_CONNECT);
        } else if (policy_.GotIp(now)) {
          {
            std::lock_guard<std::mutex> lock(stats_mutex_);
            stats_.ip_valid = true;
          }
          Notify(true);
          ESP_LOGI("AwCarNetwork", "sta_ip_ready attempts=%lu",
                   (unsigned long)policy_.attempts);
        }
      } else if (e.id == kLostIp) {
        Notify(false);
        policy_.Associated(now);
        std::lock_guard<std::mutex> lock(stats_mutex_);
        stats_.ip_valid = false;
      } else if (e.id == WIFI_EVENT_AP_START || e.id == WIFI_EVENT_AP_STOP) {
        std::lock_guard<std::mutex> lock(stats_mutex_);
        stats_.ap_started = e.id == WIFI_EVENT_AP_START;
      } else if (e.id == WIFI_EVENT_AP_STACONNECTED ||
                 e.id == WIFI_EVENT_AP_STADISCONNECTED) {
        {
          std::lock_guard<std::mutex> lock(stats_mutex_);
          if (e.id == WIFI_EVENT_AP_STACONNECTED)
            ++stats_.ap_clients;
          else {
            if (stats_.ap_clients) --stats_.ap_clients;
            ++stats_.ap_disconnects;
            stats_.ap_reason = e.reason;
          }
        }
        ESP_LOGI("AwCarNetwork", "ap_client event=%d reason=%u", e.id,
                 e.reason);
      }
    }
    if (configuring && !cancel_wait) {
      configuring = false;
      policy_.Configure(cfg.sta.ssid[0] != 0, now);
    }
    if (cancel_wait && now >= cancel_until) {
      cancel_wait = false;
      if (configuring) {
        configuring = false;
        policy_.Configure(cfg.sta.ssid[0] != 0, now);
      } else
        policy_.Failed(StaFailure::Transient, now);
    }
    if (queue_drops_.load() != observed_drops) {
      observed_drops = queue_drops_;
      Notify(false);
      policy_.Failed(StaFailure::Transient, now);
      cancel_wait = true;
      cancel_until = now + 3000;
      Check("disconnect_event_overflow", esp_wifi_disconnect(),
            ESP_ERR_WIFI_NOT_CONNECT);
    }
    if (!cancel_wait && policy_.TimedOut(now)) {
      Notify(false);
      policy_.Failed(StaFailure::Transient, now);
      cancel_wait = true;
      cancel_until = now + 3000;
      const auto code = esp_wifi_disconnect();
      if (code == ESP_ERR_WIFI_NOT_CONNECT) cancel_wait = false;
      Check("disconnect_attempt_timeout", code, ESP_ERR_WIFI_NOT_CONNECT);
    }
    bool ap_client = false;
    {
      std::lock_guard<std::mutex> lock(stats_mutex_);
      ap_client = stats_.ap_clients > 0;
    }
    if (!cancel_wait && !configuring && policy_.StartDue(now, ap_client)) {
      cfg.sta.scan_method = WIFI_FAST_SCAN;
      cfg.sta.failure_retry_cnt = 0;
      // Full default scans measured ~2.8s with the saved AP absent, exceeding
      // the independent 2s dashboard lease. Shorten off-channel dwell while
      // serving AP clients; keep APSTA and all safety deadlines unchanged.
      wifi_scan_default_params_t scan{};
      scan.scan_time.active.max = ap_client ? 40 : 120;
      scan.scan_time.passive = ap_client ? 120 : 360;
      scan.home_chan_dwell_time = ap_client ? 60 : 30;
      if (!Check("set_scan_parameters", esp_wifi_set_scan_parameters(&scan))) {
        policy_.Failed(StaFailure::Transient, now);
        continue;
      }
      const auto config_result = esp_wifi_set_config(WIFI_IF_STA, &cfg);
      if (!Check("sta_set_config", config_result) ||
          !Check("sta_connect", esp_wifi_connect()))
        policy_.Failed(StaFailure::Transient, now);
      ESP_LOGI("AwCarNetwork",
               "sta_attempt=%lu hint_channel=%u scan_active_ms=%lu "
               "scan_passive_ms=%lu home_ms=%u",
               (unsigned long)policy_.attempts, cfg.sta.channel,
               (unsigned long)scan.scan_time.active.max,
               (unsigned long)scan.scan_time.passive,
               scan.home_chan_dwell_time);
    }
    if (now >= refresh_at) {
      Refresh();
      refresh_at = now + 2000;
    }
    if (now >= report_at) {
      Stats status;
      {
        std::lock_guard<std::mutex> lock(stats_mutex_);
        status = stats_;
      }
      ESP_LOGI(
          "AwCarNetwork",
          "health phase=%s attempts=%lu failures=%lu reason=%u ap_clients=%lu "
          "channel=%d ip_valid=%d dhcpc=%d dhcps=%d errors=%lu",
          ReconnectPolicy::Name(policy_.phase), (unsigned long)policy_.attempts,
          (unsigned long)policy_.failures, status.sta_reason,
          (unsigned long)status.ap_clients, status.channel,
          int(connected_.load()), status.dhcpc, status.dhcps,
          (unsigned long)status.errors);
      report_at = now + 5000;
    }
    {
      std::lock_guard<std::mutex> lock(stats_mutex_);
      stats_.phase = policy_.phase;
      stats_.attempts = policy_.attempts;
      stats_.failures = policy_.failures;
      stats_.burst = policy_.burst;
      stats_.retry_at = policy_.NextAttempt(ap_client);
      stats_.queue_drops = queue_drops_;
    }
  }
}
bool Network::Configure(const std::string& ssid, const std::string& password) {
  if (ssid.empty() || ssid.size() > 32 || password.size() > 63) return false;
  Event e;
  e.id = kConfigure;
  memcpy(e.ssid, ssid.data(), ssid.size());
  memcpy(e.password, password.data(), password.size());
  return xQueueSend(events_, &e, 0) == pdTRUE;
}
void Network::Refresh() {
  uint8_t primary = 0;
  wifi_second_chan_t second;
  const bool channel_ok =
      Check("get_channel", esp_wifi_get_channel(&primary, &second));
  esp_netif_dhcp_status_t client{}, server{};
  const bool client_ok =
      Check("dhcpc_status", esp_netif_dhcpc_get_status(sta_, &client));
  const bool server_ok =
      Check("dhcps_status", esp_netif_dhcps_get_status(ap_, &server));
  esp_netif_ip_info_t ip{}, ap_ip{};
  const bool ip_ok = Check("sta_ip_info", esp_netif_get_ip_info(sta_, &ip));
  Check("ap_ip_info", esp_netif_get_ip_info(ap_, &ap_ip));
  wifi_sta_list_t stations{};
  const bool stations_ok =
      Check("ap_sta_list", esp_wifi_ap_get_sta_list(&stations));
  wifi_ap_record_t record{};
  const auto result = esp_wifi_sta_get_ap_info(&record);
  Check("sta_ap_info", result, ESP_ERR_WIFI_NOT_CONNECT);
  std::lock_guard<std::mutex> lock(stats_mutex_);
  if (stations_ok) stats_.ap_clients = stations.num;
  stats_.channel = channel_ok ? primary : 0;
  stats_.radio_valid = result == ESP_OK;
  stats_.rssi = record.rssi;
  snprintf(stats_.ssid, sizeof(stats_.ssid), "%s", (const char*)record.ssid);
  stats_.dhcpc = client_ok ? int(client) : -1;
  stats_.dhcps = server_ok ? int(server) : -1;
  snprintf(stats_.ip, sizeof(stats_.ip), IPSTR, IP2STR(&ip.ip));
  snprintf(stats_.ap_ip, sizeof(stats_.ap_ip), IPSTR, IP2STR(&ap_ip.ip));
  stats_.ip_valid = connected_ && ip_ok && ip.ip.addr;
}
cJSON* Network::Diagnostics() const {
  Stats s;
  {
    std::lock_guard<std::mutex> lock(stats_mutex_);
    s = stats_;
  }
  auto* j = cJSON_CreateObject();
  cJSON_AddStringToObject(j, "mode", "APSTA");
  cJSON_AddStringToObject(j, "sta_state", ReconnectPolicy::Name(s.phase));
  cJSON_AddBoolToObject(j, "ip_valid", s.ip_valid);
  cJSON_AddBoolToObject(j, "associated", s.associated);
  cJSON_AddBoolToObject(j, "ap_started", s.ap_started);
  cJSON_AddNumberToObject(j, "attempts", s.attempts);
  cJSON_AddNumberToObject(j, "failures", s.failures);
  const auto now = Millis();
  cJSON_AddNumberToObject(j, "burst", s.burst);
  cJSON_AddNumberToObject(j, "retry_in_ms",
                          s.retry_at > now ? s.retry_at - now : 0);
  cJSON_AddNumberToObject(j, "sta_disconnects", s.sta_disconnects);
  cJSON_AddNumberToObject(j, "sta_reason", s.sta_reason);
  cJSON_AddNumberToObject(j, "ap_disconnects", s.ap_disconnects);
  cJSON_AddNumberToObject(j, "ap_reason", s.ap_reason);
  cJSON_AddNumberToObject(j, "ap_clients", s.ap_clients);
  cJSON_AddNumberToObject(j, "ap_channel", s.channel);
  if (s.radio_valid)
    cJSON_AddNumberToObject(j, "rssi", s.rssi);
  else
    cJSON_AddNullToObject(j, "rssi");
  cJSON_AddNumberToObject(j, "dhcpc", s.dhcpc);
  cJSON_AddNumberToObject(j, "dhcps", s.dhcps);
  cJSON_AddStringToObject(j, "sta_ip", s.ip_valid ? s.ip : "");
  cJSON_AddStringToObject(j, "ap_ip", s.ap_ip);
  cJSON_AddNumberToObject(j, "api_errors", s.errors);
  cJSON_AddNumberToObject(j, "last_error", s.last_error);
  cJSON_AddStringToObject(j, "last_error_op", s.operation);
  cJSON_AddNumberToObject(j, "queue_drops", s.queue_drops);
  return j;
}
std::string Network::Json() const {
  auto* j = Diagnostics();
  Stats s;
  {
    std::lock_guard<std::mutex> lock(stats_mutex_);
    s = stats_;
  }
  cJSON_AddStringToObject(j, "ip", s.ip_valid ? s.ip : "");
  cJSON_AddStringToObject(j, "ssid", s.radio_valid ? s.ssid : "");
  cJSON_AddNumberToObject(j, "channel", s.channel);
  cJSON_AddStringToObject(j, "type", BOARD_TYPE);
  cJSON_AddStringToObject(j, "name", BOARD_NAME);
  cJSON_AddStringToObject(j, "manufacturer", "AW-Car");
  cJSON_AddStringToObject(j, "mac", SystemInfo::GetMacAddress().c_str());
  char* value = cJSON_PrintUnformatted(j);
  std::string out = value ? value : "{}";
  cJSON_free(value);
  cJSON_Delete(j);
  return out;
}
}  // namespace awcar
