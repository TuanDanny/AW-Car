#include "websocket_transport.h"

#include <cassert>
#include <cstring>
#include <iostream>
#include <string>

struct Session {
  httpd_req_t req{};
  std::string payload = "{\"type\":\"HEARTBEAT\",\"seq\":1}", reply;
  httpd_ws_type_t type = HTTPD_WS_TYPE_TEXT;
  bool final = true, closed = false;
  int headers = 0, bodies = 0, dispatched = 0, sent = 0;
  int header_error = 0, body_error = 0, send_error = 0;
  Session() {
    req.handle = this;
    req.user_ctx = this;
  }
  int run() {
    return awcar::ServeControlWebSocket(
        &req, this, [](void* p, const char* body, size_t n) {
          auto& s = *static_cast<Session*>(p);
          ++s.dispatched;
          assert(std::string(body, n) == s.payload);
          return std::string("ACK:") + std::string(body, n);
        });
  }
};
int httpd_req_to_sockfd(httpd_req_t* req) { return req->fd; }
int httpd_sess_trigger_close(httpd_handle_t handle, int) {
  static_cast<Session*>(handle)->closed = true;
  return ESP_OK;
}
int httpd_ws_recv_frame(httpd_req_t* req, httpd_ws_frame_t* frame,
                        size_t capacity) {
  auto& s = *static_cast<Session*>(req->user_ctx);
  if (!capacity) {
    ++s.headers;
    if (s.header_error) return s.header_error;
    frame->type = s.type;
    frame->final = s.final;
    frame->len = s.payload.size();
    frame->left_len = frame->len;
    return ESP_OK;
  }
  ++s.bodies;
  if (s.body_error) return s.body_error;
  assert(frame->payload && capacity >= s.payload.size());
  std::memcpy(frame->payload, s.payload.data(), s.payload.size());
  frame->left_len = 0;
  return ESP_OK;
}
int httpd_ws_send_frame(httpd_req_t* req, httpd_ws_frame_t* frame) {
  auto& s = *static_cast<Session*>(req->user_ctx);
  assert(frame->type == HTTPD_WS_TYPE_TEXT);
  ++s.sent;
  s.reply.assign(reinterpret_cast<char*>(frame->payload), frame->len);
  return s.send_error;
}
int main(int argc, char** argv) {
  assert(argc == 2);
  std::string test = argv[1];
  if (test == "handshake") {
    Session s;
    s.req.method = HTTP_GET;
    std::strcpy(s.req.uri, "/ws");
    assert(s.run() == ESP_OK);
    assert(!s.headers && !s.dispatched && !s.sent);
  } else if (test == "empty_uri") {
    Session s;  // ESP-IDF init_req(): method=0, uri="" for established frames.
    for (int i = 0; i < 1000; ++i) {
      assert(s.run() == ESP_OK);
      assert(s.reply == "ACK:" + s.payload);
    }
    assert(s.dispatched == 1000 && s.sent == 1000 && !s.closed);
  } else if (test == "boundaries") {
    for (size_t size : {size_t(1), size_t(512), size_t(513), size_t(0)}) {
      Session s;
      s.payload.assign(size, 'x');
      int result = s.run();
      bool valid = size > 0 && size <= 512;
      assert((result == ESP_OK) == valid);
      assert(s.closed == !valid);
      assert(s.dispatched == int(valid));
    }
    Session s;
    s.final = false;
    assert(s.run() == ESP_FAIL && s.closed);
    Session b;
    b.type = HTTPD_WS_TYPE_BINARY;
    assert(b.run() == ESP_FAIL && b.closed);
  } else if (test == "pong") {
    for (size_t size : {size_t(0), size_t(3), size_t(125), size_t(126)}) {
      Session s;
      s.type = HTTPD_WS_TYPE_PONG;
      s.payload.assign(size, 'p');
      assert((s.run() == ESP_OK) == (size <= 125));
      assert(!s.dispatched && !s.sent);
      assert(s.bodies == int(size > 0 && size <= 125));
    }
  } else if (test == "io_errors") {
    Session h;
    h.header_error = -8;
    assert(h.run() == -8 && !h.dispatched);
    Session b;
    b.body_error = -9;
    assert(b.run() == -9 && !b.dispatched);
    Session s;
    s.send_error = -7;
    assert(s.run() == -7 && s.dispatched == 1);
  } else {
    assert(false);
  }
  std::cout << "PASS " << test << '\n';
}
