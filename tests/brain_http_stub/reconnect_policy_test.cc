#include <cassert>
#include <iostream>
#include <vector>

#include "network_policy.h"
using namespace awcar;
struct SavedWifi {
  struct Entry { std::string ssid, password; };
  std::vector<Entry> list, persisted;
  int promotions = 0;
  const std::vector<Entry>& GetSsidList() const { return list; }
  void AddSsid(const std::string& ssid, const std::string& password) {
    for (auto& item : list) {
      if (item.ssid == ssid) { item.password = password; persisted = list; return; }
    }
    list.insert(list.begin(), {ssid, password}); persisted = list;
  }
  void SetDefaultSsid(int index) {
    const auto entry = list.at(index);
    list.erase(list.begin() + index); list.insert(list.begin(), entry);
    persisted = list; ++promotions;
  }
};
int main() {
  SavedWifi saved;
  saved.list = {{"previous", "test-a"}, {"selected", "test-old"}};
  saved.AddSsid("selected", "test-new");
  assert(saved.persisted.front().ssid == "previous");  // Old SDK behavior.
  RememberSelectedWifi(saved, "selected", "test-new");
  SavedWifi rebooted;
  rebooted.list = saved.persisted;
  assert(rebooted.list.front().ssid == "selected");
  assert(rebooted.list.front().password == "test-new");
  assert(rebooted.list[1].ssid == "previous" && rebooted.list[1].password == "test-a");
  assert(saved.promotions == 1);
  RememberSelectedWifi(saved, "selected", "test-next");
  assert(saved.promotions == 1 && saved.persisted.front().password == "test-next");
  RememberSelectedWifi(saved, "new-network", "test-only");
  assert(saved.promotions == 1 && saved.persisted.front().ssid == "new-network");
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
