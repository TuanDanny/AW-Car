// OLED/audio construction follows Xiaozhi v2.5.2 bread-compact-wifi (MIT).
#include "board.h"
#include "application.h"
#include "button.h"
#include "codecs/no_audio_codec.h"
#include "config.h"
#include "display/oled_display.h"
#include "audio_codec.h"
#include "sta_network.h"
#include "status_led.h"
#include "car/runtime.h"
#include <driver/i2c_master.h>
#include <esp_lcd_panel_ops.h>
#include <esp_lcd_panel_vendor.h>
#include <esp_network.h>
#include <esp_wifi.h>
#include <material_symbols.h>
#include <cJSON.h>

class AwCarBoard final : public Board {
    i2c_master_bus_handle_t display_bus_{};
    Display* display_{};
    Button boot_{BOOT_BUTTON_GPIO};
    StatusLed led_;
    StaNetwork wifi_;
    NetworkEventCallback callback_;
public:
    AwCarBoard() {
        i2c_master_bus_config_t bus{};
        bus.i2c_port = I2C_NUM_0; bus.sda_io_num = DISPLAY_SDA_PIN; bus.scl_io_num = DISPLAY_SCL_PIN;
        bus.clk_source = I2C_CLK_SRC_DEFAULT; bus.glitch_ignore_cnt = 7;
        bus.flags.enable_internal_pullup = true;
        ESP_ERROR_CHECK(i2c_new_master_bus(&bus, &display_bus_));
        esp_lcd_panel_io_i2c_config_t io{};
        io.dev_addr=0x3C; io.scl_speed_hz=400000; io.control_phase_bytes=1;
        io.dc_bit_offset=6; io.lcd_cmd_bits=8; io.lcd_param_bits=8;
        esp_lcd_panel_io_handle_t panel_io{};
        ESP_ERROR_CHECK(esp_lcd_new_panel_io_i2c(display_bus_, &io, &panel_io));
        esp_lcd_panel_dev_config_t config{};
        config.reset_gpio_num=GPIO_NUM_NC; config.bits_per_pixel=1;
        esp_lcd_panel_ssd1306_config_t oled{}; oled.height=64; config.vendor_config=&oled;
        esp_lcd_panel_handle_t panel{};
        ESP_ERROR_CHECK(esp_lcd_new_panel_ssd1306(panel_io, &config, &panel));
        ESP_ERROR_CHECK(esp_lcd_panel_reset(panel)); ESP_ERROR_CHECK(esp_lcd_panel_init(panel));
        ESP_ERROR_CHECK(esp_lcd_panel_invert_color(panel, false));
        ESP_ERROR_CHECK(esp_lcd_panel_disp_on_off(panel, true));
        display_ = new OledDisplay(panel_io, panel, 128, 64, true, true);
        boot_.OnClick([] { Application::GetInstance().StartListening(); });
    }
    std::string GetBoardType() override { return "wifi"; }
    NetworkInterface* GetNetwork() override { static EspNetwork network; return &network; }
    void SetNetworkEventCallback(NetworkEventCallback callback) override { callback_=std::move(callback); }
    void StartNetwork() override {
        wifi_.Start([this](NetworkEvent event, const std::string& data) { if(callback_) callback_(event,data); });
        brain::Runtime::Get().Start(&wifi_, &led_);
    }
    const char* GetNetworkStateIcon() override { return wifi_.Connected() ? MATERIAL_SYMBOLS_WIFI : MATERIAL_SYMBOLS_WIFI_OFF; }
    // StaNetwork sets WIFI_PS_NONE once with a checked return code.
    void SetPowerSaveLevel(PowerSaveLevel) override {}
    std::string GetBoardJson() override { return wifi_.Json(); }
    std::string GetDeviceStatusJson() override {
        auto* json = cJSON_Parse(wifi_.Json().c_str());
        if (!json) return "{}";
        cJSON_AddNumberToObject(json, "speaker_volume", GetAudioCodec()->output_volume());
        auto* text = cJSON_PrintUnformatted(json);
        std::string result = text ? text : "{}";
        cJSON_free(text); cJSON_Delete(json);
        return result;
    }
    Led* GetLed() override { return &led_; }
    Display* GetDisplay() override { return display_; }
    AudioCodec* GetAudioCodec() override {
        static NoAudioCodecSimplex codec(AUDIO_INPUT_SAMPLE_RATE, AUDIO_OUTPUT_SAMPLE_RATE,
            AUDIO_I2S_SPK_GPIO_BCLK, AUDIO_I2S_SPK_GPIO_LRCK, AUDIO_I2S_SPK_GPIO_DOUT,
            AUDIO_I2S_MIC_GPIO_SCK, AUDIO_I2S_MIC_GPIO_WS, AUDIO_I2S_MIC_GPIO_DIN);
        return &codec;
    }
};
DECLARE_BOARD(AwCarBoard);
