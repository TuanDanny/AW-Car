#include "status_led.h"
#include "config.h"
#include <esp_log.h>
#include <esp_timer.h>
StatusLed::StatusLed() {
    led_strip_config_t config{};
    config.strip_gpio_num = BUILTIN_LED_GPIO;
    config.max_leds = 1;
    config.led_model = LED_MODEL_WS2812;
    config.color_component_format = LED_STRIP_COLOR_COMPONENT_FMT_GRB;
    led_strip_rmt_config_t rmt{};
    rmt.clk_src = RMT_CLK_SRC_DEFAULT;
    rmt.resolution_hz = 10000000;
    if (led_strip_new_rmt_device(&config, &rmt, &strip_) != ESP_OK) {
        strip_ = nullptr;
        ESP_LOGW("StatusLed", "Observer unavailable");
    }
}
void StatusLed::Observe(bool wifi, bool cloud, bool listening, bool speaking) {
    (void)listening;
    (void)speaking;
    // Observes readiness only; listening/speaking never takes ownership of RGB.
    const int color = wifi && cloud ? 1 : 0;
    const auto now = uint64_t(esp_timer_get_time() / 1000);
    if (!strip_ || color == color_ || now < retry_at_) return;
    static constexpr uint8_t rgb[][3] = {{0,0,8},{0,8,0}};
    auto err = led_strip_set_pixel(strip_, 0, rgb[color][0], rgb[color][1], rgb[color][2]);
    if (err == ESP_OK) err = led_strip_refresh(strip_);
    if (err == ESP_OK) color_ = color;
    else retry_at_ = now + 1000;
}
