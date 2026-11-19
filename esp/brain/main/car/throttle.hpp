#pragma once

namespace brain {
inline constexpr int kDefaultThrottlePercent = 20;

// Accepts a 0–100% MCP input. Match the Web dashboard throttle scale.
constexpr int ThrottleToDutyPercent(int throttle) {
    if (throttle == 0) return 0;
    return 45 + ((throttle - 1) * 55 + 49) / 99;
}
} // namespace brain
