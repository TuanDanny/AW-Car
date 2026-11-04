#include <cassert>
#include <iostream>

#include "network_policy.h"
using namespace awcar;
int main() {
  ReconnectPolicy none;
  none.Configure(false, 0);
  assert(!none.StartDue(1000000) && none.attempts == 0);
  ReconnectPolicy absent;
  absent.Configure(true, 0);
  for (uint64_t now = 0; now < 600000; now += 100)
    if (absent.StartDue(now)) absent.Failed(StaFailure::MissingAp, now);
  assert(absent.attempts <= 30 && absent.attempts > 3);
  ReconnectPolicy active;
  active.Configure(true, 0);
  assert(active.StartDue(0, true));
  active.Failed(StaFailure::MissingAp, 100);
  assert(!active.StartDue(1000, true) && !active.StartDue(59999, true));
  assert(active.StartDue(60000, true));
  active.Configure(true, 60001);
  assert(active.StartDue(60001, true));
  ReconnectPolicy bad;
  bad.Configure(true, 0);
  assert(bad.StartDue(0));
  bad.Failed(StaFailure::Authentication, 1);
  assert(!bad.StartDue(300000));
  assert(bad.StartDue(300001));
  ReconnectPolicy pending;
  pending.Configure(true, 0);
  assert(pending.StartDue(0));
  assert(!pending.StartDue(3000) && pending.TimedOut(15000));
  pending.Associated(14000);
  assert(!pending.TimedOut(15000) && pending.TimedOut(29000));
  assert(pending.GotIp(28000));
  for (uint64_t now = 28000; now < 1800000; now += 100)
    assert(!pending.StartDue(now));
  ReconnectPolicy flap;
  flap.Configure(true, 0);
  for (int i = 0; i < 3; ++i) {
    assert(flap.StartDue(flap.due));
    auto t = flap.due;
    flap.GotIp(t);
    flap.Failed(StaFailure::Transient, t + 1);
  }
  assert(flap.phase == StaPhase::Cooldown);
  assert(flap.StartDue(flap.due));
  auto t = flap.due;
  flap.GotIp(t);
  flap.Failed(StaFailure::Transient, t + 30001);
  assert(flap.burst == 1 && flap.phase == StaPhase::Backoff);
  std::cout << "PASS bounded_scan_auth_dhcp_flap_and_cloud_independence\n";
}
