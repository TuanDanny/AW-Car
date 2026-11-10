#pragma once
#include <cstddef>
#include <cstdint>
#include "esp_http_server.h"
namespace motion {
struct NetworkState {
    bool configured{},online{},connecting{},ap_started{};
    uint32_t attempts{},failures{},retry_ms{};
    uint16_t disconnect_reason{};
    uint8_t ap_channel{},clients{};
    int8_t rssi{};
    char ip[16]{},ssid[33]{};
};
void start_network();
bool configure_network(const char* ssid, size_t ssid_len, const char* password, size_t password_len);
NetworkState network_state();
bool request_on_ap(httpd_req_t* request);
}
