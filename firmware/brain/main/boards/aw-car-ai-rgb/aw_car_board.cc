// OLED/audio initialization follows upstream bread-compact-wifi (MIT).
#include "wifi_board.h"
#include "codecs/no_audio_codec.h"
#include "display/oled_display.h"
#include "application.h"
#include "button.h"
#include "config.h"
#include "rgb_light.h"

#include <driver/i2c_master.h>
#include <esp_lcd_panel_ops.h>
#include <esp_lcd_panel_vendor.h>
#include <esp_log.h>

class AwCarAiRgbBoard : public WifiBoard {
private:
    i2c_master_bus_handle_t display_bus_ = nullptr;
    Display* display_ = nullptr;
    Button boot_button_;
    AwCarRgbLight rgb_;

    void InitializeDisplay() {
        i2c_master_bus_config_t bus = {};
        bus.i2c_port = I2C_NUM_0;
        bus.sda_io_num = DISPLAY_SDA_PIN;
        bus.scl_io_num = DISPLAY_SCL_PIN;
        bus.clk_source = I2C_CLK_SRC_DEFAULT;
        bus.glitch_ignore_cnt = 7;
        bus.flags.enable_internal_pullup = true;
        ESP_ERROR_CHECK(i2c_new_master_bus(&bus, &display_bus_));

        esp_lcd_panel_io_i2c_config_t io = {};
        io.dev_addr = 0x3C;
        io.scl_speed_hz = 400 * 1000;
        io.control_phase_bytes = 1;
        io.dc_bit_offset = 6;
        io.lcd_cmd_bits = 8;
        io.lcd_param_bits = 8;
        esp_lcd_panel_io_handle_t panel_io = nullptr;
        ESP_ERROR_CHECK(esp_lcd_new_panel_io_i2c(display_bus_, &io, &panel_io));

        esp_lcd_panel_dev_config_t panel_config = {};
        panel_config.reset_gpio_num = GPIO_NUM_NC;
        panel_config.bits_per_pixel = 1;
        esp_lcd_panel_ssd1306_config_t ssd1306 = {};
        ssd1306.height = DISPLAY_HEIGHT;
        panel_config.vendor_config = &ssd1306;
        esp_lcd_panel_handle_t panel = nullptr;
        ESP_ERROR_CHECK(esp_lcd_new_panel_ssd1306(panel_io, &panel_config, &panel));
        ESP_ERROR_CHECK(esp_lcd_panel_reset(panel));
        ESP_ERROR_CHECK(esp_lcd_panel_init(panel));
        ESP_ERROR_CHECK(esp_lcd_panel_invert_color(panel, false));
        ESP_ERROR_CHECK(esp_lcd_panel_disp_on_off(panel, true));
        display_ = new OledDisplay(panel_io, panel, DISPLAY_WIDTH, DISPLAY_HEIGHT,
                                   DISPLAY_MIRROR_X, DISPLAY_MIRROR_Y);
        ESP_LOGI("AwCarBoard", "SSD1306 ready SDA=41 SCL=42; BOOT starts chat");
    }

public:
    AwCarAiRgbBoard() : boot_button_(BOOT_BUTTON_GPIO), rgb_(BUILTIN_LED_GPIO) {
        InitializeDisplay();
        boot_button_.OnClick([this]() {
            auto& app = Application::GetInstance();
            if (app.GetDeviceState() == kDeviceStateStarting) {
                EnterWifiConfigMode();
                return;
            }
            app.ToggleChatState();
        });
        rgb_.RegisterTools(McpServer::GetInstance());
    }

    Led* GetLed() override { return &rgb_; }

    AudioCodec* GetAudioCodec() override {
        static NoAudioCodecSimplex codec(AUDIO_INPUT_SAMPLE_RATE, AUDIO_OUTPUT_SAMPLE_RATE,
            AUDIO_I2S_SPK_GPIO_BCLK, AUDIO_I2S_SPK_GPIO_LRCK, AUDIO_I2S_SPK_GPIO_DOUT,
            AUDIO_I2S_MIC_GPIO_SCK, AUDIO_I2S_MIC_GPIO_WS, AUDIO_I2S_MIC_GPIO_DIN);
        return &codec;
    }

    Display* GetDisplay() override { return display_; }
};

DECLARE_BOARD(AwCarAiRgbBoard);
