#include "management.hpp"
#include "management_key.hpp"
#include "simple/log_ring.hpp"
#include "simple/network_policy.hpp"
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <cerrno>
#include "cJSON.h"
#include "esp_app_desc.h"
#include "esp_http_server.h"
#include "esp_https_server.h"
#include "esp_netif.h"
#include "esp_random.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "lwip/sockets.h"
#include "mdns.h"

namespace management {
namespace {
httpd_handle_t server{};
const char *role_name{},*build_name{};
Describe describe_state{};
char boot_id[33]{};
simple::LogRing<> ring;
portMUX_TYPE ring_mux=portMUX_INITIALIZER_UNLOCKED;
bool initialized{};
uint64_t now_ms() { return esp_timer_get_time()/1000; }
void hex(const uint8_t* data,size_t n,char* output) {
    constexpr char digits[]="0123456789abcdef";
    for(size_t i=0;i<n;++i) { output[2*i]=digits[data[i]>>4];output[2*i+1]=digits[data[i]&15]; }
    output[2*n]=0;
}
void random_nonce(char* output) { uint8_t bytes[16];esp_fill_random(bytes,sizeof(bytes));hex(bytes,sizeof(bytes),output); }
bool on_sta(httpd_req_t* r) {
    auto* sta=esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
    esp_netif_ip_info_t ip{};sockaddr_storage local{};socklen_t size=sizeof(local);
    if(!sta || esp_netif_get_ip_info(sta,&ip)!=ESP_OK || !ip.ip.addr ||
       getsockname(httpd_req_to_sockfd(r),reinterpret_cast<sockaddr*>(&local),&size)!=0) return false;
    uint32_t destination{};bool valid=false;
    if(local.ss_family==AF_INET && size>=sizeof(sockaddr_in)) {
        const auto* a=reinterpret_cast<const sockaddr_in*>(&local);
        valid=simple::ipv4_destination(reinterpret_cast<const uint8_t*>(&a->sin_addr.s_addr),4,destination);
    }
#if CONFIG_LWIP_IPV6
    else if(local.ss_family==AF_INET6 && size>=sizeof(sockaddr_in6)) {
        const auto* a=reinterpret_cast<const sockaddr_in6*>(&local);
        valid=simple::ipv4_destination(a->sin6_addr.s6_addr,16,destination);
    }
#endif
    return valid && simple::on_interface(destination,ip.ip.addr);
}
esp_err_t deny(httpd_req_t* r,const char* status,const char* why) {
    httpd_resp_set_status(r,status);return httpd_resp_sendstr(r,why);
}
esp_err_t json(httpd_req_t* r,cJSON* value) {
    if(!value) return ESP_ERR_NO_MEM;
    cJSON_AddStringToObject(value,"role",role_name);cJSON_AddStringToObject(value,"key_id",awcar_private::key_id);
    char* text=cJSON_PrintUnformatted(value);cJSON_Delete(value);
    if(!text) return ESP_ERR_NO_MEM;
    httpd_resp_set_type(r,"application/json");httpd_resp_set_hdr(r,"Cache-Control","no-store");
    const auto rc=httpd_resp_sendstr(r,text);cJSON_free(text);return rc;
}
bool authenticate(httpd_req_t* r) {
    char auth[72]{};
    if(httpd_req_get_hdr_value_str(r,"Authorization",auth,sizeof(auth))!=ESP_OK ||
       std::strlen(auth)!=71 || std::strncmp(auth,"Bearer ",7)!=0) return false;
    uint8_t diff=0;
    for(size_t i=0;i<64;++i) diff|=uint8_t(awcar_private::key[i]^auth[7+i]);
    return diff==0;
}
esp_err_t info(httpd_req_t* r) {
    if(!on_sta(r)) return deny(r,"403 Forbidden","STA only");
    if(!authenticate(r)) return deny(r,"401 Unauthorized","authentication required");
    char status[256]{};describe_state(status,sizeof(status));const auto* app=esp_app_get_description();
    auto* root=cJSON_CreateObject();if(!root) return ESP_ERR_NO_MEM;
    cJSON_AddStringToObject(root,"build",build_name);
    cJSON_AddStringToObject(root,"project",app->project_name);cJSON_AddStringToObject(root,"version",app->version);
    cJSON_AddStringToObject(root,"boot",boot_id);cJSON_AddNumberToObject(root,"heap",esp_get_free_heap_size());
    cJSON_AddNumberToObject(root,"uptime_ms",double(now_ms()));cJSON_AddBoolToObject(root,"ota_enabled",false);
    if(auto* s=cJSON_Parse(status)) cJSON_AddItemToObject(root,"status",s);
    return json(r,root);
}
esp_err_t logs(httpd_req_t* r) {
    if(!on_sta(r)) return deny(r,"403 Forbidden","STA only");
    if(!authenticate(r)) return deny(r,"401 Unauthorized","authentication required");
    char query[64]{},value[24]{};uint64_t after=0;
    if(httpd_req_get_url_query_len(r)) {
        if(httpd_req_get_url_query_str(r,query,sizeof(query))!=ESP_OK ||
           httpd_query_key_value(query,"after",value,sizeof(value))!=ESP_OK) return deny(r,"400 Bad Request","after required");
        if(!value[0]) return deny(r,"400 Bad Request","invalid cursor");
        for(const char* p=value;*p;++p) if(*p<'0' || *p>'9') return deny(r,"400 Bad Request","invalid cursor");
        errno=0;after=std::strtoull(value,nullptr,10);if(errno) return deny(r,"400 Bad Request","invalid cursor");
    }
    simple::LogRing<>::Record records[8];
    portENTER_CRITICAL(&ring_mux);const auto batch=ring.read(after,records,8);portEXIT_CRITICAL(&ring_mux);
    auto* root=cJSON_CreateObject();if(!root) return ESP_ERR_NO_MEM;
    cJSON_AddStringToObject(root,"boot",boot_id);cJSON_AddNumberToObject(root,"next",double(batch.next));
    cJSON_AddNumberToObject(root,"dropped",double(batch.dropped));auto* list=cJSON_AddArrayToObject(root,"samples");
    for(size_t i=0;i<batch.count;++i) {
        auto* item=cJSON_CreateObject();cJSON_AddNumberToObject(item,"seq",double(records[i].seq));
        cJSON_AddNumberToObject(item,"ms",double(records[i].ms));cJSON_AddStringToObject(item,"text",records[i].text);
        cJSON_AddItemToArray(list,item);
    }
    return json(r,root);
}
void sample(void*) {
    for(;;) {
        char text[256]{};describe_state(text,sizeof(text));
        portENTER_CRITICAL(&ring_mux);ring.append(now_ms(),text);portEXIT_CRITICAL(&ring_mux);
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}
}
esp_err_t start(const char* role,const char* build,Describe describe) {
    if(initialized) return ESP_OK;
    role_name=role;build_name=build;describe_state=describe;random_nonce(boot_id);
    // IDF6.1's SSL default macro omits a deprecated field and triggers C++ -Werror.
    // Initialize all fields to zero, then set the documented defaults we use.
    httpd_ssl_config_t config{};config.httpd=HTTPD_DEFAULT_CONFIG();config.port_secure=3232;
    config.port_insecure=80;config.transport_mode=HTTPD_SSL_TRANSPORT_SECURE;
    config.ecdsa_curve=ESP_TLS_ECDSA_CURVE_SECP256R1;config.tls_version=ESP_TLS_VER_ANY;
    config.httpd.ctrl_port=32769;config.httpd.task_priority=2;config.httpd.core_id=0;
    config.httpd.stack_size=10240;config.httpd.max_open_sockets=2;
    config.httpd.recv_wait_timeout=2;config.httpd.send_wait_timeout=1;config.httpd.lru_purge_enable=false;
    config.servercert=reinterpret_cast<const uint8_t*>(awcar_private::certificate);
    config.servercert_len=sizeof(awcar_private::certificate);
    config.prvtkey_pem=reinterpret_cast<const uint8_t*>(awcar_private::tls_key);
    config.prvtkey_len=sizeof(awcar_private::tls_key);
    config.tls_handshake_timeout_ms=3000;
    auto rc=httpd_ssl_start(&server,&config);if(rc!=ESP_OK) return rc;
    httpd_uri_t handlers[2]{};
    const char* paths[]={"/info","/logs"};
    esp_err_t (*functions[])(httpd_req_t*)={info,logs};
    for(size_t i=0;i<2;++i) {
        handlers[i].uri=paths[i];handlers[i].method=HTTP_GET;handlers[i].handler=functions[i];
        rc=httpd_register_uri_handler(server,&handlers[i]);
        if(rc!=ESP_OK) { httpd_ssl_stop(server);server=nullptr;return rc; }
    }
    rc=mdns_init();
    if(rc==ESP_OK) {
        char hostname[32]{};std::snprintf(hostname,sizeof(hostname),"awcar-%s",role);
        rc=mdns_hostname_set(hostname);
        mdns_txt_item_t txt[]={{"role",role},{"ota","0"}};
        if(rc==ESP_OK) rc=mdns_service_add(hostname,"_awcar","_tcp",3232,txt,2);
    }
    if(rc!=ESP_OK) { mdns_free();httpd_ssl_stop(server);server=nullptr;return rc; }
    if(xTaskCreatePinnedToCore(sample,"mgmt_samples",4096,nullptr,1,nullptr,0)!=pdPASS) {
        mdns_free();httpd_ssl_stop(server);server=nullptr;return ESP_ERR_NO_MEM;
    }
    initialized=true;return ESP_OK;
}
}
