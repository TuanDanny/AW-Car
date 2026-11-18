#pragma once
#include <driver/gpio.h>
// Verified AW-Car bread-compact wiring; only the simplev1 UART contract changes.
#define AUDIO_INPUT_SAMPLE_RATE 16000
// MAX98357A I2S supports 48 kHz, not 24 kHz. AudioService resamples each
// cloud/OGG packet from its declared rate; never play 24 kHz PCM at 48 kHz.
#define AUDIO_OUTPUT_SAMPLE_RATE 48000
#define AUDIO_I2S_MIC_GPIO_WS GPIO_NUM_4
#define AUDIO_I2S_MIC_GPIO_SCK GPIO_NUM_5
#define AUDIO_I2S_MIC_GPIO_DIN GPIO_NUM_6
#define AUDIO_I2S_SPK_GPIO_DOUT GPIO_NUM_7
#define AUDIO_I2S_SPK_GPIO_BCLK GPIO_NUM_15
#define AUDIO_I2S_SPK_GPIO_LRCK GPIO_NUM_16
#define DISPLAY_SDA_PIN GPIO_NUM_41
#define DISPLAY_SCL_PIN GPIO_NUM_42
#define BOOT_BUTTON_GPIO GPIO_NUM_0
#define BUILTIN_LED_GPIO GPIO_NUM_48
#define BRAIN_UART_TX GPIO_NUM_17
#define BRAIN_UART_RX GPIO_NUM_18
