#include "fpga_codec.h"

#include <algorithm>

#include "brain_motion_codec.h"
namespace awcar::fpga {
static int Length(uint8_t type) {
  return type == Status                   ? 34
         : type == Command                ? 6
         : type >= Hello && type <= Clear ? 0
                                          : -1;
}
size_t Encode(const Frame& f, uint8_t* out, size_t capacity) {
  const size_t n = 13 + f.length;
  if (Length(f.type) != f.length || capacity < n) return 0;
  out[0] = 0xa5;
  out[1] = 0x5a;
  out[2] = 2;
  out[3] = f.type;
  out[4] = f.length;
  bm::Put32(out + 5, f.session);
  bm::Put16(out + 9, f.seq);
  std::copy_n(f.payload.begin(), f.length, out + 11);
  bm::Put16(out + n - 2, bm::Crc(out + 2, n - 4));
  return n;
}
bool DecodeStatus(const Frame& f, Snapshot& s) {
  if (f.type != Status || f.length != 34) return false;
  const auto* p = f.payload.data();
  if (bm::U16(p + 12) != f.seq || p[14] > 5 || !(p[17] & 0x10) ||
      (p[17] & 0x80))
    return false;
  // A period-valid flag requires an initialized decoder, an edge and a period.
  for (int side = 0; side < 2; ++side) {
    if ((p[17] & (1u << side)) &&
        (!(p[17] & (1u << (side + 2))) || !(p[17] & (1u << (side + 5))) ||
         !bm::U32(p + 18 + side * 4) ||
         bm::U32(p + 26 + side * 4) == UINT32_MAX))
      return false;
  }
  s.session = f.session;
  s.seq = f.seq;
  s.left_count = bm::U32(p);
  s.right_count = bm::U32(p + 4);
  s.timestamp = bm::U32(p + 8);
  s.state = p[14];
  s.fault = bm::U16(p + 15);
  s.encoder = p[17];
  s.left_period = bm::U32(p + 18);
  s.right_period = bm::U32(p + 22);
  s.left_age = bm::U32(p + 26);
  s.right_age = bm::U32(p + 30);
  return true;
}
Frame CommandFrame(uint32_t session, uint16_t seq, uint8_t dir, uint16_t left,
                   uint16_t right) {
  Frame f{};
  f.type = Command;
  f.length = 6;
  f.session = session;
  f.seq = seq;
  f.payload[1] = dir;
  bm::Put16(f.payload.data() + 2, left);
  bm::Put16(f.payload.data() + 4, right);
  return f;
}
void Parser::Reject(ErrorReason reason, uint64_t now, uint64_t gap) {
  ++errors;
  if (reason == ErrorReason::Timeout) ++diagnostics_.timeout_errors;
  else if (reason == ErrorReason::Header) ++diagnostics_.header_errors;
  else if (reason == ErrorReason::Crc) ++diagnostics_.crc_errors;
  diagnostics_.last_reason = reason;
  diagnostics_.last_size = uint8_t(size_);
  diagnostics_.last_gap_us = uint32_t(std::min<uint64_t>(gap, UINT32_MAX));
  diagnostics_.last_frame_us = uint32_t(std::min<uint64_t>(now - start_, UINT32_MAX));
}
bool Parser::Feed(uint8_t byte, uint64_t now, Frame& out) {
  const uint64_t gap = now - last_;
  if (size_ && (gap >= 2000 || now - start_ >= 6000)) {
    Reject(ErrorReason::Timeout, now, gap);
    size_ = 0;
  }
  last_ = now;
  if (!size_) {
    if (byte == 0xa5) {
      bytes_[size_++] = byte;
      start_ = now;
    }
    return false;
  }
  if (size_ == 1 && byte != 0x5a) {
    size_ = byte == 0xa5 ? 1 : 0;
    start_ = now;
    return false;
  }
  bytes_[size_++] = byte;
  const bool bad = (size_ == 3 && byte != 2) ||
                   (size_ == 4 && Length(byte) < 0) ||
                   (size_ == 5 && byte != Length(bytes_[3]));
  if (bad) {
    Reject(ErrorReason::Header, now, gap);
    size_ = byte == 0xa5 ? 1 : 0;
    start_ = now;
    return false;
  }
  if (size_ < 5 || size_ < size_t(13 + bytes_[4])) return false;
  const size_t n = size_;
  if (bm::Crc(bytes_.data() + 2, n - 4) != bm::U16(bytes_.data() + n - 2)) {
    Reject(ErrorReason::Crc, now, gap);
    size_ = 0;
    if (byte == 0xa5) {
      bytes_[0] = byte;
      size_ = 1;
      start_ = now;
    }
    return false;
  }
  size_ = 0;
  out = {};
  out.type = bytes_[3];
  out.length = bytes_[4];
  out.session = bm::U32(bytes_.data() + 5);
  out.seq = bm::U16(bytes_.data() + 9);
  std::copy_n(bytes_.data() + 11, out.length, out.payload.begin());
  return true;
}
}  // namespace awcar::fpga
