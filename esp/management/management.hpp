#pragma once
#include <cstddef>
#include "esp_err.h"
namespace management {
using Describe=void(*)(char*,size_t);
struct UpdateHooks { bool (*enter)(){};void (*leave)(){}; };
// Initialize once from a network/background task after Wi-Fi is initialized.
esp_err_t start(const char* role,const char* build,Describe describe,UpdateHooks hooks={});
bool update_busy();
class UpdateLease {
public:
    UpdateLease();~UpdateLease();
    explicit operator bool() const { return held_; }
    UpdateLease(const UpdateLease&)=delete;
private: bool held_{};
};
// request_check must schedule a check in the application's own event loop.
void start_boot_guard(void(*request_check)());
esp_err_t confirm_local_boot();
bool boot_pending();
}
