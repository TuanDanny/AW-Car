#include "update.hpp"
#include <atomic>
#include <cstdio>
#include <cstring>
#include "esp_app_format.h"
#include "esp_app_desc.h"
#include "esp_ota_ops.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "psa/crypto.h"

namespace management {
namespace {
std::atomic<bool> writing{false};
void(*check_boot)(){};
uint64_t now_ms() { return esp_timer_get_time()/1000; }
bool pending() {
    esp_ota_img_states_t state{};
    return esp_ota_get_state_partition(esp_ota_get_running_partition(),&state)==ESP_OK && state==ESP_OTA_IMG_PENDING_VERIFY;
}
esp_err_t error(httpd_req_t* r,const char* status,const char* reason) {
    httpd_resp_set_status(r,status);httpd_resp_set_hdr(r,"Connection","close");httpd_resp_sendstr(r,reason);
    // ESP_FAIL skips httpd_req_delete's remaining-body purge and closes this session.
    return ESP_FAIL;
}
void boot_guard(void*) {
    vTaskDelay(pdMS_TO_TICKS(3000));check_boot();
    const auto deadline=now_ms()+12000;
    while(pending() && now_ms()<deadline) vTaskDelay(pdMS_TO_TICKS(200));
    if(pending()) esp_restart(); // Bootloader rolls an unconfirmed trial back.
    vTaskDelete(nullptr);
}
struct Transfer {
    esp_ota_handle_t handle{};bool active{},entered{};
    psa_hash_operation_t hash=PSA_HASH_OPERATION_INIT;
    UpdateHooks hooks{};
    ~Transfer() {
        psa_hash_abort(&hash);
        if(active) esp_ota_abort(handle);
        if(entered) hooks.leave();
    }
};
}
UpdateLease::UpdateLease() { bool expected=false;held_=writing.compare_exchange_strong(expected,true); }
UpdateLease::~UpdateLease() { if(held_) writing=false; }
bool update_busy() { return writing.load(); }
bool ota_available(UpdateHooks hooks) {
#ifdef CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE
    return hooks.enter && hooks.leave && esp_ota_get_next_update_partition(nullptr)!=nullptr;
#else
    (void)hooks;return false;
#endif
}
const char* ota_state() {
    esp_ota_img_states_t state{};
    if(esp_ota_get_state_partition(esp_ota_get_running_partition(),&state)!=ESP_OK) return "not_ota";
    switch(state) {
    case ESP_OTA_IMG_PENDING_VERIFY:return "pending";
    case ESP_OTA_IMG_VALID:return "valid";
    case ESP_OTA_IMG_NEW:return "new";
    default:return "other";
    }
}
esp_err_t receive_update(httpd_req_t* r,UpdateHooks hooks) {
    if(!ota_available(hooks) || pending()) return error(r,"409 Conflict","OTA bootstrap/health check required");
    UpdateLease lease;if(!lease) return error(r,"409 Conflict","update already active");
    const auto* target=esp_ota_get_next_update_partition(nullptr);
    constexpr size_t prefix=sizeof(esp_image_header_t)+sizeof(esp_image_segment_header_t)+sizeof(esp_app_desc_t);
    static_assert(prefix<=1024);
    if(r->content_len<prefix || r->content_len>target->size) return error(r,"400 Bad Request","image size invalid");
    char expected[65]{};
    if(httpd_req_get_hdr_value_str(r,"X-AW-SHA256",expected,sizeof(expected))!=ESP_OK || std::strlen(expected)!=64)
        return error(r,"400 Bad Request","SHA256 required");
    for(auto c:expected) if(c && !((c>='0'&&c<='9') || (c>='a'&&c<='f'))) return error(r,"400 Bad Request","invalid SHA256");
    uint8_t buffer[1024];size_t filled=0;
    while(filled<prefix) {
        const int count=httpd_req_recv(r,reinterpret_cast<char*>(buffer+filled),prefix-filled);
        if(count<=0) return error(r,"400 Bad Request","incomplete image header");
        filled+=size_t(count);
    }
    esp_image_header_t image{};esp_app_desc_t app{};
    std::memcpy(&image,buffer,sizeof(image));std::memcpy(&app,buffer+sizeof(image)+sizeof(esp_image_segment_header_t),sizeof(app));
    if(image.magic!=ESP_IMAGE_HEADER_MAGIC || image.chip_id!=ESP_CHIP_ID_ESP32S3 || image.hash_appended!=1 ||
       app.magic_word!=ESP_APP_DESC_MAGIC_WORD || std::memcmp(app.project_name,esp_app_get_description()->project_name,sizeof(app.project_name))!=0)
        return error(r,"400 Bad Request","wrong chip/project image");
    Transfer transfer;transfer.hooks=hooks;
    if(!hooks.enter()) { hooks.leave();return error(r,"409 Conflict","maintenance could not be established"); }
    transfer.entered=true;
    if(psa_crypto_init()!=PSA_SUCCESS || psa_hash_setup(&transfer.hash,PSA_ALG_SHA_256)!=PSA_SUCCESS)
        return error(r,"500 Internal Server Error","hash setup failed");
    if(esp_ota_begin(target,r->content_len,&transfer.handle)!=ESP_OK) return error(r,"500 Internal Server Error","OTA begin failed");
    transfer.active=true;size_t received=0;const auto deadline=now_ms()+120000;
    while(received<r->content_len && now_ms()<deadline) {
        if(psa_hash_update(&transfer.hash,buffer,filled)!=PSA_SUCCESS || esp_ota_write(transfer.handle,buffer,filled)!=ESP_OK)
            return error(r,"500 Internal Server Error","OTA write failed");
        received+=filled;if(received==r->content_len) break;
        const auto remaining=r->content_len-received;
        const int count=httpd_req_recv(r,reinterpret_cast<char*>(buffer),remaining<sizeof(buffer)?remaining:sizeof(buffer));
        if(count<=0) return error(r,"400 Bad Request","transfer interrupted");
        filled=size_t(count);
    }
    if(received!=r->content_len) return error(r,"408 Request Timeout","transfer expired");
    uint8_t digest[32]{};size_t digest_size=0;
    if(psa_hash_finish(&transfer.hash,digest,sizeof(digest),&digest_size)!=PSA_SUCCESS || digest_size!=32)
        return error(r,"500 Internal Server Error","hash finalization failed");
    constexpr char digits[]="0123456789abcdef";uint8_t diff=0;
    for(size_t i=0;i<32;++i) { diff|=uint8_t(expected[2*i]^digits[digest[i]>>4]);diff|=uint8_t(expected[2*i+1]^digits[digest[i]&15]); }
    if(diff) return error(r,"400 Bad Request","image SHA256 mismatch");
    transfer.active=false;
    if(esp_ota_end(transfer.handle)!=ESP_OK) return error(r,"400 Bad Request","image validation failed");
    if(esp_ota_set_boot_partition(target)!=ESP_OK) return error(r,"500 Internal Server Error","boot selection failed");
    // Remain in maintenance until reboot; never release a saved target.
    transfer.entered=false;
    httpd_resp_set_status(r,"202 Accepted");httpd_resp_set_type(r,"application/json");
    httpd_resp_sendstr(r,"{\"stored\":true,\"boot_pending\":true}");
    vTaskDelay(pdMS_TO_TICKS(500));esp_restart();return ESP_OK;
}
void start_boot_guard(void(*request_check)()) {
    if(!pending()) return;
    check_boot=request_check;
    if(xTaskCreatePinnedToCore(boot_guard,"ota_boot_guard",3072,nullptr,1,nullptr,0)!=pdPASS) esp_restart();
}
esp_err_t confirm_local_boot() {
#ifdef SIMPLE_OTA_TEST_FAIL_HEALTH
    return ESP_FAIL;
#else
    return pending()?esp_ota_mark_app_valid_cancel_rollback():ESP_OK;
#endif
}
}
