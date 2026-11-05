#include <cassert>
#include <cstdio>
#include "status_indicator.h"
using namespace awcar::indicator;
int main() {
  assert(Brain(false, -1, 0, false, false, false).reason == Reason::WifiOffline);
  assert(Brain(true, -1, 0, false, false, false).reason == Reason::MotionWaiting);
  assert(Brain(true, 149, 0, false, false, false).color == Color::Green);
  assert(Brain(true, 150, 0, false, false, true).color == Color::Red);
  assert(Brain(false, 200, 0, false, false, false).color == Color::Red);
  assert(Brain(false, -1, 1, false, false, false).color == Color::Red);
  assert(Brain(true, 0, 0, true, false, false).color == Color::Red);
  assert(Brain(true, 0, 0, false, true, false).reason == Reason::AiWaiting);
  assert(Brain(true, 0, 0, false, true, true).color == Color::Green);
  assert(Motion(0, 0, false, false, false, false, true).reason == Reason::Locked);
  assert(Motion(0, 0, true, false, true, true, true).reason == Reason::FpgaWaiting);
  assert(Motion(0, 0, true, true, false, true, true).reason == Reason::SafetyWaiting);
  assert(Motion(0, 0, true, true, true, true, true).color == Color::Green);
  for (unsigned bit = 0; bit < 16; ++bit) {
    const auto mask = uint16_t(1u << bit);
    assert(Motion(mask, 0, false, false, false, false, true).color == Color::Red);
    const auto state = Motion(0, mask, true, true, true, true, true);
    assert((state.color == Color::Red) == bool(mask & 0x88ff));
  }
  assert(Motion(0, 0, true, true, true, true, false).reason == Reason::InternalFault);
  OutputCache cache;
  State state{Color::Blue, Reason::Starting};
  assert(cache.Due(state, 0)); cache.Complete(state, true, 0);
  for (unsigned i = 0; i < 100000; ++i) {
    assert(!cache.Due({Color::Blue, Reason::WifiOffline}, i));
  }
  assert(cache.Writes() == 1);
  state = {Color::Green, Reason::Ready};
  assert(cache.Due(state, 100000)); cache.Complete(state, false, 100000);
  assert(!cache.Known() && cache.Errors() == 1);
  assert(!cache.Due(state, 1099999));
  assert(cache.Due(state, 1100000)); cache.Complete(state, true, 1100000);
  assert(cache.Known() && cache.Writes() == 2);
  state = {Color::Red, Reason::MotionFault};
  assert(cache.Due(state, 1100001)); cache.Complete(state, true, 1100001);
  assert(cache.Writes() == 3);
  std::puts("PASS status decision boundaries, fault priority, diagnostic masks, change-only writes and bounded retry");
}
