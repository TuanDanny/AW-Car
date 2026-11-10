#include "simple/control.hpp"
#include <cstdio>

#ifdef _WIN32
#define API extern "C" __declspec(dllexport)
#else
#define API extern "C"
#endif
API void* car_create(unsigned generation) { return new simple::Control(generation); }
API void car_destroy(void* p) { delete static_cast<simple::Control*>(p); }
API void codec_spi_encode(unsigned seq,int left,int right,unsigned char* out) {
    const auto bytes=simple::encode_spi_command({uint16_t(seq),int16_t(left),int16_t(right)});
    for(unsigned i=0;i<32;++i) out[i]=bytes[i];
}
API int codec_spi_status(const unsigned char* in,unsigned* out) {
    simple::SpiBytes bytes{};for(unsigned i=0;i<32;++i) bytes[i]=in[i];
    simple::SpiStatus s{};if(!simple::decode_spi_status(bytes,s)) return 0;
    out[0]=s.flags;out[1]=s.applied_seq;out[2]=s.left_count;out[3]=s.right_count;
    out[4]=s.left_period_ticks;out[5]=s.right_period_ticks;out[6]=s.left_age_ticks;out[7]=s.right_age_ticks;return 1;
}
API int car_event(void* p,unsigned event,unsigned a,unsigned b,unsigned duration,unsigned generation,unsigned long long now) {
    auto& c=*static_cast<simple::Control*>(p);
    switch(event) {
        case 0:c.tick(now);return 1;
        case 1:return c.manual(simple::Action(a),uint8_t(b),now);
        case 2:c.set_mode(simple::Mode(a));return 1;
        case 3:c.stop(simple::Reason(a));return 1;
        case 4:c.disconnect();return 1;
        case 5:{simple::BrainState s{};s.flags=uint8_t(a);c.brain(s,now);return 1;}
        case 6:{simple::SpiStatus s{};s.left_count=a;s.right_count=b;c.fpga(s,now);return 1;}
        case 7:return c.ai({generation,simple::Action(a),uint8_t(b),uint16_t(duration)},now);
        default:return 0;
    }
}
API int car_state(void* p,char* out,unsigned capacity,unsigned long long now) {
    auto& c=*static_cast<simple::Control*>(p);const auto s=c.state();
    return std::snprintf(out,capacity,"{\"mode\":\"%s\",\"generation\":%u,\"action\":\"%s\",\"speed\":%u,\"left\":%d,\"right\":%d,\"reason\":\"%s\",\"fpga_connected\":%s,\"brain_connected\":%s,\"driver\":%s,\"left_count\":%u,\"right_count\":%u}",
        s.mode==simple::Mode::Manual?"manual":"ai",s.generation,simple::action_name(s.action),s.speed,s.left,s.right,simple::reason_name(s.reason),c.fpga_connected(now)?"true":"false",c.brain_connected(now)?"true":"false",c.driver_enabled()?"true":"false",s.left_count,s.right_count);
}
