#include "laser_diag.hpp"
#include "sensor_telemetry.hpp"

#include "driver/i2c_master.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "vl53l0x_idf.h"
#include "vl53l0x_platform.h"

namespace motion {
namespace {

constexpr char kTag[]="laser_diag";
constexpr uint8_t kAddress=0x29;
constexpr uint8_t kModelIdRegister=0xc0;
constexpr uint8_t kVl53l0xModelId=0xee;
constexpr int kBusError=-2;
constexpr int kNoAck=-3;
constexpr int kInitError=-4;
constexpr int kReadError=-5;

portMUX_TYPE reading_mux=portMUX_INITIALIZER_UNLOCKED;
LaserReading reading{};

void publish(int status,bool ack,uint16_t mm=0) {
    const auto sampled_us = esp_timer_get_time();
    portENTER_CRITICAL(&reading_mux);
    reading={status,mm,ack,sampled_us};
    portEXIT_CRITICAL(&reading_mux);
}

// A single background task owns both I²C device handles, including attach/detach.
void wait_between_ranges(unsigned slots) {
    auto tick = xTaskGetTickCount();
    for (unsigned slot = 0; slot < slots; ++slot) {
        poll_mpu_telemetry();
        vTaskDelayUntil(&tick, pdMS_TO_TICKS(100));
    }
}

VL53L0X_Error initialize(VL53L0X_Dev_t& sensor) {
    uint8_t model=0;
    auto status=VL53L0X_RdByte(&sensor,kModelIdRegister,&model);
    if(status!=VL53L0X_ERROR_NONE) return status;
    if(model!=kVl53l0xModelId) return VL53L0X_ERROR_INVALID_PARAMS;

    // Select the sensor's 2.8 V I/O mode used by the powered breakout.
    status=VL53L0X_UpdateByte(&sensor,VL53L0X_REG_VHV_CONFIG_PAD_SCL_SDA__EXTSUP_HV,0xfe,0x01);
    if(status!=VL53L0X_ERROR_NONE) return status;
    status=VL53L0X_DataInit(&sensor);
    if(status!=VL53L0X_ERROR_NONE) return status;
    status=VL53L0X_StaticInit(&sensor);
    if(status!=VL53L0X_ERROR_NONE) return status;

    uint8_t vhv=0,phase=0,aperture=0;
    uint32_t spads=0;
    status=VL53L0X_PerformRefCalibration(&sensor,&vhv,&phase);
    if(status!=VL53L0X_ERROR_NONE) return status;
    status=VL53L0X_PerformRefSpadManagement(&sensor,&spads,&aperture);
    if(status!=VL53L0X_ERROR_NONE) return status;
    return VL53L0X_SetDeviceMode(&sensor,VL53L0X_DEVICEMODE_SINGLE_RANGING);
}

void laser_task(void*) {
    i2c_master_bus_config_t bus_config{};
    bus_config.i2c_port=I2C_NUM_0;
    bus_config.sda_io_num=GPIO_NUM_11;
    bus_config.scl_io_num=GPIO_NUM_12;
    bus_config.clk_source=I2C_CLK_SRC_DEFAULT;
    bus_config.glitch_ignore_cnt=7;
    i2c_master_bus_handle_t bus{};
    const esp_err_t bus_result=i2c_new_master_bus(&bus_config,&bus);
    start_mpu_telemetry(bus_result==ESP_OK ? bus : nullptr);
    if(bus_result!=ESP_OK) {
        publish(kBusError,false);
        ESP_LOGW(kTag,"I2C setup: %s",esp_err_to_name(bus_result));
        vTaskDelete(nullptr);
        return;
    }

    vl53l0x_idf_config_t config{};
    config.existing_bus=bus;
    config.i2c_address_7bit=kAddress;
    config.scl_speed_hz=100000;
    config.xshut_gpio_num=GPIO_NUM_NC;
    config.gpio1_gpio_num=GPIO_NUM_NC;

    for(;;) {
        const esp_err_t probe=i2c_master_probe(bus,kAddress,40);
        if(probe!=ESP_OK) {
            publish(probe==ESP_ERR_NOT_FOUND?kNoAck:kBusError,false);
            wait_between_ranges(10);
            continue;
        }

        publish(-1,true);
        VL53L0X_Dev_t sensor{};
        const esp_err_t attached=vl53l0x_idf_init(&sensor,&config);
        if(attached==ESP_OK) {
            const auto ready=initialize(sensor);
            if(ready==VL53L0X_ERROR_NONE) {
                ESP_LOGI(kTag,"VL53L0X ready at 0x29 on SDA11/SCL12");
                for(;;) {
                    VL53L0X_RangingMeasurementData_t sample{};
                    const auto result=VL53L0X_PerformSingleRangingMeasurement(&sensor,&sample);
                    if(result!=VL53L0X_ERROR_NONE) {
                        publish(kReadError,true);
                        ESP_LOGW(kTag,"ranging API error %d",int(result));
                        break;
                    }
                    publish(sample.RangeStatus,true,sample.RangeMilliMeter);
                    wait_between_ranges(2);
                }
            } else {
                publish(kInitError,true);
                ESP_LOGW(kTag,"sensor initialization error %d",int(ready));
            }
            vl53l0x_idf_deinit(&sensor);
        } else {
            publish(kInitError,true);
            ESP_LOGW(kTag,"sensor attach: %s",esp_err_to_name(attached));
        }
        wait_between_ranges(10);
    }
}

} // namespace

LaserReading laser_reading() {
    portENTER_CRITICAL(&reading_mux);
    const auto sample=reading;
    portEXIT_CRITICAL(&reading_mux);
    return sample;
}

void start_laser_diagnostics() {
    if(xTaskCreatePinnedToCore(laser_task,"laser_diag",6144,nullptr,1,nullptr,0)!=pdPASS) {
        publish(kBusError,false);
        start_mpu_telemetry(nullptr);
        ESP_LOGW(kTag,"could not start sensor task");
    }
}

} // namespace motion
