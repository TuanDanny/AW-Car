#pragma once
#include <driver/gpio.h>
#include <led_strip.h>
#include <mutex>
#include <string>
#include "led/led.h"
#include "status_indicator.h"

// One writer in the background status task. Chat and tools never own this pixel.
class AwCarStatusLed : public Led {
 public:
  explicit AwCarStatusLed(gpio_num_t gpio);
  ~AwCarStatusLed() override;
  void OnStateChanged() override {}
  void Update(awcar::indicator::State desired, uint64_t now);
  std::string SnapshotJson();
 private:
  std::mutex mutex_;
  led_strip_handle_t strip_ = nullptr;
  awcar::indicator::State desired_{};
  awcar::indicator::OutputCache output_;
  uint32_t write_max_us_ = 0;
};
