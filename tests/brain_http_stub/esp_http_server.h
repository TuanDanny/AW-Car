#pragma once
#include <cstddef>
#include <cstdint>
using esp_err_t = int;
using httpd_handle_t = void*;
constexpr int ESP_OK = 0, ESP_FAIL = -1, HTTP_GET = 1;
enum httpd_ws_type_t {
  HTTPD_WS_TYPE_TEXT = 1,
  HTTPD_WS_TYPE_BINARY = 2,
  HTTPD_WS_TYPE_PONG = 10
};
struct httpd_req_t {
  int method = 0, fd = 7;
  char uri[64]{};
  httpd_handle_t handle = nullptr;
  void* user_ctx = nullptr;
};
struct httpd_ws_frame_t {
  bool final = true, fragmented = false;
  httpd_ws_type_t type = HTTPD_WS_TYPE_TEXT;
  uint8_t* payload = nullptr;
  size_t len = 0, left_len = 0;
};
int httpd_req_to_sockfd(httpd_req_t*);
esp_err_t httpd_sess_trigger_close(httpd_handle_t, int);
esp_err_t httpd_ws_recv_frame(httpd_req_t*, httpd_ws_frame_t*, size_t);
esp_err_t httpd_ws_send_frame(httpd_req_t*, httpd_ws_frame_t*);
