#pragma once

#include <cstdint>

namespace motion {

struct LaserReading {
    int status=-1;
    uint16_t mm=0;
    bool ack=false;
    int64_t sampled_us=0;
};

LaserReading laser_reading();
void start_laser_diagnostics();

} // namespace motion
