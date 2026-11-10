#include "simple/control.hpp"

namespace simple {
namespace { int8_t sign(int16_t v) { return v>0?1:v<0?-1:0; } }
void Control::clear_target(Reason reason) {
    action_=Action::Neutral; speed_=0; desired_left_=desired_right_=left_=right_=0;
    deadline_=wake_until_=0; driver_=false; reason_=reason;
}
void Control::stop(Reason reason) {
    ++generation_; if(generation_==0) ++generation_;
    mode_=Mode::Manual; clear_target(maintenance_?Reason::Maintenance:reason);
}
void Control::maintenance(bool enabled) {
    if(maintenance_==enabled) return;
    maintenance_=enabled;stop(enabled?Reason::Maintenance:Reason::Stop);
}
void Control::set_mode(Mode mode) {
    if(maintenance_) return;
    ++generation_; if(generation_==0) ++generation_;
    mode_=mode; clear_target(Reason::ModeChanged);
}
void Control::target(Action a,uint8_t speed,uint64_t deadline) {
    if(a==Action::Neutral || speed==0) { clear_target(Reason::Released); return; }
    action_=a; speed_=speed; deadline_=deadline; reason_=Reason::Released;
    const int16_t duty=int16_t((unsigned(speed)*kDutyMax+50)/100);
    switch(a) {
        case Action::Forward:desired_left_=duty;desired_right_=duty;break;
        case Action::Backward:desired_left_=-duty;desired_right_=-duty;break;
        case Action::Left:desired_left_=-duty;desired_right_=duty;break;
        case Action::Right:desired_left_=duty;desired_right_=-duty;break;
        default:clear_target(Reason::Invalid);break;
    }
}
bool Control::manual(Action a,uint8_t speed,uint64_t now) {
    now_=now;
    if(maintenance_ || mode_!=Mode::Manual || !valid_action(a) || speed>100) return false;
    if(a!=Action::Neutral && speed>0 && !fpga_connected(now)) return false;
    target(a,speed,now+500); return true;
}
bool Control::ai(const AiMove& m,uint64_t now) {
    now_=now;
    if(maintenance_ || mode_!=Mode::Ai || m.generation!=generation_ || !valid_action(m.action) || m.speed>100 ||
       (m.duration_ms!=0 && (m.duration_ms<100 || m.duration_ms>3000)) ||
       !fpga_connected(now) || !brain_connected(now) ||
       (brain_.flags&(kWifiReady|kCloudReady))!=(kWifiReady|kCloudReady)) return false;
    target(m.action,m.speed,now+(m.duration_ms?m.duration_ms:kAiDefaultDurationMs)); return true;
}
void Control::brain(const BrainState& state,uint64_t now) { brain_=state;brain_at_=now;brain_seen_=true; }
void Control::fpga(const SpiStatus& state,uint64_t now) { fpga_=state;fpga_at_=now;fpga_seen_=true; }
void Control::tick(uint64_t now) {
    now_=now;
    if(action_==Action::Neutral) { left_=right_=0;driver_=false;return; }
    if(!fpga_connected(now)) { stop(Reason::FpgaLost);return; }
    if(mode_==Mode::Ai && !brain_connected(now)) { stop(Reason::BrainLost);return; }
    if(mode_==Mode::Ai && (brain_.flags&(kWifiReady|kCloudReady))!=(kWifiReady|kCloudReady)) { stop(Reason::InternetLost);return; }
    if(now>=deadline_) { clear_target(mode_==Mode::Manual?Reason::ManualTimeout:Reason::AiComplete);return; }
    const bool reverse_left=desired_left_ && last_left_sign_ && sign(desired_left_)!=last_left_sign_ && now-last_left_at_<40;
    const bool reverse_right=desired_right_ && last_right_sign_ && sign(desired_right_)!=last_right_sign_ && now-last_right_at_<40;
    if(reverse_left || reverse_right) { left_=right_=0;driver_=false;wake_until_=0;reason_=Reason::Reversing;return; }
    if(!driver_) { driver_=true;wake_until_=now+1;left_=right_=0;reason_=Reason::Waking;return; }
    if(now<wake_until_) { left_=right_=0;reason_=Reason::Waking;return; }
    left_=desired_left_; right_=desired_right_;
    if(left_) { last_left_sign_=sign(left_);last_left_at_=now; }
    if(right_) { last_right_sign_=sign(right_);last_right_at_=now; }
    reason_=Reason::Active;
}
MotionState Control::state() const {
    return {generation_,mode_,action_,speed_,reason_,left_,right_,fpga_connected(now_),fpga_.left_count,fpga_.right_count,fpga_.applied_seq};
}
} // namespace simple
