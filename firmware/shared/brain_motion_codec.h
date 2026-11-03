#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

namespace awcar::bm {
enum Type : uint8_t {
  Hello = 1,
  Arm = 2,
  Twist = 3,
  Stop = 4,
  Clear = 5,
  Status = 0x80
};
struct Frame {
  uint8_t type = 0, length = 0;
  uint32_t session = 0;
  uint16_t seq = 0;
  std::array<uint8_t, 17> payload{};
};
inline uint16_t U16(const uint8_t* p) {
  return uint16_t(p[0]) | uint16_t(p[1]) << 8;
}
inline uint32_t U32(const uint8_t* p) {
  return uint32_t(U16(p)) | uint32_t(U16(p + 2)) << 16;
}
inline void Put16(uint8_t* p, uint16_t v) {
  p[0] = uint8_t(v);
  p[1] = uint8_t(v >> 8);
}
inline void Put32(uint8_t* p, uint32_t v) {
  Put16(p, uint16_t(v));
  Put16(p + 2, uint16_t(v >> 16));
}
uint16_t Crc(const uint8_t* p, size_t n);
size_t Encode(const Frame& f, uint8_t* out, size_t capacity);
class Parser {
 public:
  bool Feed(uint8_t byte, uint64_t now_us, Frame& out);
  void Reset() { size_ = 0; }
  uint32_t errors = 0;

 private:
  std::array<uint8_t, 32> bytes_{};
  size_t size_ = 0;
  uint64_t start_ = 0, last_ = 0;
};
}  // namespace awcar::bm
