#include "runtime.hpp"
#include "network_manager.hpp"
#include <cstring>
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "nvs_flash.h"
#include "management.hpp"
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
    motion::start_network();
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT,ESP_EVENT_ANY_ID,wifi_event,nullptr));
    motion::start_web();
    management::start_boot_guard([] { motion::Runtime::get().check_local_boot(); });
    ESP_LOGI("simple_motion","build=%s AP+STA ready http://192.168.4.1; UART13/14 SPI15/16/4/5 STBY10; PID=off",SIMPLE_BUILD_ID);
}
