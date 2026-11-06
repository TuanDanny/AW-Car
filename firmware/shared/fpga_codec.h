#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

namespace awcar::fpga {
enum Type : uint8_t {
  Hello = 1,
  ArmZero = 2,
  Command = 3,
  Disable = 4,
  Clear = 5,
  Status = 0x80
};
struct Frame {
  uint8_t type = 0, length = 0;
  uint32_t session = 0;
  uint16_t seq = 0;
  std::array<uint8_t, 34> payload{};
};
struct Snapshot {
  uint32_t session = 0, left_count = 0, right_count = 0, timestamp = 0;
  uint16_t seq = 0, fault = 0;
  uint8_t state = 0, encoder = 0;
  uint32_t left_period = 0, right_period = 0;
  uint32_t left_age = UINT32_MAX, right_age = UINT32_MAX;
};
size_t Encode(const Frame& frame, uint8_t* out, size_t capacity);
bool DecodeStatus(const Frame& frame, Snapshot& out);
Frame CommandFrame(uint32_t session, uint16_t seq, uint8_t direction,
                   uint16_t left, uint16_t right);
class Parser {
 public:
  enum class ErrorReason : uint8_t { None, Timeout, Header, Crc };
  struct Diagnostics {
    uint32_t timeout_errors = 0, header_errors = 0, crc_errors = 0;
    uint32_t last_gap_us = 0, last_frame_us = 0;
    uint8_t last_size = 0;
    ErrorReason last_reason = ErrorReason::None;
  };
  bool Feed(uint8_t byte, uint64_t now_us, Frame& out);
  void Reset() { size_ = 0; }
  const Diagnostics& GetDiagnostics() const { return diagnostics_; }
  uint32_t errors = 0;

 private:
  std::array<uint8_t, 64> bytes_{};
  size_t size_ = 0;
  uint64_t start_ = 0, last_ = 0;
  Diagnostics diagnostics_{};
  void Reject(ErrorReason reason, uint64_t now, uint64_t gap);
};
}  // namespace awcar::fpga
