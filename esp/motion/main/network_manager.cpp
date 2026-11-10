#include "network_manager.hpp"
#include "runtime.hpp"
#include "management.hpp"
#include <cstdio>
#include "simple/network_policy.hpp"
#include <cstring>
#include <atomic>
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "lwip/sockets.h"
#include "nvs.h"

namespace motion {
namespace {
struct Credentials { char ssid[33]{}; char password[65]{}; };
QueueHandle_t changes{};
TaskHandle_t worker{};
esp_netif_t *ap_netif{},*sta_netif{};
portMUX_TYPE state_mux=portMUX_INITIALIZER_UNLOCKED;
NetworkState published{};
std::atomic<uint16_t> last_reason{0};
constexpr uint32_t kUp=1,kDown=2;
constexpr const char* tag="motion_network";
#ifndef SIMPLE_BUILD_ID
#define SIMPLE_BUILD_ID "simplev1-dev"
#endif
void describe_motion(char* out,size_t size) {
    const auto s=Runtime::get().snapshot();
    std::snprintf(out,size,"{\"mode\":\"%s\",\"action\":\"%s\",\"left\":%d,\"right\":%d,\"generation\":%lu,\"reason\":\"%s\",\"fpga\":%d,\"uart_errors\":%lu,\"spi_errors\":%lu}",
        s.car.mode==simple::Mode::Manual?"manual":"ai",simple::action_name(s.car.action),s.car.left,s.car.right,
        static_cast<unsigned long>(s.car.generation),simple::reason_name(s.car.reason),s.car.fpga_link,
        static_cast<unsigned long>(s.uart_errors),static_cast<unsigned long>(s.spi_errors));
}
uint64_t now_ms() { return esp_timer_get_time()/1000; }
void disconnect() {
    const auto rc=esp_wifi_disconnect();
    if(rc!=ESP_OK && rc!=ESP_ERR_WIFI_NOT_CONNECT) ESP_LOGW(tag,"disconnect err=%s",esp_err_to_name(rc));
}
void event(void*,esp_event_base_t base,int32_t id,void* data) {
    if(base==IP_EVENT && id==IP_EVENT_STA_GOT_IP) {
        if(worker) xTaskNotify(worker,kUp,eSetBits);
    } else if(base==WIFI_EVENT && id==WIFI_EVENT_STA_DISCONNECTED) {
        const auto* e=static_cast<wifi_event_sta_disconnected_t*>(data);
        last_reason=e->reason;
        ESP_LOGW(tag,"STA disconnect reason=%u",unsigned(e->reason));
        if(worker) xTaskNotify(worker,kDown,eSetBits);
    } else if(base==IP_EVENT && id==IP_EVENT_STA_LOST_IP) {
        if(worker) xTaskNotify(worker,kDown,eSetBits);
    }
}
bool save(const Credentials& c) {
    nvs_handle_t handle{};
    auto rc=nvs_open("simple_sta",NVS_READWRITE,&handle);
    if(rc!=ESP_OK) return false;
    rc=nvs_set_str(handle,"ssid",c.ssid);
    if(rc==ESP_OK) rc=nvs_set_str(handle,"pass",c.password);
    if(rc==ESP_OK) rc=nvs_commit(handle);
    nvs_close(handle);return rc==ESP_OK;
}
bool load(Credentials& c) {
    nvs_handle_t handle{};
    if(nvs_open("simple_sta",NVS_READONLY,&handle)!=ESP_OK) return false;
    size_t ss=sizeof(c.ssid),ps=sizeof(c.password);
    const auto a=nvs_get_str(handle,"ssid",c.ssid,&ss),b=nvs_get_str(handle,"pass",c.password,&ps);
    nvs_close(handle);
    if(a!=ESP_OK || b!=ESP_OK) { explicit_bzero(&c,sizeof(c));return false; }
    return c.ssid[0]!=0;
}
void run(void*) {
    Credentials current{};simple::NetworkPolicy policy;NetworkState state{};state.ap_started=true;
    bool apply=load(current);state.configured=apply;
    if(apply) policy.configure(now_ms());
    for(;;) {
        uint32_t events=0;xTaskNotifyWait(0,UINT32_MAX,&events,pdMS_TO_TICKS(100));
        auto now=now_ms();
        if(events&kDown) policy.disconnected(now);
        if(events&kUp) {
            esp_netif_ip_info_t ip{};wifi_ap_record_t record{};
            if(esp_netif_get_ip_info(sta_netif,&ip)==ESP_OK && ip.ip.addr &&
               esp_wifi_sta_get_ap_info(&record)==ESP_OK &&
               std::strncmp(reinterpret_cast<const char*>(record.ssid),current.ssid,32)==0) {
                policy.got_ip();ESP_LOGI(tag,"STA IP " IPSTR,IP2STR(&ip.ip));
                const auto rc=management::start("motion",SIMPLE_BUILD_ID,describe_motion);
                if(rc!=ESP_OK) ESP_LOGE(tag,"management start err=%s",esp_err_to_name(rc));
            }
        }
        Credentials incoming{};
        if(xQueueReceive(changes,&incoming,0)==pdTRUE) {
            if(save(incoming)) {
                current=incoming;disconnect();policy.configure(now);apply=true;state.configured=true;
            } else ESP_LOGE(tag,"save configuration failed");
            explicit_bzero(&incoming,sizeof(incoming));
        }
        // At most one attempt in flight, no periodic reconfiguration during DHCP.
        if(apply) {
            wifi_config_t config{};
            std::memcpy(config.sta.ssid,current.ssid,std::strlen(current.ssid));
            std::memcpy(config.sta.password,current.password,std::strlen(current.password));
            const auto rc=esp_wifi_set_config(WIFI_IF_STA,&config);
            explicit_bzero(&config,sizeof(config));
            if(rc!=ESP_OK) ESP_LOGE(tag,"STA config err=%s",esp_err_to_name(rc));
            else apply=false;
        }
        const auto action=apply?simple::NetworkPolicy::Action::None:policy.step(now,Runtime::get().network_busy());
        if(action==simple::NetworkPolicy::Action::Connect) {
            ++state.attempts;const auto rc=esp_wifi_connect();
            if(rc!=ESP_OK) { ESP_LOGW(tag,"connect err=%s",esp_err_to_name(rc));policy.disconnected(now); }
        } else if(action==simple::NetworkPolicy::Action::Cancel) disconnect();
        state.online=policy.online();state.connecting=policy.connecting();state.failures=policy.failures();
        state.retry_ms=policy.retry_ms(now);state.disconnect_reason=last_reason.load();
        std::memcpy(state.ssid,current.ssid,sizeof(state.ssid));
        esp_netif_ip_info_t ip{};state.ip[0]=0;
        if(state.online && esp_netif_get_ip_info(sta_netif,&ip)==ESP_OK) esp_ip4addr_ntoa(&ip.ip,state.ip,sizeof(state.ip));
        wifi_ap_record_t record{};state.rssi=0;
        if(state.online && esp_wifi_sta_get_ap_info(&record)==ESP_OK) state.rssi=record.rssi;
        uint8_t channel{};wifi_second_chan_t second{};
        if(esp_wifi_get_channel(&channel,&second)==ESP_OK) state.ap_channel=channel;
        wifi_sta_list_t clients{};
        if(esp_wifi_ap_get_sta_list(&clients)==ESP_OK) state.clients=uint8_t(clients.num);
        portENTER_CRITICAL(&state_mux);published=state;portEXIT_CRITICAL(&state_mux);
    }
}
}
void start_network() {
    ESP_ERROR_CHECK(esp_netif_init());ESP_ERROR_CHECK(esp_event_loop_create_default());
    ap_netif=esp_netif_create_default_wifi_ap();sta_netif=esp_netif_create_default_wifi_sta();configASSERT(ap_netif && sta_netif);
    ESP_ERROR_CHECK(esp_netif_set_hostname(sta_netif,"awcar-motion"));
    wifi_init_config_t init=WIFI_INIT_CONFIG_DEFAULT();ESP_ERROR_CHECK(esp_wifi_init(&init));
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT,WIFI_EVENT_STA_DISCONNECTED,event,nullptr));
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT,ESP_EVENT_ANY_ID,event,nullptr));
    wifi_config_t ap{};std::memcpy(ap.ap.ssid,"AW-CAR",6);ap.ap.ssid_len=6;
    std::memcpy(ap.ap.password,"123456789",9);ap.ap.channel=1;ap.ap.max_connection=4;
    ap.ap.authmode=WIFI_AUTH_WPA2_PSK;ap.ap.pmf_cfg.required=false;
    changes=xQueueCreate(1,sizeof(Credentials));configASSERT(changes);
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_APSTA));ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP,&ap));
    ESP_ERROR_CHECK(esp_wifi_start());
    configASSERT(xTaskCreate(run,"motion_sta",6144,nullptr,3,&worker)==pdPASS);
}
bool configure_network(const char* ssid,size_t n,const char* password,size_t p) {
    if(!changes || !n || n>32 || p>64 || (p && p<8)) return false;
    Credentials c{};std::memcpy(c.ssid,ssid,n);std::memcpy(c.password,password,p);
    Runtime::get().stop();const bool result=xQueueOverwrite(changes,&c)==pdTRUE;
    explicit_bzero(&c,sizeof(c));return result;
}
NetworkState network_state() {
    portENTER_CRITICAL(&state_mux);const auto s=published;portEXIT_CRITICAL(&state_mux);return s;
}
bool request_on_ap(httpd_req_t* request) {
    sockaddr_storage local{};socklen_t size=sizeof(local);esp_netif_ip_info_t ap{};
    if(!ap_netif || getsockname(httpd_req_to_sockfd(request),reinterpret_cast<sockaddr*>(&local),&size)!=0 ||
       esp_netif_get_ip_info(ap_netif,&ap)!=ESP_OK) return false;
    uint32_t destination=0;bool recognized=false;
    if(local.ss_family==AF_INET && size>=sizeof(sockaddr_in)) {
        const auto* v4=reinterpret_cast<const sockaddr_in*>(&local);
        recognized=simple::ipv4_destination(reinterpret_cast<const uint8_t*>(&v4->sin_addr.s_addr),4,destination);
    }
#if CONFIG_LWIP_IPV6
    else if(local.ss_family==AF_INET6 && size>=sizeof(sockaddr_in6)) {
        const auto* v6=reinterpret_cast<const sockaddr_in6*>(&local);
        recognized=simple::ipv4_destination(v6->sin6_addr.s6_addr,16,destination);
    }
#endif
    return recognized && simple::on_interface(destination,ap.ip.addr);
}
}
