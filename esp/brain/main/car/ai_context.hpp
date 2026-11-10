#pragma once
#include <cstdint>
#include <string>
#include "simple/protocol.hpp"

namespace brain {
// Copied at cloud ingress, before McpServer queues a callback. No execution-time rebinding.
struct DriveContext {
    uint32_t generation{};
    uint64_t conversation{}, revision{};
    bool valid{};
};

// Caller serializes access. Header-only so host tests execute the firmware policy.
class AiContext {
public:
    static constexpr uint64_t kMotionTimeoutMs = 500;
    void UpdateMotion(const simple::MotionState& state, uint64_t now) {
        if (have_motion_ && (!MotionFresh(now) || state.generation != motion_.generation || state.mode != motion_.mode))
            Invalidate();
        motion_ = state;
        motion_at_ = now;
        have_motion_ = true;
        if (state.mode != simple::Mode::Ai) Invalidate();
    }
    bool MotionFresh(uint64_t now) const {
        return have_motion_ && now >= motion_at_ && now - motion_at_ <= kMotionTimeoutMs;
    }
    const simple::MotionState& motion() const { return motion_; }
    void Invalidate() { ++revision_; bound_ = {}; session_.clear(); }
    DriveContext BeginExplicit(uint64_t now) {
        Invalidate();
        ++conversation_;
        return {motion_.generation, conversation_, revision_,
                MotionFresh(now) && motion_.mode == simple::Mode::Ai};
    }
    bool Bind(const DriveContext& start, const std::string& actual_session, uint64_t now) {
        if (!Current(start, now) || actual_session.empty() || actual_session.size() > 128 ||
            actual_session == previous_session_) return false;
        session_ = actual_session;
        previous_session_ = actual_session;
        bound_ = start;
        return true;
    }
    DriveContext Capture(const std::string& actual_session, uint64_t now) const {
        if (actual_session.empty() || actual_session != session_ || !Current(bound_, now)) return {};
        return bound_;
    }
    bool CanMove(const DriveContext& context, uint64_t now) const {
        return !session_.empty() && Current(bound_, now) && Current(context, now);
    }
    void AudioClosed() {
        // A fresh request clears session_ before closing the previous transport.
        if (!session_.empty()) Invalidate();
    }
private:
    bool Current(const DriveContext& context, uint64_t now) const {
        return context.valid && context.revision == revision_ &&
            context.conversation == conversation_ && MotionFresh(now) &&
            motion_.mode == simple::Mode::Ai && context.generation == motion_.generation;
    }
    simple::MotionState motion_{};
    uint64_t motion_at_{}, revision_{}, conversation_{};
    bool have_motion_{};
    DriveContext bound_{};
    std::string session_, previous_session_;
};
} // namespace brain
