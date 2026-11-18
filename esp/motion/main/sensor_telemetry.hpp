#pragma once
#include "cJSON.h"

namespace motion {
void start_edge_inputs();
void start_mpu_telemetry();
struct MpuDiagnostic {
    int identity;
    bool fresh;
    int accel_z_mg;
    int address;
};
MpuDiagnostic mpu_diagnostic();
void add_sensor_status(cJSON* status);
}
