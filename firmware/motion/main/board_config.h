#pragma once
#include "driver/gpio.h"
#include "driver/uart.h"
#include "sdkconfig.h"
namespace awcar::motion::board {
constexpr gpio_num_t logical = gpio_num_t(CONFIG_AWCAR_MOTION_PERMIT);
constexpr gpio_num_t driver = gpio_num_t(CONFIG_AWCAR_DRIVER_PERMIT);
constexpr gpio_num_t req = gpio_num_t(CONFIG_AWCAR_RECOVERY_REQ);
constexpr gpio_num_t ack = gpio_num_t(CONFIG_AWCAR_RECOVERY_ACK);
constexpr gpio_num_t fpga_permit = gpio_num_t(CONFIG_AWCAR_FPGA_PERMIT);
constexpr gpio_num_t safety = gpio_num_t(CONFIG_AWCAR_SAFETY_OK);
constexpr gpio_num_t gate = gpio_num_t(CONFIG_AWCAR_GATE_OK);
constexpr gpio_num_t boot = GPIO_NUM_0;
constexpr gpio_num_t status_led = gpio_num_t(CONFIG_AWCAR_STATUS_LED_GPIO);
constexpr int brain_tx = CONFIG_AWCAR_BRAIN_TX,
              brain_rx = CONFIG_AWCAR_BRAIN_RX;
constexpr int fpga_tx = CONFIG_AWCAR_FPGA_TX, fpga_rx = CONFIG_AWCAR_FPGA_RX;
#if CONFIG_AWCAR_ENABLE_DRIVER
constexpr bool allow_driver = true;
#else
constexpr bool allow_driver = false;
#endif
}  // namespace awcar::motion::board
