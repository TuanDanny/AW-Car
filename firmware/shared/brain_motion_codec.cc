#include "brain_motion_codec.h"

#include <algorithm>
namespace awcar::bm {
static int Length(uint8_t t) {
  return t == Twist                   ? 7
         : t == Status                ? 17
         : (t >= Hello && t <= Clear) ? 0
                                      : -1;
}
uint16_t Crc(const uint8_t* p, size_t n) {
  uint16_t c = 0xffff;
  while (n--) {
    c ^= uint16_t(*p++) << 8;
    for (int i = 0; i < 8; i++)
      c = uint16_t((c << 1) ^ ((c & 0x8000) ? 0x1021 : 0));
  }
  return c;
}
size_t Encode(const Frame& f, uint8_t* out, size_t capacity) {
  size_t n = 13 + f.length;
  if (Length(f.type) != f.length || capacity < n) return 0;
  out[0] = 0xa5;
  out[1] = 0x5a;
  out[2] = 1;
  out[3] = f.type;
  out[4] = f.length;
  Put32(out + 5, f.session);
  Put16(out + 9, f.seq);
  std::copy_n(f.payload.begin(), f.length, out + 11);
  Put16(out + 11 + f.length, Crc(out + 2, 9 + f.length));
  return n;
}
bool Parser::Feed(uint8_t b, uint64_t now, Frame& out) {
  if (size_ && (now - last_ >= 10000 || now - start_ >= 30000)) {
    ++errors;
    size_ = 0;
  }
  last_ = now;
  if (!size_) {
    if (b == 0xa5) {
      bytes_[size_++] = b;
      start_ = now;
    }
    return false;
  }
  if (size_ == 1 && b != 0x5a) {
    size_ = b == 0xa5 ? 1 : 0;
    start_ = now;
    return false;
  }
  bytes_[size_++] = b;
  bool bad = (size_ == 3 && b != 1) || (size_ == 4 && Length(b) < 0) ||
             (size_ == 5 && b != Length(bytes_[3]));
  if (bad) {
    ++errors;
    size_ = b == 0xa5 ? 1 : 0;
    start_ = now;
    return false;
  }
  if (size_ < 5 || size_ < size_t(13 + bytes_[4])) return false;
  size_t n = size_;
  size_ = 0;
  if (Crc(bytes_.data() + 2, n - 4) != U16(bytes_.data() + n - 2)) {
    ++errors;
    if (b == 0xa5) {
      bytes_[0] = b;
      size_ = 1;
      start_ = now;
    }
    return false;
  }
  out = {};
  out.type = bytes_[3];
  out.length = bytes_[4];
  out.session = U32(bytes_.data() + 5);
  out.seq = U16(bytes_.data() + 9);
  std::copy_n(bytes_.data() + 11, out.length, out.payload.begin());
  return true;
}
}  // namespace awcar::bm
