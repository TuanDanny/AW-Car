#include "runtime.hpp"
#include "network_manager.hpp"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cerrno>
#include <cstring>
#include <memory>
#include "cJSON.h"
#include "esp_http_server.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "lwip/sockets.h"

#ifndef SIMPLE_BUILD_ID
#define SIMPLE_BUILD_ID "simplev1-dev"
#endif
extern const char page_start[] asm("_binary_index_html_start");
namespace motion {
namespace {
httpd_handle_t server{};
int owner=-1; // Only the HTTP server task reads/writes this descriptor.
uint32_t opened{},closed{},send_errors{},recv_errors{};
using Json=std::unique_ptr<cJSON,decltype(&cJSON_Delete)>;
esp_err_t send_text(httpd_req_t* request,const char* text) {
    httpd_ws_frame_t frame{};frame.type=HTTPD_WS_TYPE_TEXT;
    frame.payload=reinterpret_cast<uint8_t*>(const_cast<char*>(text));frame.len=std::strlen(text);
    const auto result=httpd_ws_send_frame(request,&frame);
    if(result!=ESP_OK) { ++send_errors;ESP_LOGW("simple_web","send_failed fd=%d err=%s",httpd_req_to_sockfd(request),esp_err_to_name(result)); }
    return result;
}
esp_err_t send_json(httpd_req_t* request,cJSON* json) {
    char* text=cJSON_PrintUnformatted(json);if(!text) return ESP_ERR_NO_MEM;
    const auto result=send_text(request,text);cJSON_free(text);return result;
}
esp_err_t result(httpd_req_t* request,bool ok,const char* why) {
    Json root(cJSON_CreateObject(),cJSON_Delete);if(!root) return ESP_ERR_NO_MEM;
    cJSON_AddStringToObject(root.get(),"t","result");cJSON_AddBoolToObject(root.get(),"ok",ok);cJSON_AddStringToObject(root.get(),"reason",why);
    return send_json(request,root.get());
}
esp_err_t status(httpd_req_t* request) {
    const auto s=Runtime::get().snapshot();
    Json root(cJSON_CreateObject(),cJSON_Delete);if(!root) return ESP_ERR_NO_MEM;
    auto* r=root.get();cJSON_AddStringToObject(r,"t","status");cJSON_AddStringToObject(r,"build",SIMPLE_BUILD_ID);
    cJSON_AddStringToObject(r,"mode",s.car.mode==simple::Mode::Manual?"manual":"ai");
    cJSON_AddStringToObject(r,"action",simple::action_name(s.car.action));cJSON_AddNumberToObject(r,"speed",s.car.speed);
    cJSON_AddNumberToObject(r,"left",s.car.left);cJSON_AddNumberToObject(r,"right",s.car.right);
    cJSON_AddNumberToObject(r,"generation",s.car.generation);cJSON_AddStringToObject(r,"reason",simple::reason_name(s.car.reason));
    cJSON_AddBoolToObject(r,"simulator",false);
    cJSON_AddBoolToObject(r,"maintenance",s.maintenance);
    const auto net=network_state();auto* network=cJSON_AddObjectToObject(r,"motion_network");
    cJSON_AddBoolToObject(network,"configured",net.configured);cJSON_AddBoolToObject(network,"online",net.online);
    cJSON_AddBoolToObject(network,"connecting",net.connecting);cJSON_AddStringToObject(network,"ip",net.ip);
    cJSON_AddStringToObject(network,"ssid",net.ssid);cJSON_AddNumberToObject(network,"attempts",net.attempts);
    cJSON_AddNumberToObject(network,"retry_ms",net.retry_ms);cJSON_AddNumberToObject(network,"failures",net.failures);
    cJSON_AddNumberToObject(network,"disconnect_reason",net.disconnect_reason);cJSON_AddNumberToObject(network,"ap_channel",net.ap_channel);
    auto* f=cJSON_AddObjectToObject(r,"fpga");cJSON_AddBoolToObject(f,"connected",s.car.fpga_link);
    cJSON_AddNumberToObject(f,"applied_seq",s.car.applied_seq);cJSON_AddNumberToObject(f,"left_count",s.fpga.left_count);
    cJSON_AddNumberToObject(f,"right_count",s.fpga.right_count);cJSON_AddBoolToObject(f,"left_seen",(s.fpga.flags&2)!=0);
    cJSON_AddBoolToObject(f,"right_seen",(s.fpga.flags&4)!=0);
    auto* b=cJSON_AddObjectToObject(r,"brain");cJSON_AddBoolToObject(b,"connected",s.brain_connected);
    cJSON_AddBoolToObject(b,"wifi",s.brain_connected&&(s.brain.flags&simple::kWifiReady));
    cJSON_AddBoolToObject(b,"cloud",s.brain_connected&&(s.brain.flags&simple::kCloudReady));
    cJSON_AddBoolToObject(b,"listening",s.brain_connected&&(s.brain.flags&simple::kListening));
    cJSON_AddBoolToObject(b,"speaking",s.brain_connected&&(s.brain.flags&simple::kSpeaking));
    char ssid[33]{};std::memcpy(ssid,s.brain.ssid.data(),32);cJSON_AddStringToObject(b,"ssid",ssid);
    char ip[16]{};std::snprintf(ip,sizeof(ip),"%u.%u.%u.%u",s.brain.ipv4[0],s.brain.ipv4[1],s.brain.ipv4[2],s.brain.ipv4[3]);
    cJSON_AddStringToObject(b,"ip",ip);cJSON_AddNumberToObject(b,"wifi_result",s.brain.wifi_result);
    auto* d=cJSON_AddObjectToObject(r,"diag");cJSON_AddNumberToObject(d,"uart_rx",s.uart_rx);
    cJSON_AddNumberToObject(d,"uart_errors",s.uart_errors);cJSON_AddNumberToObject(d,"uart_tx_errors",s.uart_tx_errors);
    cJSON_AddNumberToObject(d,"spi_ok",s.spi_ok);cJSON_AddNumberToObject(d,"spi_errors",s.spi_errors);
    cJSON_AddNumberToObject(d,"spi_io_errors",s.spi_io_errors);cJSON_AddNumberToObject(d,"spi_frame_errors",s.spi_frame_errors);
    cJSON_AddNumberToObject(d,"spi_ack_errors",s.spi_ack_errors);cJSON_AddNumberToObject(d,"spi_startup",s.spi_startup);
    cJSON_AddNumberToObject(d,"rejected",s.rejected);cJSON_AddNumberToObject(d,"latency_count",s.latency_count);
    auto samples=s.latency_us;const size_t count=std::min<size_t>(s.latency_count,samples.size());
    std::sort(samples.begin(),samples.begin()+count);
    const auto percentile=[&](unsigned p){return count?samples[(count*p+99)/100-1]:0;};
    cJSON_AddNumberToObject(d,"latency_p50_us",percentile(50));cJSON_AddNumberToObject(d,"latency_p95_us",percentile(95));
    cJSON_AddNumberToObject(d,"latency_p99_us",percentile(99));cJSON_AddNumberToObject(d,"latency_max_us",s.latency_max_us);
    cJSON_AddNumberToObject(d,"latency_window",count);cJSON_AddNumberToObject(d,"heap",esp_get_free_heap_size());
    cJSON_AddNumberToObject(d,"uptime_ms",double(esp_timer_get_time()/1000));
    cJSON_AddNumberToObject(d,"ws_opened",opened);cJSON_AddNumberToObject(d,"ws_closed",closed);
    cJSON_AddNumberToObject(d,"ws_send_errors",send_errors);cJSON_AddNumberToObject(d,"ws_receive_errors",recv_errors);
    return send_json(request,r);
}
const char* string(cJSON* object,const char* key) {
    const auto* p=cJSON_GetObjectItemCaseSensitive(object,key);return cJSON_IsString(p)?p->valuestring:nullptr;
}
bool integer(cJSON* object,const char* key,int min,int max,int& value) {
    const auto* p=cJSON_GetObjectItemCaseSensitive(object,key);
    if(!cJSON_IsNumber(p) || !std::isfinite(p->valuedouble) || std::floor(p->valuedouble)!=p->valuedouble || p->valuedouble<min || p->valuedouble>max) return false;
    value=int(p->valuedouble);return true;
}
esp_err_t message(httpd_req_t* request,cJSON* json) {
    const char* type=string(json,"t");if(!type) return result(request,false,"invalid_type");
    auto& runtime=Runtime::get();
    if(std::strcmp(type,"status")==0) return status(request);
    if(std::strcmp(type,"stop")==0) { runtime.stop();return result(request,true,"received"); }
    if(runtime.snapshot().maintenance) return result(request,false,"maintenance");
    if(std::strcmp(type,"neutral")==0) { runtime.drive(simple::Action::Neutral,0);return result(request,true,"received"); }
    if(std::strcmp(type,"mode")==0) {
        const auto* mode=string(json,"mode");if(!mode || (std::strcmp(mode,"manual") && std::strcmp(mode,"ai"))) return result(request,false,"invalid_mode");
        runtime.mode(std::strcmp(mode,"ai")==0?simple::Mode::Ai:simple::Mode::Manual);return result(request,true,"received");
    }
    if(std::strcmp(type,"drive")==0) {
        const auto* name=string(json,"action");int speed=0;simple::Action action=simple::Action::Neutral;
        if(!name || !integer(json,"speed",0,100,speed)) return result(request,false,"invalid_drive");
        if(!std::strcmp(name,"forward")) action=simple::Action::Forward;
        else if(!std::strcmp(name,"backward")) action=simple::Action::Backward;
        else if(!std::strcmp(name,"left")) action=simple::Action::Left;
        else if(!std::strcmp(name,"right")) action=simple::Action::Right;
        else return result(request,false,"invalid_action");
        const auto s=runtime.snapshot();
        if(s.car.mode!=simple::Mode::Manual) return result(request,false,"manual_only");
        if(!s.car.fpga_link) return result(request,false,"fpga_unavailable");
        runtime.drive(action,uint8_t(speed));return result(request,true,"received");
    }
    if(std::strcmp(type,"listen")==0) {
        const auto* enabled=cJSON_GetObjectItemCaseSensitive(json,"enabled");
        if(!cJSON_IsBool(enabled)) return result(request,false,"invalid_listen");
        if(!runtime.snapshot().brain_connected) return result(request,false,"brain_unavailable");
        return result(request,runtime.listen(cJSON_IsTrue(enabled)),"received");
    }
    if(std::strcmp(type,"wifi")==0) {
        const auto* ssid=string(json,"ssid");const auto* password=string(json,"password");
        if(!ssid || !password) return result(request,false,"invalid_wifi");
        const size_t n=std::strlen(ssid),p=std::strlen(password);
        if(!n || n>32 || p>64 || (p>0 && p<8)) return result(request,false,"invalid_wifi");
        runtime.stop();
        const bool motion_ok=configure_network(ssid,n,password,p);
        const bool brain_ok=runtime.snapshot().brain_connected && runtime.wifi(ssid,n,password,p);
        return result(request,motion_ok && brain_ok,motion_ok?(brain_ok?"wifi_both_queued":"motion_queued_brain_unavailable"):"motion_network_queue_failed");
    }
    return result(request,false,"unknown_command");
}
void close_socket(httpd_handle_t,int fd) {
    if(fd==owner) { owner=-1;Runtime::get().disconnect();++closed;ESP_LOGI("simple_web","peer_closed fd=%d",fd); }
    close(fd);
}
esp_err_t pre_handshake(httpd_req_t* request) {
    if(!request_on_ap(request)) {
        ESP_LOGW("simple_web","STA control denied");return ESP_FAIL;
    }
    // URI/header access happens exactly here, never after WS upgrade.
    char origin[80]{},host[48]{};
    if(httpd_req_get_hdr_value_str(request,"Origin",origin,sizeof(origin))!=ESP_OK ||
       httpd_req_get_hdr_value_str(request,"Host",host,sizeof(host))!=ESP_OK) return ESP_FAIL;
    const bool host_ok=std::strcmp(host,"192.168.4.1")==0 || std::strcmp(host,"192.168.4.1:80")==0;
    const bool origin_ok=std::strcmp(origin,"http://192.168.4.1")==0 || std::strcmp(origin,"http://192.168.4.1:80")==0;
    if(!host_ok || !origin_ok) { ESP_LOGW("simple_web","origin_rejected");return ESP_FAIL; }
    return ESP_OK;
}
esp_err_t post_handshake(httpd_req_t* request) {
    const int fd=httpd_req_to_sockfd(request),previous=owner;owner=fd;
    Runtime::get().stop(simple::Reason::Takeover);++opened;
    const int one=1;const auto rc=setsockopt(fd,IPPROTO_TCP,TCP_NODELAY,&one,sizeof(one));
    if(rc!=0) ESP_LOGW("simple_web","TCP_NODELAY failed fd=%d errno=%d",fd,errno);
    if(previous>=0 && previous!=fd) {
        static uint8_t payload[]={0x03,0xe9,'c','o','n','t','r','o','l','l','e','r','_','r','e','p','l','a','c','e','d'};
        httpd_ws_frame_t frame{};frame.type=HTTPD_WS_TYPE_CLOSE;frame.payload=payload;frame.len=sizeof(payload);
        // This call is within the server task, not queued from another task.
        const auto sent=httpd_ws_send_frame_async(server,previous,&frame);
        if(sent!=ESP_OK) ++send_errors;
        const auto closing=httpd_sess_trigger_close(server,previous);
        if(closing!=ESP_OK) ESP_LOGW("simple_web","takeover_close err=%s",esp_err_to_name(closing));
    }
    ESP_LOGI("simple_web","handshake fd=%d takeover=%d",fd,previous);
    return status(request);
}
esp_err_t ws_handler(httpd_req_t* request) {
    if(!request_on_ap(request)) return ESP_FAIL;
    if(httpd_req_to_sockfd(request)!=owner) return ESP_FAIL;
    httpd_ws_frame_t frame{};auto rc=httpd_ws_recv_frame(request,&frame,0);
    if(rc!=ESP_OK) { ++recv_errors;return rc; }
    if(frame.len>512) return ESP_FAIL;
    char bytes[513]{};frame.payload=reinterpret_cast<uint8_t*>(bytes);
    if(frame.len) {
        rc=httpd_ws_recv_frame(request,&frame,frame.len);
        if(rc!=ESP_OK) { ++recv_errors;return rc; }
    }
    if(frame.type==HTTPD_WS_TYPE_CLOSE) { Runtime::get().disconnect();return ESP_FAIL; }
    if(frame.type==HTTPD_WS_TYPE_PING) { frame.type=HTTPD_WS_TYPE_PONG;return httpd_ws_send_frame(request,&frame); }
    if(frame.type==HTTPD_WS_TYPE_PONG) return ESP_OK;
    if(frame.type!=HTTPD_WS_TYPE_TEXT || frame.fragmented || !frame.final) return result(request,false,"invalid_frame");
    Json json(cJSON_ParseWithLength(bytes,frame.len),cJSON_Delete);
    if(!json || !cJSON_IsObject(json.get())) return result(request,false,"invalid_json");
    return message(request,json.get());
}
esp_err_t index(httpd_req_t* request) {
    if(!request_on_ap(request)) return httpd_resp_send_err(request,HTTPD_403_FORBIDDEN,"Dashboard is available on AW-CAR / 192.168.4.1 only");
    httpd_resp_set_type(request,"text/html; charset=utf-8");httpd_resp_set_hdr(request,"Cache-Control","no-store");
    httpd_resp_set_hdr(request,"X-Content-Type-Options","nosniff");httpd_resp_set_hdr(request,"X-Frame-Options","DENY");
    return httpd_resp_send(request,page_start,HTTPD_RESP_USE_STRLEN);
}
}
void start_web() {
    httpd_config_t config=HTTPD_DEFAULT_CONFIG();config.task_priority=4;config.core_id=0;config.stack_size=12288;
    config.max_open_sockets=4;config.lru_purge_enable=false;config.recv_wait_timeout=2;config.send_wait_timeout=1;
    config.keep_alive_enable=true;config.keep_alive_idle=10;config.keep_alive_interval=3;config.keep_alive_count=3;
    config.close_fn=close_socket;ESP_ERROR_CHECK(httpd_start(&server,&config));
    httpd_uri_t root{};root.uri="/";root.method=HTTP_GET;root.handler=index;
    ESP_ERROR_CHECK(httpd_register_uri_handler(server,&root));
    httpd_uri_t ws{};ws.uri="/ws";ws.method=HTTP_GET;ws.handler=ws_handler;ws.is_websocket=true;
    ws.handle_ws_control_frames=true;ws.ws_pre_handshake_cb=pre_handshake;ws.ws_post_handshake_cb=post_handshake;
    ESP_ERROR_CHECK(httpd_register_uri_handler(server,&ws));
}
} // namespace motion
