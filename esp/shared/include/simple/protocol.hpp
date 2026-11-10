#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

namespace simple {
constexpr uint8_t kVersion = 1;
constexpr size_t kSpiBytes = 32, kMaxPayload = 128, kMaxFrame = kMaxPayload + 9;
constexpr int16_t kDutyMax = 1350;
constexpr uint32_t kClockHz = 27000000;
enum class Mode : uint8_t { Manual = 0, Ai = 1 };
enum class Action : uint8_t { Neutral, Forward, Backward, Left, Right };
enum class Reason : uint8_t {
    Boot, Released, Stop, ModeChanged, ManualTimeout, AiComplete,
    BrainLost, FpgaLost, Takeover, InternetLost, WrongMode, Invalid, Reversing, Waking, Active, Maintenance
};
enum class Type : uint8_t {
    BrainState = 0x01, AiMove = 0x02, Stop = 0x03,
    MotionState = 0x81, Listen = 0x82, WifiConfig = 0x83
};
constexpr uint8_t kWifiReady = 1, kCloudReady = 2, kListening = 4, kSpeaking = 8;
constexpr uint16_t read16(const uint8_t* p) { return uint16_t(p[0]) | (uint16_t(p[1]) << 8); }
constexpr uint32_t read32(const uint8_t* p) { return uint32_t(read16(p)) | (uint32_t(read16(p+2)) << 16); }
inline void write16(uint8_t* p, uint16_t v) { p[0]=uint8_t(v); p[1]=uint8_t(v>>8); }
inline void write32(uint8_t* p, uint32_t v) { write16(p,uint16_t(v)); write16(p+2,uint16_t(v>>16)); }
uint16_t crc16(const uint8_t* data, size_t size);

struct Frame {
    Type type{};
    uint16_t seq{};
    uint8_t size{};
    std::array<uint8_t,kMaxPayload> payload{};
};
size_t encode_uart(const Frame& frame, uint8_t* out, size_t capacity);
class UartParser {
public:
    bool push(uint8_t byte, Frame& out);
    void reset() { used_=0; }
    uint32_t errors() const { return errors_; }
private:
    std::array<uint8_t,kMaxFrame> bytes_{};
    size_t used_{};
    uint32_t errors_{};
};
struct SpiCommand { uint16_t seq{}; int16_t left{}, right{}; };
struct SpiStatus {
    uint8_t flags{};
    uint16_t applied_seq{};
    uint32_t left_count{}, right_count{}, left_period_ticks{}, right_period_ticks{}, left_age_ticks{}, right_age_ticks{};
};
using SpiBytes = std::array<uint8_t,kSpiBytes>;
SpiBytes encode_spi_command(const SpiCommand& command);
bool decode_spi_command(const SpiBytes& bytes, SpiCommand& out);
SpiBytes encode_spi_status(const SpiStatus& status);
bool decode_spi_status(const SpiBytes& bytes, SpiStatus& out);

struct AiMove { uint32_t generation{}; Action action{Action::Neutral}; uint8_t speed{30}; uint16_t duration_ms{1000}; };
struct BrainState {
    uint8_t flags{}, wifi_result{};
    int8_t rssi{};
    std::array<uint8_t,4> ipv4{};
    std::array<char,32> ssid{};
};
struct MotionState {
    uint32_t generation{};
    Mode mode{Mode::Manual};
    Action action{Action::Neutral};
    uint8_t speed{};
    Reason reason{Reason::Boot};
    int16_t left{}, right{};
    bool fpga_link{};
    uint32_t left_count{}, right_count{};
    uint16_t applied_seq{};
};
Frame make_ai_move(uint16_t seq, const AiMove& move);
bool parse_ai_move(const Frame& frame, AiMove& move);
Frame make_brain_state(uint16_t seq, const BrainState& state);
bool parse_brain_state(const Frame& frame, BrainState& state);
Frame make_motion_state(uint16_t seq, const MotionState& state);
bool parse_motion_state(const Frame& frame, MotionState& state);
bool valid_action(Action action);
const char* action_name(Action action);
const char* reason_name(Reason reason);
} // namespace simple
