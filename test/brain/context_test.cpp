#include "car/ai_context.hpp"
#include <cassert>
#include <functional>
#include <iostream>
#include <vector>

using brain::AiContext;
using simple::Mode;
static simple::MotionState State(uint32_t generation, Mode mode = Mode::Ai) {
    simple::MotionState s; s.generation = generation; s.mode = mode; return s;
}
static brain::DriveContext Open(AiContext& guard, uint64_t now, const char* sid) {
    auto context = guard.BeginExplicit(now);
    assert(guard.Bind(context, sid, now));
    return guard.Capture(sid, now);
}
int main() {
    int checks = 0;
    auto check = [&](bool value) { assert(value); ++checks; };
    AiContext g;
    check(!g.BeginExplicit(0).valid); // No Motion at boot.
    g.UpdateMotion(State(1, Mode::Manual), 10);
    check(!g.BeginExplicit(10).valid); // Chat in Manual never grants driving.
    g.UpdateMotion(State(2), 20);
    const auto a = Open(g,20,"session-a");
    check(g.CanMove(a,21));
    check(!g.Capture("",21).valid);
    check(!g.Capture("other-session",21).valid);
    // The cloud callback is delayed. STOP changes Motion generation before it runs.
    bool sent = false;
    auto queued = [a, &g, &sent] { sent = g.CanMove(a,30); };
    g.UpdateMotion(State(3,Mode::Manual),25);
    queued(); check(!sent);
    g.UpdateMotion(State(4),30);
    check(!g.Capture("session-a",30).valid); // Auto listen/chat cannot rebind old session.
    const auto b = Open(g,30,"session-b");
    check(g.CanMove(b,31));
    check(!g.CanMove(a,31));
    check(!g.Capture("session-a",31).valid);
    // Local STOP invalidates before the Motion ACK/state returns.
    g.Invalidate(); check(!g.CanMove(b,31));
    check(!g.Capture("session-b",31).valid);
    auto c = g.BeginExplicit(32);
    check(!g.Bind(c,"session-b",32)); // Cloud must provide a fresh actual session.
    check(g.Bind(c,"session-c",32));
    check(g.CanMove(g.Capture("session-c",32),32));
    // Context is pinned before connecting, not at a late audio-open callback.
    auto pending = g.BeginExplicit(33);
    g.UpdateMotion(State(5),34);
    check(!g.Bind(pending,"session-d",35));
    check(!g.Capture("session-d",35).valid);
    const auto d = Open(g,35,"session-e");
    // A timeout and recovery with the SAME generation must not revive a callback.
    check(!g.CanMove(d,1000));
    g.UpdateMotion(State(5),1000);
    check(!g.CanMove(d,1000));
    const auto e = Open(g,1000,"session-f");
    g.AudioClosed(); check(!g.CanMove(e,1001));
    auto f = g.BeginExplicit(1002);
    g.AudioClosed(); // Closing old transport must not invalidate an unbound fresh request.
    check(g.Bind(f,"session-g",1002));
    check(g.CanMove(f,1002));
    g.UpdateMotion(State(0),1010); // Motion reset/uint32 generation wrap.
    check(!g.CanMove(f,1010));
    const auto h = Open(g,1010,"session-h");
    check(!g.Bind(h,"",1010));
    check(!g.Bind(h,std::string(129,'x'),1010));
    check(g.CanMove(h,1011));
    // Many stale requests keep their original value; current status never upgrades them.
    std::vector<brain::DriveContext> callbacks(100,h);
    g.UpdateMotion(State(1,Mode::Manual),1020);
    g.UpdateMotion(State(2),1030);
    const auto fresh = Open(g,1030,"session-i");
    for (auto old : callbacks) check(!g.CanMove(old,1031));
    check(g.CanMove(fresh,1031));
    std::cout << "Brain context checks: " << checks << " PASS\n";
}
