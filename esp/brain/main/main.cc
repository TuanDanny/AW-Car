#include <esp_log.h>
#include <esp_err.h>
#include <nvs.h>
#include <nvs_flash.h>
#include <driver/gpio.h>
#include <esp_event.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#include "application.h"
#include "car/runtime.h"
#include "management.hpp"

#define TAG "main"
#ifndef SIMPLE_BUILD_ID
#define SIMPLE_BUILD_ID "simplev1-dev"
#endif

extern "C" void app_main(void)
{
    ESP_LOGI(TAG,"build=%s Brain STA-only / UART17-18 / no dashboard",SIMPLE_BUILD_ID);
    // Initialize NVS flash for WiFi configuration
    esp_err_t ret = nvs_flash_init();
    ESP_ERROR_CHECK(ret);

    // Initialize and run the application
    auto& app = Application::GetInstance();
    app.Initialize();
    management::start_boot_guard([] {
        Application::GetInstance().Schedule([] {
            if(brain::Runtime::Get().WorkerHealthy()) management::confirm_local_boot();
        });
    });
    app.Run();  // This function runs the main event loop and never returns
}
