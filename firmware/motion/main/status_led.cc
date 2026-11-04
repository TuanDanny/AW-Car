#include "status_led.h"
#include <algorithm>
#include "esp_log.h"
#include "esp_timer.h"

namespace awcar::motion {
void StatusLed::Init(gpio_num_t pin) {
  led_strip_config_t config{};
  config.strip_gpio_num = pin;
  config.max_leds = 1;
  config.color_component_format = LED_STRIP_COLOR_COMPONENT_FMT_GRB;
  config.led_model = LED_MODEL_WS2812;
  led_strip_rmt_config_t rmt{};
  rmt.resolution_hz = 10000000;
  const auto error = led_strip_new_rmt_device(&config, &rmt, &strip_);
  if (error != ESP_OK) {
    output_.Complete({}, false, uint64_t(esp_timer_get_time()));
    ESP_LOGE("MotionLed", "init gpio=%d error=%s; driver safety independent", pin, esp_err_to_name(error));
  }
}
void StatusLed::Update(indicator::State state, uint64_t now) {
  if (!strip_ || !output_.Due(state, now)) return;
  const int64_t start = esp_timer_get_time();
  auto error = led_strip_set_pixel(strip_, 0,
      state.color == indicator::Color::Red ? 12 : 0,
      state.color == indicator::Color::Green ? 12 : 0,
      state.color == indicator::Color::Blue ? 12 : 0);
  if (error == ESP_OK) error = led_strip_refresh(strip_);
  max_us_ = std::max(max_us_, uint32_t(esp_timer_get_time() - start));
  output_.Complete(state, error == ESP_OK, now);
  if (error != ESP_OK)
    ESP_LOGW("MotionLed", "write error=%s; retry at most 1Hz", esp_err_to_name(error));
  else
    ESP_LOGI("MotionLed", "color=%s reason=%s writes=%lu max_us=%lu",
        indicator::Name(state.color), indicator::Name(state.reason),
        (unsigned long)output_.Writes(), (unsigned long)max_us_);
}
}  // namespace awcar::motion
