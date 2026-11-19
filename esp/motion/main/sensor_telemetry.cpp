#include "sensor_telemetry.hpp"
#include "laser_diag.hpp"
#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

namespace motion {
namespace {

constexpr auto kEdgeLeft = GPIO_NUM_8;
constexpr auto kEdgeRight = GPIO_NUM_9;
constexpr uint8_t kMpuAddress = 0x68;
constexpr uint8_t kMpu6050Identity = 0x68;
constexpr uint8_t kMpu6515Identity = 0x74;
constexpr int kI2cTimeoutMs = 15;

struct MpuReading {
    const char* status = "initializing";
    int who_am_i = -1;
    int address{};
    int accel_mg[3]{};
    int gyro_dps10[3]{};
    int64_t sampled_us{};
};

bool edge_ready = false; // Set before starting the Web server.
portMUX_TYPE mpu_mux = portMUX_INITIALIZER_UNLOCKED;
MpuReading mpu_reading{};
i2c_master_dev_handle_t mpu_handles[2]{};
i2c_master_dev_handle_t mpu_device{};
int64_t mpu_retry_us{};
int mpu_identity = -1; // Only accessed by the I²C task.
int mpu_address{};

void publish_mpu(const MpuReading& sample) {
    portENTER_CRITICAL(&mpu_mux);
    mpu_reading = sample;
    portEXIT_CRITICAL(&mpu_mux);
}

const char* initialize_mpu(i2c_master_dev_handle_t device) {
    constexpr uint8_t who_am_i = 0x75;
    uint8_t identity{};
    mpu_identity = -1;
    if (i2c_master_transmit_receive(device, &who_am_i, 1, &identity, 1, kI2cTimeoutMs) != ESP_OK)
        return "unavailable";
    mpu_identity = identity;
    if (identity != kMpu6050Identity && identity != kMpu6515Identity) return "wrong_device";
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

void attach_mpu_handles(i2c_master_bus_handle_t bus) {
    i2c_device_config_t config{};
    config.dev_addr_length = I2C_ADDR_BIT_LEN_7;
    config.scl_speed_hz = 100000;
    if (bus) {
        for (int i = 0; i < 2; ++i) {
            config.device_address = kMpuAddress + i;
            i2c_master_bus_add_device(bus, &config, &mpu_handles[i]);
        }
    }
    if (!mpu_handles[0] && !mpu_handles[1])
        publish_mpu({"bus_error"});
}

void poll_mpu_telemetry() {
    if ((!mpu_handles[0] && !mpu_handles[1]) || esp_timer_get_time() < mpu_retry_us) return;
    if (!mpu_device) {
        MpuReading failure{"unavailable"};
        for (int i = 0; i < 2; ++i) {
            if (!mpu_handles[i]) continue;
            const char* error = initialize_mpu(mpu_handles[i]);
            if (!error) {
                mpu_device = mpu_handles[i];
                mpu_address = kMpuAddress + i;
                mpu_retry_us = esp_timer_get_time() + 80000;
                publish_mpu({"initializing", mpu_identity, mpu_address});
                return;
            }
            if (mpu_identity >= 0) failure = {error, mpu_identity, kMpuAddress + i};
        }
        publish_mpu(failure);
        mpu_retry_us = esp_timer_get_time() + 1000000;
        return;
    }
    constexpr uint8_t accel_xout_h = 0x3b;
    uint8_t bytes[14]{};
    if (i2c_master_transmit_receive(mpu_device, &accel_xout_h, 1, bytes, sizeof(bytes), kI2cTimeoutMs) != ESP_OK) {
        publish_mpu({"read_error", mpu_identity, mpu_address});
        mpu_device = nullptr;
        mpu_retry_us = esp_timer_get_time() + 1000000;
        return;
    }
    MpuReading sample{"ok", mpu_identity, mpu_address};
    for (int axis = 0; axis < 3; ++axis) {
        sample.accel_mg[axis] = signed_word(bytes + 2 * axis) * 1000 / 16384;
        sample.gyro_dps10[axis] = signed_word(bytes + 8 + 2 * axis) * 10 / 131;
    }
    sample.sampled_us = esp_timer_get_time();
    publish_mpu(sample);
}

void mpu_task(void*) {
    i2c_master_bus_config_t config{};
    config.i2c_port = I2C_NUM_1;
    config.sda_io_num = GPIO_NUM_6;
    config.scl_io_num = GPIO_NUM_7;
    config.clk_source = I2C_CLK_SRC_DEFAULT;
    config.glitch_ignore_cnt = 7;
    i2c_master_bus_handle_t bus{};
    const auto result = i2c_new_master_bus(&config, &bus);
    attach_mpu_handles(result == ESP_OK ? bus : nullptr);
    if (!mpu_handles[0] && !mpu_handles[1]) {
        ESP_LOGW("sensor_status", "MPU setup failed on SDA6/SCL7");
        vTaskDelete(nullptr);
        return;
    }

    auto tick = xTaskGetTickCount();
    for (;;) {
        poll_mpu_telemetry();
        vTaskDelayUntil(&tick, pdMS_TO_TICKS(100));
    }
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

void start_mpu_telemetry() {
    if (xTaskCreatePinnedToCore(mpu_task, "mpu_telemetry", 4096, nullptr, 1, nullptr, 0) != pdPASS)
        publish_mpu({"bus_error"});
}

MpuDiagnostic mpu_diagnostic() {
    portENTER_CRITICAL(&mpu_mux);
    const auto sample = mpu_reading;
    portEXIT_CRITICAL(&mpu_mux);
    const bool fresh = sample.sampled_us && esp_timer_get_time() - sample.sampled_us <= 500000;
    return {sample.who_am_i, fresh, sample.accel_mg[2], sample.address};
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
    if (mpu.who_am_i >= 0) cJSON_AddNumberToObject(sensors, "mpu_who_am_i", mpu.who_am_i);
    if (mpu.address) cJSON_AddNumberToObject(sensors, "mpu_address", mpu.address);
    if (mpu.sampled_us && !stale) {
        cJSON_AddItemToObject(sensors, "accel_mg", cJSON_CreateIntArray(mpu.accel_mg, 3));
        cJSON_AddItemToObject(sensors, "gyro_dps10", cJSON_CreateIntArray(mpu.gyro_dps10, 3));
    }
}

} // namespace motion
