#pragma once
#include <led_strip.h>
#include "led/led.h"
class StatusLed : public Led {
public:
    StatusLed();
    void OnStateChanged() override {} // Observation is driven by the UART worker snapshot.
    void Observe(bool wifi, bool cloud, bool listening, bool speaking);
private:
    led_strip_handle_t strip_{};
    int color_{-1};
    uint64_t retry_at_{};
};
