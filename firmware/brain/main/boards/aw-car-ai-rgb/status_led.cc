#include "status_led.h"
#include <esp_log.h>
#include <esp_timer.h>
#include <algorithm>
#include <cstdio>

AwCarStatusLed::AwCarStatusLed(gpio_num_t gpio) {
  led_strip_config_t config{};
  config.strip_gpio_num = gpio;
  config.max_leds = 1;
  config.color_component_format = LED_STRIP_COLOR_COMPONENT_FMT_GRB;
  config.led_model = LED_MODEL_WS2812;
  led_strip_rmt_config_t rmt{};
  rmt.resolution_hz = 10000000;
  const auto error = led_strip_new_rmt_device(&config, &rmt, &strip_);
  if (error != ESP_OK) {
    output_.Complete({}, false, uint64_t(esp_timer_get_time()));
    ESP_LOGE("AwCarLed", "init gpio=%d failed=%s; control remains independent", gpio, esp_err_to_name(error));
    return;
  }
  Update({}, uint64_t(esp_timer_get_time()));
}
AwCarStatusLed::~AwCarStatusLed() {
  if (strip_) led_strip_del(strip_);
}
void AwCarStatusLed::Update(awcar::indicator::State desired, uint64_t now) {
  using namespace awcar::indicator;
  std::lock_guard<std::mutex> lock(mutex_);
  const bool changed = desired.reason != desired_.reason;
  desired_ = desired;
  if (!strip_ || !output_.Due(desired, now)) return;
  const int64_t start = esp_timer_get_time();
  // Low fixed brightness; no PWM animation, heap allocation or busy waiting.
  auto error = led_strip_set_pixel(strip_, 0, desired.color == Color::Red ? 12 : 0,
      desired.color == Color::Green ? 12 : 0, desired.color == Color::Blue ? 12 : 0);
  if (error == ESP_OK) error = led_strip_refresh(strip_);
  write_max_us_ = std::max(write_max_us_, uint32_t(esp_timer_get_time() - start));
  output_.Complete(desired, error == ESP_OK, now);
  if (error != ESP_OK)
    ESP_LOGW("AwCarLed", "write failed=%s; retry at most 1Hz", esp_err_to_name(error));
  else if (changed || output_.Writes() == 1)
    ESP_LOGI("AwCarLed", "color=%s reason=%s writes=%lu max_us=%lu",
        Name(desired.color), Name(desired.reason), (unsigned long)output_.Writes(), (unsigned long)write_max_us_);
}
std::string AwCarStatusLed::SnapshotJson() {
  std::lock_guard<std::mutex> lock(mutex_);
  char text[224];
  std::snprintf(text, sizeof(text),
      "{\"color\":\"%s\",\"reason\":\"%s\",\"known\":%s,\"writes\":%lu,\"errors\":%lu,\"write_max_us\":%lu}",
      awcar::indicator::Name(desired_.color), awcar::indicator::Name(desired_.reason),
      output_.Known() ? "true" : "false", (unsigned long)output_.Writes(),
      (unsigned long)output_.Errors(), (unsigned long)write_max_us_);
  return text;
}
