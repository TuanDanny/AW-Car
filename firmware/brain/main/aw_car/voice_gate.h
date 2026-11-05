#pragma once
#include <array>
#include <cstdint>
#include <cstring>
namespace awcar {
struct VoiceTicket {
  uint32_t epoch = 0, turn = 0;
  int id = 0;
  uint64_t received = 0;
  bool valid = false;
};
// A cloud message must carry the active session envelope. Never infer it from
// current mode when executing a callback queued by an older conversation.
class VoiceGate {
 public:
  void Epoch(uint32_t epoch) {
    if (epoch_ == epoch) return;
    epoch_ = epoch;
    if (sid_[0]) retired_[retired_slot_++ % retired_.size()] = sid_;
    sid_[0] = 0;
    have_stt_ = false;
    ++turn_;
  }
  bool Bind(const char* sid) {
    if (!sid || !*sid || std::strlen(sid) >= sid_.size()) {
      sid_[0] = 0;
      have_stt_ = false;
      ++turn_;
      return false;
    }
    for (const auto& old : retired_)
      if (std::strcmp(old.data(), sid) == 0) return false;
    if (std::strcmp(sid_.data(), sid) != 0) {
      sid_.fill(0);
      std::strncpy(sid_.data(), sid, sid_.size() - 1);
      have_stt_ = false;
      ++turn_;
      used_ids_.fill(0);
    }
    return true;
  }
  void Stt(const char* sid, uint64_t now) {
    if (!sid || !sid_[0] || std::strcmp(sid_.data(), sid) != 0) return;
    ++turn_;
    have_stt_ = true;
    stt_at_ = now;
  }
  VoiceTicket Capture(uint32_t epoch, int id, const char* sid,
                      uint64_t now) const {
    bool duplicate = false;
    for (auto used : used_ids_)
      if (used == id) duplicate = true;
    return {epoch, turn_, id, now,
            epoch == epoch_ && sid && sid_[0] &&
                std::strcmp(sid, sid_.data()) == 0 && have_stt_ &&
                now - stt_at_ < 5000000 && consumed_ != turn_ && id > 0 &&
                !duplicate};
  }
  bool Check(const VoiceTicket& t, uint32_t epoch, uint64_t now) const {
    return t.valid && epoch == epoch_ && t.epoch == epoch && t.turn == turn_ &&
           consumed_ != turn_ && sid_[0] && now - t.received < 120000 &&
           have_stt_ && now - stt_at_ < 5000000;
  }
  void Consume(const VoiceTicket& t) {
    consumed_ = t.turn;
    used_ids_[used_slot_++ % used_ids_.size()] = t.id;
  }
  bool Ready() const { return sid_[0] != 0; }

 private:
  uint32_t epoch_ = 1, turn_ = 0, consumed_ = 0;
  uint64_t stt_at_ = 0;
  bool have_stt_ = false;
  std::array<char, 96> sid_{};
  std::array<std::array<char, 96>, 4> retired_{};
  size_t retired_slot_ = 0, used_slot_ = 0;
  std::array<int, 64> used_ids_{};
};
}  // namespace awcar
