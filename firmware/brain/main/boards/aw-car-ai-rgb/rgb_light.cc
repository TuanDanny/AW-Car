#include "rgb_light.h"

#include <esp_log.h>
#include <cstdio>

namespace {
constexpr const char* TAG = "AwCarRgb";
}

AwCarRgbLight::AwCarRgbLight(gpio_num_t gpio) {
    led_strip_config_t config = {};
    config.strip_gpio_num = gpio;
    config.max_leds = 1;
    config.color_component_format = LED_STRIP_COLOR_COMPONENT_FMT_GRB;
    config.led_model = LED_MODEL_WS2812;
    led_strip_rmt_config_t rmt = {};
    rmt.resolution_hz = 10 * 1000 * 1000;
    ESP_ERROR_CHECK(led_strip_new_rmt_device(&config, &rmt, &strip_));
    ESP_ERROR_CHECK(led_strip_clear(strip_));
    ESP_LOGI(TAG, "Ready gpio=%d, power=off; RGB is controlled only by MCP", gpio);
}

AwCarRgbLight::~AwCarRgbLight() {
    if (strip_ != nullptr) {
        led_strip_del(strip_);
    }
}

void AwCarRgbLight::RegisterTools(McpServer& server) {
    server.AddTool("self.rgb_light.set_power",
        "控制ESP32板载RGB灯的开关。把灯打开、开灯: on=true; "
        "把灯关掉吧、关灯、熄灯: on=false。开灯恢复上次颜色，首次为白色。"
        "需要指定颜色或编号（例如把红灯打开、打开一号灯）时请直接调用set_color，设置颜色会自动开灯。",
        PropertyList({Property("on", kPropertyTypeBoolean)}),
        [this](const PropertyList& properties) -> ToolResult {
            return SetPower(properties["on"].value<bool>());
        });
    server.AddTool("self.rgb_light.set_color",
        "设置ESP32板载RGB灯颜色并立即开灯。红灯、把红灯打开: r=255,g=0,b=0; "
        "绿灯、把绿灯打开: r=0,g=255,b=0; 蓝灯、把蓝灯打开: r=0,g=0,b=255。"
        "也支持编号简称: 一号灯、一号、1号=r255,g0,b0红色; 二号灯、二号、2号=r0,g255,b0绿色; "
        "三号灯、三号、3号=r0,g0,b255蓝色。编号是同一颗RGB灯的颜色预设，不是多个灯。"
        "支持每个颜色分量0到255。颜色和开关保持到下一条灯控命令，聊天不会覆盖。",
        PropertyList({Property("r", kPropertyTypeInteger, 0, 255),
                      Property("g", kPropertyTypeInteger, 0, 255),
                      Property("b", kPropertyTypeInteger, 0, 255)}),
        [this](const PropertyList& properties) -> ToolResult {
            return SetColor(properties["r"].value<int>(), properties["g"].value<int>(),
                            properties["b"].value<int>());
        });
    server.AddTool("self.rgb_light.get_state",
        "读取板载RGB灯最近成功写入的开关power和颜色r/g/b；这是软件状态，不是光学测量。",
        PropertyList(), [this](const PropertyList&) -> ToolResult { return GetState(); });
    ESP_LOGI(TAG, "Tools registered: self.rgb_light.set_power / set_color / get_state");
}

ToolResult AwCarRgbLight::SetPower(bool on) {
    std::lock_guard<std::mutex> lock(mutex_);
    return ApplyLocked(on, r_, g_, b_);
}

ToolResult AwCarRgbLight::SetColor(int r, int g, int b) {
    if (r < 0 || r > 255 || g < 0 || g > 255 || b < 0 || b > 255) {
        return std::unexpected("RGB components must be integers in 0..255");
    }
    std::lock_guard<std::mutex> lock(mutex_);
    return ApplyLocked(true, r, g, b);
}

ToolResult AwCarRgbLight::ApplyLocked(bool on, uint8_t r, uint8_t g, uint8_t b) {
    esp_err_t result;
    if (on) {
        result = led_strip_set_pixel(strip_, 0, r, g, b);
        if (result == ESP_OK) {
            result = led_strip_refresh(strip_);
        }
    } else {
        result = led_strip_clear(strip_);
    }
    if (result != ESP_OK) {
        state_known_ = false;
        ESP_LOGE(TAG, "RGB write failed: %s", esp_err_to_name(result));
        return std::unexpected(std::string("RGB write failed; output state unknown: ") +
                               esp_err_to_name(result));
    }
    power_ = on;
    r_ = r;
    g_ = g;
    b_ = b;
    state_known_ = true;
    ESP_LOGI(TAG, "APPLIED power=%s r=%u g=%u b=%u", on ? "on" : "off", r_, g_, b_);
    return ReturnValue(StateJsonLocked());
}

ToolResult AwCarRgbLight::GetState() {
    std::lock_guard<std::mutex> lock(mutex_);
    if (!state_known_) {
        return std::unexpected("RGB output state unknown after a write failure; retry the command");
    }
    return ReturnValue(StateJsonLocked());
}

std::string AwCarRgbLight::StateJsonLocked() const {
    char json[96];
    std::snprintf(json, sizeof(json), "{\"power\":%s,\"r\":%u,\"g\":%u,\"b\":%u}",
                  power_ ? "true" : "false", r_, g_, b_);
    return json;
}
