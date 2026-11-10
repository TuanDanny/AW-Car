#include "sta_network.h"
#include "car/runtime.h"
#include "management.hpp"
#include <ssid_manager.h>
#include <cJSON.h>
#include <esp_log.h>
#include <esp_timer.h>
#include <esp_wifi.h>
#include <algorithm>
#include <cstring>

namespace {
#ifndef SIMPLE_BUILD_ID
#define SIMPLE_BUILD_ID "simplev1-dev"
#endif
void DescribeBrain(char* output,size_t capacity) { brain::Runtime::Get().Diagnostics(output,capacity); }
constexpr uint32_t kUp = 1, kDown = 2;
uint64_t Now() { return esp_timer_get_time()/1000; }
void Disconnect() {
    const auto err=esp_wifi_disconnect();
    if(err!=ESP_OK && err!=ESP_ERR_WIFI_NOT_CONNECT)
        ESP_LOGW("BrainSTA","disconnect failed: %s",esp_err_to_name(err));
}
}
void StaNetwork::Notify(NetworkEvent event, const std::string& data) {
    if (callback_) callback_(event, data);
}
void StaNetwork::Start(NetworkEventCallback callback) {
    callback_ = std::move(callback);
    configurations_ = xQueueCreate(1, sizeof(Credentials));
    ESP_ERROR_CHECK(configurations_ ? ESP_OK : ESP_ERR_NO_MEM);
    ESP_ERROR_CHECK(esp_netif_init());
    auto err = esp_event_loop_create_default();
    ESP_ERROR_CHECK(err == ESP_ERR_INVALID_STATE ? ESP_OK : err);
    netif_ = esp_netif_create_default_wifi_sta();
    ESP_ERROR_CHECK(netif_ ? ESP_OK : ESP_ERR_NO_MEM);
    ESP_ERROR_CHECK(esp_netif_set_hostname(netif_, "AW-Car-Brain"));
    wifi_init_config_t init = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&init));
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT, WIFI_EVENT_STA_DISCONNECTED, OnEvent, this, &wifi_handler_));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP, OnEvent, this, &ip_handler_));
    ESP_ERROR_CHECK(esp_wifi_start());
    ESP_ERROR_CHECK(esp_wifi_set_ps(WIFI_PS_NONE));
    ESP_ERROR_CHECK(xTaskCreate([](void* p) { static_cast<StaNetwork*>(p)->Run(); },
        "brain_sta", 6144, this, 3, &task_) == pdPASS ? ESP_OK : ESP_ERR_NO_MEM);
}
void StaNetwork::OnEvent(void* arg, esp_event_base_t base, int32_t id, void* data) {
    auto* self = static_cast<StaNetwork*>(arg);
    if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        const auto* event = static_cast<ip_event_got_ip_t*>(data);
        {
            std::lock_guard lock(self->state_mutex_);
            std::memcpy(self->ip_.data(), &event->ip_info.ip.addr, 4);
        }
        self->connected_ = true;
        self->result_ = 2;
        if (self->task_) xTaskNotify(self->task_, kUp, eSetBits);
    } else {
        self->connected_ = false;
        brain::Runtime::Get().SetCloud(false);
        if (self->task_) xTaskNotify(self->task_, kDown, eSetBits);
    }
}
bool StaNetwork::Configure(const simple::Frame& frame) {
    if (frame.size < 3) return false;
    const auto ss = frame.payload[0], pw = frame.payload[1];
    if (ss < 1 || ss > 32 || pw > 64 || frame.size != 2+ss+pw ||
        std::memchr(frame.payload.data()+2, 0, ss+pw)) return false;
    Credentials credentials;
    credentials.ssid_len = ss; credentials.pass_len = pw;
    std::memcpy(credentials.ssid, frame.payload.data()+2, ss);
    std::memcpy(credentials.password, frame.payload.data()+2+ss, pw);
    result_ = 1;
    const bool queued = xQueueOverwrite(configurations_, &credentials) == pdPASS;
    explicit_bzero(&credentials, sizeof(credentials));
    return queued;
}
void StaNetwork::FillState(simple::BrainState& state) {
    state.wifi_result = result_;
    {
        std::lock_guard lock(state_mutex_);
        std::memcpy(state.ssid.data(), ssid_.data(), std::min(ssid_.size(), state.ssid.size()));
        if (connected_) { state.flags |= simple::kWifiReady; state.ipv4 = ip_; }
    }
    wifi_ap_record_t ap{};
    if (connected_ && esp_wifi_sta_get_ap_info(&ap) == ESP_OK) state.rssi = ap.rssi;
}
std::string StaNetwork::Json() {
    simple::BrainState state;
    FillState(state);
    char ip[16];
    snprintf(ip, sizeof(ip), "%u.%u.%u.%u", state.ipv4[0],state.ipv4[1],state.ipv4[2],state.ipv4[3]);
    auto* json = cJSON_CreateObject();
    cJSON_AddStringToObject(json, "type", "wifi");
    cJSON_AddStringToObject(json, "name", "aw-car-simplev1");
    cJSON_AddStringToObject(json, "ssid", std::string(state.ssid.data(), strnlen(state.ssid.data(),32)).c_str());
    cJSON_AddStringToObject(json, "ip", ip);
    cJSON_AddNumberToObject(json, "rssi", state.rssi);
    char* encoded = cJSON_PrintUnformatted(json);
    std::string result = encoded ? encoded : "{}";
    cJSON_free(encoded); cJSON_Delete(json);
    return result;
}
void StaNetwork::Run() {
    auto& store = SsidManager::GetInstance();
    uint64_t next_attempt = Now(), connect_deadline = 0;
    uint32_t backoff = 1000;
    size_t index = 0;
    bool connecting = false;
    for (;;) {
        uint32_t events = 0;
        xTaskNotifyWait(0, UINT32_MAX, &events, pdMS_TO_TICKS(100));
        const auto now = Now();
        if (events & kDown) {
            connecting = false;
            if (result_ != 0) result_ = 3;
            Notify(NetworkEvent::Disconnected);
            next_attempt = now + backoff;
            backoff = std::min(backoff * 2, uint32_t(30000));
            ++index;
        }
        if (events & kUp) {
            connecting = false; backoff = 1000;
            std::string ssid;
            { std::lock_guard lock(state_mutex_); ssid = ssid_; }
            Notify(NetworkEvent::Connected, ssid);
            const auto rc=management::start("brain",SIMPLE_BUILD_ID,DescribeBrain);
            if(rc!=ESP_OK) ESP_LOGE("BrainSTA","management start failed: %s",esp_err_to_name(rc));
        }
        Credentials credentials;
        if (xQueueReceive(configurations_, &credentials, 0) == pdPASS) {
            // Same manager/namespace/keys as the activated firmware; never log credentials.
            const bool saved = store.AddSsid(credentials.ssid, credentials.password);
            if (saved) {
                connected_ = false; connecting = false;
                brain::Runtime::Get().SetCloud(false);
                Disconnect();
                Notify(NetworkEvent::Disconnected);
                result_ = 1; index = 0; backoff = 1000; next_attempt = now+500;
            } else result_ = 3;
            explicit_bzero(&credentials, sizeof(credentials));
        }
        if (connected_) continue;
        if (connecting && now >= connect_deadline) {
            Disconnect(); connecting = false;
            next_attempt = now+backoff;
            backoff = std::min(backoff*2, uint32_t(30000));
        }
        const auto& list = store.GetSsidList();
        if (connecting || now < next_attempt || list.empty()) continue;
        const auto& item = list[index % list.size()];
        wifi_config_t config{};
        std::memcpy(config.sta.ssid, item.ssid.data(), std::min(item.ssid.size(),sizeof(config.sta.ssid)));
        std::memcpy(config.sta.password, item.password.data(), std::min(item.password.size(),sizeof(config.sta.password)));
        config.sta.scan_method = WIFI_ALL_CHANNEL_SCAN;
        config.sta.threshold.authmode = item.password.empty() ? WIFI_AUTH_OPEN : WIFI_AUTH_WPA2_PSK;
        config.sta.pmf_cfg.capable = true;
        config.sta.failure_retry_cnt = 0;
        {
            std::lock_guard lock(state_mutex_); ssid_ = item.ssid;
        }
        auto err = esp_wifi_set_config(WIFI_IF_STA, &config);
        explicit_bzero(&config, sizeof(config));
        if (err == ESP_OK) { Notify(NetworkEvent::Connecting, item.ssid); err = esp_wifi_connect(); }
        if (err == ESP_OK) { connecting = true; connect_deadline = now+15000; }
        else { result_ = 3; next_attempt = now+backoff; backoff = std::min(backoff*2,uint32_t(30000)); }
    }
}
