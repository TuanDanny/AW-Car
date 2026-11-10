#include "runtime.hpp"
#include <cstring>
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "nvs_flash.h"
#ifndef SIMPLE_BUILD_ID
#define SIMPLE_BUILD_ID "simplev1-dev"
#endif

namespace {
void wifi_event(void*,esp_event_base_t,int32_t id,void* data) {
    if(id==WIFI_EVENT_AP_STACONNECTED) {
        const auto* event=static_cast<wifi_event_ap_staconnected_t*>(data);
        ESP_LOGI("simple_ap","client_join aid=%d",event->aid);
    } else if(id==WIFI_EVENT_AP_STADISCONNECTED) {
        const auto* event=static_cast<wifi_event_ap_stadisconnected_t*>(data);
        ESP_LOGI("simple_ap","client_leave aid=%d reason=%d",event->aid,event->reason);
        // WS close or the independent Manual500ms deadline owns motion stop.
        // Another station leaving must not stop the current controller.
    }
}
}
extern "C" void app_main() {
    // Refuse NVS init errors; never erase stored identities/configuration implicitly.
    ESP_ERROR_CHECK(nvs_flash_init());
    motion::Runtime::get().start();
    ESP_ERROR_CHECK(esp_netif_init());ESP_ERROR_CHECK(esp_event_loop_create_default());
    configASSERT(esp_netif_create_default_wifi_ap());
    const wifi_init_config_t init=WIFI_INIT_CONFIG_DEFAULT();ESP_ERROR_CHECK(esp_wifi_init(&init));
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT,ESP_EVENT_ANY_ID,wifi_event,nullptr));
    wifi_config_t wifi{};std::memcpy(wifi.ap.ssid,"AW-CAR",6);wifi.ap.ssid_len=6;
    std::memcpy(wifi.ap.password,"123456789",9);wifi.ap.channel=1;wifi.ap.max_connection=4;
    wifi.ap.authmode=WIFI_AUTH_WPA2_PSK;wifi.ap.pmf_cfg.required=false;
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_AP));ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP,&wifi));
    ESP_ERROR_CHECK(esp_wifi_start());
    motion::start_web();
    ESP_LOGI("simple_motion","build=%s AP-only ready http://192.168.4.1; UART13/14 SPI15/16/4/5 STBY10; PID=off",SIMPLE_BUILD_ID);
}
