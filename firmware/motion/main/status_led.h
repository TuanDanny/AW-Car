#pragma once
#include "driver/gpio.h"
#include "led_strip.h"
#include "status_indicator.h"

namespace awcar::motion {
// Owned only by StatsTask. No LED I/O or lock is added to the control/ISR path.
class StatusLed {
 public:
  void Init(gpio_num_t pin);
  void Update(indicator::State state, uint64_t now);
  const indicator::OutputCache& Output() const { return output_; }
  uint32_t MaxWriteUs() const { return max_us_; }
 private:
  led_strip_handle_t strip_ = nullptr;
  indicator::OutputCache output_;
  uint32_t max_us_ = 0;
};
}  // namespace awcar::motion
