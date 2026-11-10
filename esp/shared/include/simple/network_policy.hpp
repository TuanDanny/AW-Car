#pragma once
#include <algorithm>
#include <cstdint>
#include <cstddef>
#include <cstring>

namespace simple {
// All calls belong to the network task. Time is monotonic/injectable on host.
class NetworkPolicy {
public:
    enum class Action { None, Connect, Cancel };
    void configure(uint64_t now) { configured_=true;online_=false;connecting_=false;failures_=0;next_=now+500; }
    void got_ip() { online_=true;connecting_=false;failures_=0; }
    void disconnected(uint64_t now) {
        if(!online_ && !connecting_) return; // Ignore duplicate disconnect notifications.
        online_=false;connecting_=false;
        const auto delay=failures_>=5?60000U:std::min(1000U<<failures_,30000U);
        ++failures_;next_=now+delay;
    }
    Action step(uint64_t now,bool active) {
        if(active) quiet_until_=now+2000;
        if(connecting_ && (active || now>=deadline_)) {
            disconnected(now);return Action::Cancel;
        }
        if(!configured_ || online_ || connecting_ || active || now<quiet_until_ || now<next_) return Action::None;
        connecting_=true;deadline_=now+15000;return Action::Connect;
    }
    bool online() const { return online_; }
    bool connecting() const { return connecting_; }
    uint32_t failures() const { return failures_; }
    uint32_t retry_ms(uint64_t now) const { return !configured_ || online_ || connecting_ || now>=next_?0:uint32_t(next_-now); }
private:
    bool configured_{},online_{},connecting_{};
    uint32_t failures_{};
    uint64_t next_{},deadline_{},quiet_until_{};
};
// Local destination address is authoritative; never trust Host/Origin alone.
constexpr bool on_interface(uint32_t local,uint32_t interface_ip) { return interface_ip!=0 && local==interface_ip; }
inline bool ipv4_destination(const uint8_t* bytes,size_t size,uint32_t& address) {
    if(size==4) { std::memcpy(&address,bytes,4);return true; }
    if(size!=16) return false;
    for(size_t i=0;i<10;++i) if(bytes[i]!=0) return false;
    if(bytes[10]!=0xff || bytes[11]!=0xff) return false;
    std::memcpy(&address,bytes+12,4);return true;
}
}
