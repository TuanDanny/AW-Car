#pragma once
#include "simple/protocol.hpp"

namespace simple {
// Exactly one owner calls this class. now_ms is monotonic, injectable on host.
class Control {
public:
    explicit Control(uint32_t generation=1): generation_(generation?generation:1) {}
    void stop(Reason reason=Reason::Stop);
    void maintenance(bool enabled);
    bool maintaining() const { return maintenance_; }
    void set_mode(Mode mode);
    void takeover() { stop(Reason::Takeover); }
    void disconnect() { if(mode_==Mode::Manual) stop(Reason::Released); }
    bool manual(Action action,uint8_t speed,uint64_t now_ms);
    bool ai(const AiMove& move,uint64_t now_ms);
    void brain(const BrainState& state,uint64_t now_ms);
    void fpga(const SpiStatus& state,uint64_t now_ms);
    void tick(uint64_t now_ms);
    MotionState state() const;
    const BrainState& brain_state() const { return brain_; }
    bool brain_connected(uint64_t now_ms) const { return brain_seen_ && (now_ms<=brain_at_ || now_ms-brain_at_<=500); }
    bool fpga_connected(uint64_t now_ms) const { return fpga_seen_ && (now_ms<=fpga_at_ || now_ms-fpga_at_<=500); }
    bool driver_enabled() const { return driver_; }
private:
    void clear_target(Reason reason);
    void target(Action action,uint8_t speed,uint64_t deadline);
    uint32_t generation_;
    Mode mode_{Mode::Manual};
    Action action_{Action::Neutral};
    uint8_t speed_{};
    Reason reason_{Reason::Boot};
    int16_t desired_left_{},desired_right_{},left_{},right_{};
    int8_t last_left_sign_{},last_right_sign_{};
    uint64_t deadline_{},last_left_at_{},last_right_at_{},wake_until_{},brain_at_{},fpga_at_{},now_{};
    bool driver_{},brain_seen_{},fpga_seen_{},maintenance_{};
    BrainState brain_{};
    SpiStatus fpga_{};
};
} // namespace simple
