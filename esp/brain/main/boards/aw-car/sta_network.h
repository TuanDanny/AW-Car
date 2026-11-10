#pragma once
#include <atomic>
#include <mutex>
#include <esp_event.h>
#include <esp_netif.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>
#include "board.h"
#include "simple/protocol.hpp"

class StaNetwork {
public:
    void Start(NetworkEventCallback callback);
    bool Configure(const simple::Frame& frame);
    void FillState(simple::BrainState& state);
    std::string Json();
    bool Connected() const { return connected_.load(); }
private:
    struct Credentials { uint8_t ssid_len{}, pass_len{}; char ssid[33]{}, password[65]{}; };
    static void OnEvent(void* arg, esp_event_base_t base, int32_t id, void* data);
    void Run();
    void Notify(NetworkEvent event, const std::string& data = "");
    NetworkEventCallback callback_;
    QueueHandle_t configurations_{};
    TaskHandle_t task_{};
    esp_netif_t* netif_{};
    esp_event_handler_instance_t wifi_handler_{}, ip_handler_{};
    std::atomic<bool> connected_{false};
    std::atomic<uint8_t> result_{0};
    std::mutex state_mutex_;
    std::string ssid_;
    std::array<uint8_t,4> ip_{};
};
