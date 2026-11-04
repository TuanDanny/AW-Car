#pragma once
#include <cstddef>
#include <limits>
namespace awcar {
// ESP-IDF WS sends call send_fn once per header/payload. A positive short write
// must be completed before returning success, or the next frame corrupts it.
// Socket timeout bounds a call; a monotonic deadline also bounds repeated short
// writes. Errors, no progress or deadline expiry close the session.
template <typename Send, typename Expired>
int WriteAll(const char* data, size_t size, Send send, Expired expired) {
  if (size > size_t(std::numeric_limits<int>::max())) return -1;
  size_t sent = 0;
  while (sent < size) {
    if (expired()) return -1;
    const int n = send(data + sent, size - sent);
    if (n <= 0 || size_t(n) > size - sent) return -1;
    sent += size_t(n);
  }
  return expired() ? -1 : int(sent);
}
}  // namespace awcar
