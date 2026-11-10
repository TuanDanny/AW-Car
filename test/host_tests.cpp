#include "simple/control.hpp"
#include "simple/pid.hpp"
#include "simple/network_policy.hpp"
#include "simple/log_ring.hpp"
#include "../esp/motion/main/network_activity.hpp"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <random>

namespace {
unsigned assertions=0;
void check(bool value,const char* condition,int line) {
    ++assertions;if(!value) { std::fprintf(stderr,"FAIL line=%d %s\n",line,condition);std::exit(1); }
}
#define CHECK(x) check(bool(x),#x,__LINE__)
void links(simple::Control& c,uint64_t now) {
    c.fpga({},now);simple::BrainState brain{};brain.flags=3;c.brain(brain,now);
}
void codec() {
    const auto* sample=reinterpret_cast<const uint8_t*>("123456789");
    CHECK(simple::crc16(sample,9)==0x29b1);
    std::mt19937 random(731);
    for(unsigned i=0;i<12000;++i) {
        const simple::SpiCommand sent{uint16_t(random()),int16_t(int(random()%2701)-1350),int16_t(int(random()%2701)-1350)};
        auto bytes=simple::encode_spi_command(sent);simple::SpiCommand got{};
        CHECK(simple::decode_spi_command(bytes,got));CHECK(got.seq==sent.seq && got.left==sent.left && got.right==sent.right);
        bytes[random()%32]^=uint8_t(1U<<(random()%8));CHECK(!simple::decode_spi_command(bytes,got));
    }
    simple::SpiStatus s{7,65535,0xffffffff,12345,1350,2700,42,0xffffffff},decoded{};
    auto bytes=simple::encode_spi_status(s);CHECK(simple::decode_spi_status(bytes,decoded));
    CHECK(decoded.right_age_ticks==0xffffffff && decoded.left_count==0xffffffff && decoded.left_period_ticks==1350);
    bytes[3]|=0x80;simple::write16(bytes.data()+30,simple::crc16(bytes.data(),30));CHECK(!simple::decode_spi_status(bytes,decoded));
    simple::SpiCommand invalid{};
    for(int duty:{-1351,1351,-32768,32767}) CHECK(!simple::decode_spi_command(simple::encode_spi_command({4,int16_t(duty),0}),invalid));
    std::array<uint8_t,simple::kMaxFrame> out{};simple::UartParser parser;simple::Frame received{};
    for(unsigned i=0;i<1024;++i) {
        simple::Frame f{simple::Type::WifiConfig,uint16_t(i),uint8_t(random()%129),{}};
        for(auto& b:f.payload) b=uint8_t(random());
        const auto length=simple::encode_uart(f,out.data(),out.size());CHECK(length==size_t(f.size)+9);
        unsigned messages=0;
        for(size_t j=0;j<length;++j) if(parser.push(out[j],received)) ++messages;
        CHECK(messages==1 && received.seq==f.seq && received.size==f.size);
        CHECK(std::memcmp(received.payload.data(),f.payload.data(),f.size)==0);
    }
    auto f=simple::make_ai_move(65535,{0x12345678,simple::Action::Left,30,3000});
    const auto n=simple::encode_uart(f,out.data(),out.size());
    out[n-1]^=1;for(size_t j=0;j<n;++j) CHECK(!parser.push(out[j],received));
    out[n-1]^=1;unsigned accepted=0;
    for(size_t j=0;j<n;++j) accepted+=parser.push(out[j],received)?1:0;
    CHECK(accepted==1 && parser.errors()>0);simple::AiMove ai{};CHECK(simple::parse_ai_move(received,ai));
    CHECK(ai.duration_ms==3000 && ai.generation==0x12345678);
    // Truncated big frame followed by good frames: bounded memory and recovery.
    parser.reset();const uint8_t fragment[]={0x53,0x31,1,0x01,128,0,0,9};
    for(auto b:fragment) parser.push(b,received);
    accepted=0;for(unsigned repeat=0;repeat<24;++repeat) for(size_t j=0;j<n;++j) accepted+=parser.push(out[j],received)?1:0;
    CHECK(accepted>10);
    f=simple::make_ai_move(1,{1,simple::Action::Forward,101,1000});CHECK(!simple::parse_ai_move(f,ai));
    for(auto duration:{1,99,3001,65535}) { f=simple::make_ai_move(1,{1,simple::Action::Forward,30,uint16_t(duration)});CHECK(!simple::parse_ai_move(f,ai)); }
    simple::BrainState b{};b.flags=15;b.ssid[31]='X';b.ipv4={192,168,100,2};b.rssi=-45;
    simple::BrainState b2{};CHECK(simple::parse_brain_state(simple::make_brain_state(3,b),b2));CHECK(b2.rssi==-45 && b2.ssid[31]=='X');
    simple::MotionState m{44,simple::Mode::Ai,simple::Action::Right,100,simple::Reason::Active,1350,-1350,true,9,10,65535},m2{};
    CHECK(simple::parse_motion_state(simple::make_motion_state(1,m),m2));CHECK(m2.right==-1350 && m2.generation==44 && m2.mode==simple::Mode::Ai);
}
void control() {
    using namespace simple;
    Control c(91);CHECK(c.state().mode==Mode::Manual && c.state().left==0 && !c.driver_enabled());
    CHECK(!c.manual(Action::Forward,30,0));links(c,100);
    CHECK(c.manual(Action::Forward,30,100));c.tick(100);CHECK(c.driver_enabled() && c.state().left==0);
    c.tick(101);CHECK(c.state().left==405 && c.state().right==405);
    links(c,599);c.tick(599);CHECK(c.state().left==405);c.tick(600);CHECK(c.state().left==0 && c.state().reason==Reason::ManualTimeout);
    CHECK(c.manual(Action::Backward,100,601));c.tick(601);CHECK(c.state().left==0);
    c.tick(638);CHECK(c.state().left==0);c.tick(639);CHECK(c.state().left==0);c.tick(640);CHECK(c.state().left==-1350);
    CHECK(c.manual(Action::Left,30,650));c.tick(650);CHECK(c.state().left==0 && c.state().right==0);
    links(c,700);c.tick(700);c.tick(701);CHECK(c.state().left==-405 && c.state().right==405);
    const auto old=c.state().generation;c.stop();CHECK(c.state().generation!=old && c.state().mode==Mode::Manual && c.state().left==0);
    c.set_mode(Mode::Ai);links(c,800);const auto epoch=c.state().generation;
    CHECK(!c.manual(Action::Forward,30,800));CHECK(!c.ai({old,Action::Forward,30,1000},800));
    CHECK(c.ai({epoch,Action::Forward,30,1000},800));c.tick(800);c.tick(801);CHECK(c.state().left==405);
    links(c,1290);c.tick(1290);links(c,1780);c.tick(1799);CHECK(c.state().left==405);
    c.tick(1800);CHECK(c.state().left==0 && c.state().mode==Mode::Ai && c.state().reason==Reason::AiComplete);
    links(c,1900);CHECK(c.ai({epoch,Action::Forward,50,3000},1900));c.tick(1900);c.tick(1901);
    CHECK(c.ai({epoch,Action::Right,30,100},1950));c.tick(1950);links(c,2000);c.tick(2000);c.tick(2001);
    CHECK(c.state().left==405 && c.state().right==-405);c.tick(2050);CHECK(c.state().left==0);
    CHECK(c.ai({epoch,Action::Forward,30,1000},2100));c.disconnect();CHECK(c.state().mode==Mode::Ai); // Web loss independent of AI.
    links(c,2100);c.tick(2100);c.tick(2101);CHECK(c.state().left==405);
    c.fpga({},2602);c.tick(2602);CHECK(c.state().reason==Reason::BrainLost && c.state().mode==Mode::Manual && !c.driver_enabled());
    links(c,2700);CHECK(c.manual(Action::Forward,30,2700));c.tick(2700);c.tick(2701);c.disconnect();CHECK(c.state().left==0 && c.state().mode==Mode::Manual);
    CHECK(c.manual(Action::Forward,30,2800));c.tick(2800);c.tick(2801);c.tick(3301);CHECK(c.state().reason==Reason::FpgaLost);
    links(c,3400);c.tick(3400);CHECK(c.state().left==0); // no replay after SPI recovery
    CHECK(c.manual(Action::Right,0,3401));c.tick(3401);CHECK(c.state().left==0 && !c.driver_enabled());
    c.set_mode(Mode::Ai);links(c,3500);CHECK(c.ai({c.state().generation,Action::Forward,30,1000},3500));
    BrainState offline{};c.brain(offline,3501);c.tick(3501);CHECK(c.state().reason==Reason::InternetLost && c.state().mode==Mode::Manual);
    c.takeover();CHECK(c.state().reason==Reason::Takeover && c.state().left==0);
    CHECK(!c.manual(Action(99),30,3502));CHECK(!c.manual(Action::Forward,101,3502));
    // Manual remains independent of absent Brain/Internet.
    c.fpga({},10000);CHECK(c.manual(Action::Forward,30,10000));c.tick(10000);c.tick(10001);CHECK(c.state().left==405);
    for(auto a:{Action::Forward,Action::Backward,Action::Left,Action::Right}) for(auto speed:{0,30,100}) {
        Control isolated(1);links(isolated,1);CHECK(isolated.manual(a,uint8_t(speed),1));isolated.tick(1);isolated.tick(2);
        const int magnitude=(speed*1350+50)/100;CHECK(std::abs(isolated.state().left)==magnitude && std::abs(isolated.state().right)==magnitude);
    }
}
void pid() {
    simple::Pid p;p.kp=2;p.ki=3;p.kd=.1f;p.high=100;p.integral_high=20;
    for(unsigned i=0;i<10000;++i) { const float out=p.update(1000,0);CHECK(std::isfinite(out) && out>=0 && out<=100 && p.integral<=20); }
    p.reset();CHECK(p.integral==0 && p.previous_error==0 && p.derivative==0);
    p.dt=0;CHECK(p.update(10,0)==0);
}
void ai_default_duration() {
    using namespace simple;
    CHECK(AiMove{}.duration_ms==3000);
    for(auto duration:{uint16_t(0),kAiDefaultDurationMs,uint16_t(1000)}) {
        Control c(42);c.set_mode(Mode::Ai);links(c,100);
        CHECK(c.ai({c.state().generation,Action::Forward,30,duration},100));
        const uint64_t deadline=100+(duration?duration:kAiDefaultDurationMs);
        for(uint64_t now=100;now<deadline;now+=100) { links(c,now);c.tick(now); }
        links(c,deadline-1);c.tick(deadline-1);CHECK(c.state().left==405);
        c.tick(deadline);CHECK(c.state().left==0 && c.state().reason==Reason::AiComplete);
    }
}
void maintenance() {
    using namespace simple;
    Control c(20);links(c,1);CHECK(c.manual(Action::Forward,100,1));c.tick(1);c.tick(2);
    CHECK(c.driver_enabled() && c.state().left==1350);
    c.set_mode(Mode::Ai);const auto old=c.state().generation;
    CHECK(c.ai({old,Action::Forward,100,3000},3));c.tick(3);c.tick(4);
    c.maintenance(true);CHECK(c.maintaining() && !c.driver_enabled() && c.state().left==0);
    CHECK(c.state().mode==Mode::Manual && c.state().reason==Reason::Maintenance);
    const auto entered=c.state().generation;c.maintenance(true);CHECK(c.state().generation==entered);
    for(unsigned n=0;n<1000;++n) {
        links(c,5+n);c.set_mode(Mode::Ai);
        CHECK(!c.manual(Action::Forward,100,5+n));
        CHECK(!c.ai({c.state().generation,Action::Backward,100,3000},5+n));
        c.tick(5+n);CHECK(!c.driver_enabled() && !c.state().left && !c.state().right);
    }
    c.stop();CHECK(c.maintaining() && c.state().reason==Reason::Maintenance);
    c.maintenance(false);c.tick(1005);
    CHECK(!c.maintaining() && !c.driver_enabled() && !c.state().left && c.state().mode==Mode::Manual);
    CHECK(!c.ai({old,Action::Forward,100,1000},1005)); // Old AI cannot survive update/failure.
    c.set_mode(Mode::Ai);CHECK(!c.ai({old,Action::Forward,100,1000},1005));
    c.set_mode(Mode::Manual);CHECK(c.manual(Action::Forward,30,1005));c.tick(1005);c.tick(1006);
    CHECK(c.state().left==405); // Only a fresh explicit command may move again.
}
void network_policy() {
    using P=simple::NetworkPolicy;using A=P::Action;
    P p;CHECK(p.step(0,false)==A::None);
    p.configure(0);CHECK(p.step(499,false)==A::None);CHECK(p.step(500,false)==A::Connect);
    CHECK(p.step(1000,false)==A::None); // Do not restart a DHCP/connection attempt.
    CHECK(p.step(15500,false)==A::Cancel);CHECK(p.failures()==1);
    p.disconnected(15501);CHECK(p.failures()==1); // Duplicate event does not postpone forever.
    CHECK(p.step(16499,false)==A::None);CHECK(p.step(16500,false)==A::Connect);
    p.got_ip();CHECK(p.online() && p.failures()==0);CHECK(p.step(50000,true)==A::None);
    p.disconnected(50000);CHECK(p.step(51000,true)==A::None);
    CHECK(p.step(52999,false)==A::None);CHECK(p.step(53000,false)==A::Connect);
    CHECK(p.step(53001,true)==A::Cancel); // Cancel off-channel attempts if driving starts.
    CHECK(p.step(55000,false)==A::None);CHECK(p.step(55001,false)==A::Connect);
    p.configure(60000);uint64_t now=60500;
    for(unsigned n=0;n<12;++n) {
        CHECK(p.step(now,false)==A::Connect);p.disconnected(now);
        const auto wait=p.retry_ms(now);CHECK(wait>=1000 && wait<=60000);
        if(n>=5) CHECK(wait==60000);
        CHECK(p.step(now+wait-1,false)==A::None);now+=wait;
    }
    CHECK(simple::on_interface(0x0104a8c0,0x0104a8c0));
    CHECK(!simple::on_interface(0,0));CHECK(!simple::on_interface(0x6401a8c0,0x0104a8c0));
    uint8_t ap[4]={192,168,4,1},sta[4]={192,168,0,10};uint32_t a{},s{},got{};
    CHECK(simple::ipv4_destination(ap,4,a));CHECK(simple::ipv4_destination(sta,4,s));
    uint8_t mapped[16]={0};mapped[10]=mapped[11]=0xff;std::memcpy(mapped+12,ap,4);
    CHECK(simple::ipv4_destination(mapped,16,got) && simple::on_interface(got,a));
    std::memcpy(mapped+12,sta,4);
    CHECK(simple::ipv4_destination(mapped,16,got) && !simple::on_interface(got,a));
    mapped[0]=0x20;CHECK(!simple::ipv4_destination(mapped,16,got)); // Real IPv6 is not an AP IPv4 match.
    mapped[0]=0;mapped[10]=0;CHECK(!simple::ipv4_destination(mapped,16,got));
    for(size_t size:{0U,1U,3U,5U,15U}) CHECK(!simple::ipv4_destination(mapped,size,got));

    // Use the same predicate as Runtime, with actual zero-output transition states.
    simple::Control c(400);links(c,500);
    CHECK(c.manual(simple::Action::Forward,30,500));c.tick(500);
    CHECK(c.state().reason==simple::Reason::Waking && !c.state().left && !c.state().right);
    CHECK(motion::network_motion_busy(c.state(),false,false));
    P waking;waking.configure(0);
    CHECK(waking.step(500,motion::network_motion_busy(c.state(),false,false))==A::None);
    P connecting;connecting.configure(0);CHECK(connecting.step(500,false)==A::Connect);
    CHECK(connecting.step(501,motion::network_motion_busy(c.state(),false,false))==A::Cancel);
    c.tick(501);CHECK(c.state().left==405);
    CHECK(c.manual(simple::Action::Backward,30,502));c.tick(502);
    CHECK(c.state().reason==simple::Reason::Reversing && !c.state().left && !c.state().right);
    P reversing;reversing.configure(0);
    CHECK(reversing.step(502,motion::network_motion_busy(c.state(),false,false))==A::None);
    P online;online.configure(0);CHECK(online.step(500,false)==A::Connect);online.got_ip();
    CHECK(online.step(502,motion::network_motion_busy(c.state(),false,false))==A::None && online.online());
    c.stop();CHECK(!motion::network_motion_busy(c.state(),false,false));
    CHECK(motion::network_motion_busy(c.state(),true,false));
    CHECK(motion::network_motion_busy(c.state(),false,true));
    c.maintenance(true);CHECK(motion::network_motion_busy(c.state(),false,true));
    P idle;idle.configure(0);CHECK(idle.step(500,motion::network_motion_busy(c.state(),false,false))==A::Connect);
    auto inconsistent=c.state();inconsistent.left=1;
    CHECK(motion::network_motion_busy(inconsistent,false,false));
}
void log_ring() {
    simple::LogRing<4> ring;simple::LogRing<4>::Record records[3];
    auto batch=ring.read(0,records,3);CHECK(batch.count==0 && batch.next==0);
    for(uint64_t i=1;i<=20;++i) ring.append(i*500,"sample");
    batch=ring.read(0,records,3);CHECK(batch.count==3 && batch.dropped==16 && batch.next==19);
    CHECK(records[0].seq==17 && records[0].ms==8500 && std::strcmp(records[0].text,"sample")==0);
    batch=ring.read(batch.next,records,3);CHECK(batch.count==1 && batch.next==20 && batch.dropped==0);
    CHECK(ring.read(20,records,3).count==0);CHECK(ring.read(UINT64_MAX,records,3).count==0);
    char large[1000];std::memset(large,'x',sizeof(large));large[999]=0;ring.append(1,large);
    batch=ring.read(20,records,3);CHECK(batch.count==1 && std::strlen(records[0].text)==255);
}
}
int main() { codec();control();pid();ai_default_duration();maintenance();network_policy();log_ring();std::printf("PASS native assertions=%u seed=731 SPI_random=12000 UART_frames=1024 PID=disabled_on_firmware\n",assertions); }
