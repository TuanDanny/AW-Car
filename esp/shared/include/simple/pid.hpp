#pragma once
#include <algorithm>

namespace simple {
// Positional PID, derivative on measurement, bounded integrator/output.
// Algorithm reference: pms67/PID (MIT), pinned in docs/upstream.md.
// Not enabled in the initial Motion profile: two calibrated encoders required.
struct Pid {
    float kp{},ki{},kd{},dt{0.01f},tau{0.02f};
    float low{},high{1350},integral_low{-1350},integral_high{1350};
    float integral{},derivative{},previous_error{},previous_measurement{};
    void reset() { integral=derivative=previous_error=previous_measurement=0; }
    float update(float target,float measurement) {
        if(dt<=0 || tau<0 || low>high || integral_low>integral_high) return 0;
        const float error=target-measurement;
        integral=std::clamp(integral+0.5f*ki*dt*(error+previous_error),integral_low,integral_high);
        derivative=-(2*kd*(measurement-previous_measurement)+(2*tau-dt)*derivative)/(2*tau+dt);
        previous_error=error;previous_measurement=measurement;
        return std::clamp(kp*error+integral+derivative,low,high);
    }
};
} // namespace simple
