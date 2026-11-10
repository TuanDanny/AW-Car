#pragma once
#include "management.hpp"
#include "esp_http_server.h"
namespace management {
bool ota_available(UpdateHooks hooks);
const char* ota_state();
esp_err_t receive_update(httpd_req_t* request,UpdateHooks hooks);
}
