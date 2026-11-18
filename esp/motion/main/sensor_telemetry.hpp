#pragma once
#include "driver/i2c_master.h"
#include "cJSON.h"

namespace motion {
void start_edge_inputs();
void start_mpu_telemetry(i2c_master_bus_handle_t bus);
void poll_mpu_telemetry();
void add_sensor_status(cJSON* status);
}
