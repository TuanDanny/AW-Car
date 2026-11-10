#pragma once
#include <cstddef>
#include "esp_err.h"
namespace management {
using Describe=void(*)(char*,size_t);
// Initialize once from a network/background task after Wi-Fi is initialized.
esp_err_t start(const char* role,const char* build,Describe describe);
}
