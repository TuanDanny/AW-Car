#pragma once

#include "led/led.h"
#include "mcp_server.h"

#include <driver/gpio.h>
#include <led_strip.h>
#include <cstdint>
#include <mutex>
#include <string>

// Sole owner of the onboard pixel. Chat/VAD state must not override a command.
class AwCarRgbLight : public Led {
public:
    explicit AwCarRgbLight(gpio_num_t gpio);
    ~AwCarRgbLight() override;
    void RegisterTools(McpServer& server);
    void OnStateChanged() override {}

private:
    std::mutex mutex_;
    led_strip_handle_t strip_ = nullptr;
    bool power_ = false;
    bool state_known_ = true;
    uint8_t r_ = 32, g_ = 32, b_ = 32;

    ToolResult SetPower(bool on);
    ToolResult SetColor(int r, int g, int b);
    ToolResult GetState();
    ToolResult ApplyLocked(bool on, uint8_t r, uint8_t g, uint8_t b);
    std::string StateJsonLocked() const;
};
