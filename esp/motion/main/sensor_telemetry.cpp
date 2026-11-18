#include "sensor_telemetry.hpp"
#include "laser_diag.hpp"
#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"

namespace motion {
namespace {

constexpr auto kEdgeLeft = GPIO_NUM_8;
constexpr auto kEdgeRight = GPIO_NUM_9;
constexpr uint8_t kMpuAddress = 0x68;
constexpr int kI2cTimeoutMs = 15;

struct MpuReading {
    const char* status = "initializing";
    int accel_mg[3]{};
    int gyro_dps10[3]{};
    int64_t sampled_us{};
};

bool edge_ready = false; // Set before starting the Web server.
portMUX_TYPE mpu_mux = portMUX_INITIALIZER_UNLOCKED;
MpuReading mpu_reading{};
i2c_master_dev_handle_t mpu_device{};
bool mpu_awake{};
int64_t mpu_retry_us{};

void publish_mpu(const MpuReading& sample) {
    portENTER_CRITICAL(&mpu_mux);
    mpu_reading = sample;
    portEXIT_CRITICAL(&mpu_mux);
}

const char* initialize_mpu(i2c_master_dev_handle_t device) {
    constexpr uint8_t who_am_i = 0x75;
    uint8_t identity{};
    if (i2c_master_transmit_receive(device, &who_am_i, 1, &identity, 1, kI2cTimeoutMs) != ESP_OK)
        return "unavailable";
    if (identity != 0x68) return "wrong_device";
    constexpr uint8_t wake[] = {0x6b, 0x01}; // Wake, PLL clock.
    constexpr uint8_t ranges[] = {0x1a, 0x03, 0x00, 0x00}; // DLPF, ±250 °/s, ±2 g.
    if (i2c_master_transmit(device, wake, sizeof(wake), kI2cTimeoutMs) != ESP_OK ||
        i2c_master_transmit(device, ranges, sizeof(ranges), kI2cTimeoutMs) != ESP_OK)
        return "read_error";
    return nullptr;
}

int signed_word(const uint8_t* bytes) {
    const int word = (int(bytes[0]) << 8) | bytes[1];
    return word >= 0x8000 ? word - 0x10000 : word;
}

} // namespace

void start_edge_inputs() {
    gpio_config_t config{};
    config.pin_bit_mask = (1ULL << kEdgeLeft) | (1ULL << kEdgeRight);
    config.mode = GPIO_MODE_INPUT;
    config.pull_down_en = GPIO_PULLDOWN_ENABLE;
    edge_ready = gpio_config(&config) == ESP_OK;
    if (!edge_ready) ESP_LOGW("sensor_status", "TCRT5000 input setup failed");
}

void start_mpu_telemetry(i2c_master_bus_handle_t bus) {
    i2c_device_config_t config{};
    config.dev_addr_length = I2C_ADDR_BIT_LEN_7;
    config.device_address = kMpuAddress;
    config.scl_speed_hz = 100000;
    if (!bus || i2c_master_bus_add_device(bus, &config, &mpu_device) != ESP_OK)
        publish_mpu({"bus_error"});
}

void poll_mpu_telemetry() {
    if (!mpu_device || esp_timer_get_time() < mpu_retry_us) return;
    if (!mpu_awake) {
        if (const char* error = initialize_mpu(mpu_device)) {
            publish_mpu({error});
            mpu_retry_us = esp_timer_get_time() + 1000000;
        } else {
            mpu_awake = true;
            mpu_retry_us = esp_timer_get_time() + 80000;
            publish_mpu({});
        }
        return;
    }
    constexpr uint8_t accel_xout_h = 0x3b;
    uint8_t bytes[14]{};
    if (i2c_master_transmit_receive(mpu_device, &accel_xout_h, 1, bytes, sizeof(bytes), kI2cTimeoutMs) != ESP_OK) {
        publish_mpu({"read_error"});
        mpu_awake = false;
        mpu_retry_us = esp_timer_get_time() + 1000000;
        return;
    }
    MpuReading sample{"ok"};
    for (int axis = 0; axis < 3; ++axis) {
        sample.accel_mg[axis] = signed_word(bytes + 2 * axis) * 1000 / 16384;
        sample.gyro_dps10[axis] = signed_word(bytes + 8 + 2 * axis) * 10 / 131;
    }
    sample.sampled_us = esp_timer_get_time();
    publish_mpu(sample);
}

void add_sensor_status(cJSON* status) {
    auto* sensors = cJSON_AddObjectToObject(status, "sensors");
    if (!sensors) return;
    const auto tof = laser_reading();
    portENTER_CRITICAL(&mpu_mux);
    const auto mpu = mpu_reading;
    portEXIT_CRITICAL(&mpu_mux);
    const auto now = esp_timer_get_time();
    const int tof_status = tof.sampled_us && now - tof.sampled_us > 800000 ? -6 : tof.status;
    cJSON_AddNumberToObject(sensors, "tof_status", tof_status);
    if (tof_status == 0) cJSON_AddNumberToObject(sensors, "tof_mm", tof.mm);
    if (edge_ready) {
        const int levels[] = {gpio_get_level(kEdgeLeft), gpio_get_level(kEdgeRight)};
        cJSON_AddItemToObject(sensors, "edge_do", cJSON_CreateIntArray(levels, 2));
    }
    const bool stale = mpu.sampled_us && now - mpu.sampled_us > 500000;
    cJSON_AddStringToObject(sensors, "mpu_status", stale ? "stale" : mpu.status);
    if (mpu.sampled_us && !stale) {
        cJSON_AddItemToObject(sensors, "accel_mg", cJSON_CreateIntArray(mpu.accel_mg, 3));
        cJSON_AddItemToObject(sensors, "gyro_dps10", cJSON_CreateIntArray(mpu.gyro_dps10, 3));
    }
}

} // namespace motion
