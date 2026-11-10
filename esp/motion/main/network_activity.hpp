#pragma once
#include "simple/protocol.hpp"

namespace motion {
// Waking/reversing still own a motion intent even while their PWM is zero.
constexpr bool network_motion_busy(const simple::MotionState& state,
                                   bool command_pending,bool updating) {
    return state.action!=simple::Action::Neutral || state.left || state.right ||
           command_pending || updating;
}
}
