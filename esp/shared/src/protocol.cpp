#include "simple/protocol.hpp"
#include <algorithm>
#include <cstring>

namespace simple {
uint16_t crc16(const uint8_t* data,size_t size) {
    uint16_t crc=0xffff;
    for(size_t i=0;i<size;++i) {
        crc^=uint16_t(data[i])<<8;
        for(unsigned bit=0;bit<8;++bit) crc=uint16_t((crc&0x8000)?(crc<<1)^0x1021:crc<<1);
    }
    return crc;
}
size_t encode_uart(const Frame& f,uint8_t* out,size_t capacity) {
    const size_t total=size_t(f.size)+9;
    if(f.size>kMaxPayload || capacity<total) return 0;
    out[0]=0x53; out[1]=0x31; out[2]=kVersion; out[3]=uint8_t(f.type); out[4]=f.size;
    write16(out+5,f.seq);
    std::copy_n(f.payload.begin(),f.size,out+7);
    write16(out+7+f.size,crc16(out+2,5+f.size));
    return total;
}
bool UartParser::push(uint8_t b,Frame& out) {
    if(used_==0) { if(b==0x53) bytes_[used_++]=b; return false; }
    if(used_==1) { if(b==0x31) bytes_[used_++]=b; else used_=b==0x53?1:0; return false; }
    if(used_==bytes_.size()) { ++errors_;used_=0; }
    bytes_[used_++]=b;
    while(used_>=2) {
        const bool bad_magic=bytes_[0]!=0x53 || bytes_[1]!=0x31;
        const bool bad_header=(used_>=3 && bytes_[2]!=kVersion) || (used_>=5 && bytes_[4]>kMaxPayload);
        if(bad_magic || bad_header) {
            if(bad_header) ++errors_;
            std::memmove(bytes_.data(),bytes_.data()+1,--used_);continue;
        }
        if(used_<7) return false;
        const size_t total=size_t(bytes_[4])+9;
        if(used_<total) return false;
        if(read16(bytes_.data()+total-2)!=crc16(bytes_.data()+2,total-4)) {
            ++errors_;std::memmove(bytes_.data(),bytes_.data()+1,--used_);continue;
        }
        out.type=Type(bytes_[3]); out.size=bytes_[4]; out.seq=read16(bytes_.data()+5);
        std::copy_n(bytes_.begin()+7,out.size,out.payload.begin());
        used_-=total;std::memmove(bytes_.data(),bytes_.data()+total,used_);return true;
    }
    if(used_==1 && bytes_[0]!=0x53) used_=0;
    return false;
}
SpiBytes encode_spi_command(const SpiCommand& c) {
    SpiBytes b{}; b[0]=0x53; b[1]=0x31; b[2]=1;
    write16(b.data()+4,c.seq); write16(b.data()+6,uint16_t(c.left)); write16(b.data()+8,uint16_t(c.right));
    write16(b.data()+30,crc16(b.data(),30)); return b;
}
bool decode_spi_command(const SpiBytes& b,SpiCommand& out) {
    if(b[0]!=0x53 || b[1]!=0x31 || b[2]!=1 || b[3]!=0 || read16(b.data()+30)!=crc16(b.data(),30)) return false;
    for(size_t i=10;i<30;++i) if(b[i]) return false;
    SpiCommand c{read16(b.data()+4),int16_t(read16(b.data()+6)),int16_t(read16(b.data()+8))};
    if(c.left < -kDutyMax || c.left>kDutyMax || c.right < -kDutyMax || c.right>kDutyMax) return false;
    out=c; return true;
}
SpiBytes encode_spi_status(const SpiStatus& s) {
    SpiBytes b{}; b[0]=0x53; b[1]=0x52; b[2]=1; b[3]=s.flags;
    write16(b.data()+4,s.applied_seq);
    const uint32_t values[]={s.left_count,s.right_count,s.left_period_ticks,s.right_period_ticks,s.left_age_ticks,s.right_age_ticks};
    for(size_t i=0;i<6;++i) write32(b.data()+6+4*i,values[i]);
    write16(b.data()+30,crc16(b.data(),30)); return b;
}
bool decode_spi_status(const SpiBytes& b,SpiStatus& out) {
    if(b[0]!=0x53 || b[1]!=0x52 || b[2]!=1 || (b[3]&0xf8) || read16(b.data()+30)!=crc16(b.data(),30)) return false;
    out={b[3],read16(b.data()+4),read32(b.data()+6),read32(b.data()+10),read32(b.data()+14),read32(b.data()+18),read32(b.data()+22),read32(b.data()+26)};
    return true;
}
bool valid_action(Action a) { return uint8_t(a)<=uint8_t(Action::Right); }
Frame make_ai_move(uint16_t seq,const AiMove& m) {
    Frame f{Type::AiMove,seq,8,{}}; write32(f.payload.data(),m.generation);
    f.payload[4]=uint8_t(m.action); f.payload[5]=m.speed; write16(f.payload.data()+6,m.duration_ms); return f;
}
bool parse_ai_move(const Frame& f,AiMove& m) {
    if(f.type!=Type::AiMove || f.size!=8) return false;
    const auto* p=f.payload.data(); AiMove v{read32(p),Action(p[4]),p[5],read16(p+6)};
    if(!valid_action(v.action) || v.speed>100 || (v.duration_ms!=0 && (v.duration_ms<100 || v.duration_ms>3000))) return false;
    m=v; return true;
}
Frame make_brain_state(uint16_t seq,const BrainState& s) {
    Frame f{Type::BrainState,seq,40,{}};
    f.payload[0]=s.flags; f.payload[1]=s.wifi_result; f.payload[2]=uint8_t(s.rssi);
    std::copy(s.ipv4.begin(),s.ipv4.end(),f.payload.begin()+4);
    std::memcpy(f.payload.data()+8,s.ssid.data(),32); return f;
}
bool parse_brain_state(const Frame& f,BrainState& s) {
    if(f.type!=Type::BrainState || f.size!=40 || (f.payload[0]&0xf0) || f.payload[1]>3 || f.payload[3]!=0) return false;
    s.flags=f.payload[0]; s.wifi_result=f.payload[1]; s.rssi=int8_t(f.payload[2]);
    std::copy_n(f.payload.begin()+4,4,s.ipv4.begin()); std::memcpy(s.ssid.data(),f.payload.data()+8,32); return true;
}
Frame make_motion_state(uint16_t seq,const MotionState& s) {
    Frame f{Type::MotionState,seq,28,{}}; auto* p=f.payload.data();
    write32(p,s.generation); p[4]=uint8_t(s.mode); p[5]=uint8_t(s.action); p[6]=s.speed; p[7]=uint8_t(s.reason);
    write16(p+8,uint16_t(s.left)); write16(p+10,uint16_t(s.right)); p[12]=s.fpga_link?1:0;
    write32(p+16,s.left_count); write32(p+20,s.right_count); write16(p+24,s.applied_seq); return f;
}
bool parse_motion_state(const Frame& f,MotionState& s) {
    if(f.type!=Type::MotionState || f.size!=28) return false;
    const auto* p=f.payload.data();
    if(p[4]>1 || !valid_action(Action(p[5])) || p[6]>100 || p[12]>1 || p[13] || p[14] || p[15] || p[26] || p[27]) return false;
    s={read32(p),Mode(p[4]),Action(p[5]),p[6],Reason(p[7]),int16_t(read16(p+8)),int16_t(read16(p+10)),p[12]!=0,read32(p+16),read32(p+20),read16(p+24)};
    return true;
}
const char* action_name(Action a) {
    switch(a) { case Action::Forward:return "forward"; case Action::Backward:return "backward";
        case Action::Left:return "left"; case Action::Right:return "right"; default:return "neutral"; }
}
const char* reason_name(Reason r) {
    static constexpr const char* names[]={"boot","released","stop","mode_changed","manual_timeout","ai_complete","brain_lost","fpga_lost","takeover","internet_lost","wrong_mode","invalid","reversing","waking","active"};
    const auto i=uint8_t(r); return i<sizeof(names)/sizeof(names[0])?names[i]:"unknown";
}
} // namespace simple
