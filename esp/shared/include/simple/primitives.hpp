#pragma once
#include "simple/protocol.hpp"
#include <cmath>

namespace simple {
struct WheelEffort { int16_t left{},right{}; };

// Curved motions use half effort on the inside. Positive yaw turns the HEAD
// left, including in reverse. Duty ratio is not measured wheel-speed ratio.
inline WheelEffort primitive_effort(Action action,uint8_t speed) {
    if(!valid_action(action) || speed>100) return {};
    const int16_t full=int16_t((unsigned(speed)*kDutyMax+50)/100);
    const int16_t half=int16_t((unsigned(speed)*kDutyMax+100)/200);
    switch(action) {
        case Action::Forward:return {full,full};
        case Action::Backward:return {int16_t(-full),int16_t(-full)};
        case Action::Left:return {int16_t(-full),full};
        case Action::Right:return {full,int16_t(-full)};
        case Action::ForwardLeft:return {half,full};
        case Action::ForwardRight:return {full,half};
        case Action::BackwardLeft:return {int16_t(-full),int16_t(-half)};
        case Action::BackwardRight:return {int16_t(-half),int16_t(-full)};
        case Action::PivotLeft:return {0,full};
        case Action::PivotRight:return {full,0};
        default:return {};
    }
}

struct StartupConfig {
    bool enabled{false};
    uint16_t gain_percent{100}; // 100 means no boost; physical value not calibrated.
    uint16_t tau_ms{100};
};

// Allocation-free, time-based envelope. Not a safety controller or a detector
// of physical rest. Control owns deadline/reversal/wake/STOP before calling it.
class StartupEnvelope {
public:
    explicit StartupEnvelope(StartupConfig config={}):config_(config) {
        if(config_.gain_percent<100 || config_.gain_percent>300 ||
           config_.tau_ms<10 || config_.tau_ms>1000) config_=StartupConfig{};
    }
    void reset() { started_=false; }
    StartupConfig config() const { return config_; }
    WheelEffort apply(WheelEffort target,uint64_t now) {
        if(!target.left && !target.right) { reset();return {}; }
        if(!config_.enabled || config_.gain_percent==100) return target;
        if(!started_) { started_=true;at_=now; }
        const uint64_t elapsed=now>=at_?now-at_:0;
        if(elapsed>=uint64_t(5)*config_.tau_ms) return target;
        const int left=target.left<0?-int(target.left):int(target.left);
        const int right=target.right<0?-int(target.right):int(target.right);
        const int peak=left>right?left:right;
        const float requested=float(config_.gain_percent)/100;
        const float cap=float(kDutyMax)/peak;
        const float g0=requested<cap?requested:cap;
        // One expf only during startup, no heap/waits. No global input filtering.
        const float gain=1+(g0-1)*std::exp(-float(elapsed)/config_.tau_ms);
        return {scale(target.left,gain),scale(target.right,gain)};
    }
private:
    static int16_t scale(int16_t value,float gain) {
        const int rounded=int(std::round(float(value)*gain));
        return int16_t(rounded>kDutyMax?kDutyMax:rounded < -kDutyMax?-kDutyMax:rounded);
    }
    StartupConfig config_{};
    bool started_{};
    uint64_t at_{};
};
} // namespace simple
