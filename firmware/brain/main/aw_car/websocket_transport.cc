#include "websocket_transport.h"
namespace awcar {
esp_err_t ServeControlWebSocket(httpd_req_t* req, void* context,
                                WebSocketDispatch dispatch,
                                WebSocketObserver observe) {
  auto event = [&](const char* name, int value = 0) {
    if (observe) observe(context, name, value);
  };
  if (req->method == HTTP_GET) return ESP_OK;
  httpd_ws_frame_t frame{};
  auto result = httpd_ws_recv_frame(req, &frame, 0);
  if (result != ESP_OK) {
    event("receive_error", result);
    return result;
  }
  const bool control = frame.type == HTTPD_WS_TYPE_PONG ||
                       frame.type == HTTPD_WS_TYPE_PING ||
                       frame.type == HTTPD_WS_TYPE_CLOSE;
  if (!frame.final || frame.len > (control ? 125 : 512) ||
      (!control && (frame.type != HTTPD_WS_TYPE_TEXT || !frame.len)) ||
      (frame.type == HTTPD_WS_TYPE_CLOSE && frame.len == 1)) {
    event("protocol_error", 1002);
    // Returning failure closes in HTTPD directly. Never enqueue a second close
    // referring to the SDK's reusable sock_db slot.
    return ESP_FAIL;
  }
  char body[513];
  if (frame.len) {
    frame.payload = reinterpret_cast<uint8_t*>(body);
    result = httpd_ws_recv_frame(req, &frame, 512);
    if (result != ESP_OK) {
      event("receive_error", result);
      return result;
    }
  }
  if (frame.type == HTTPD_WS_TYPE_PONG) {
    event("pong");
    return ESP_OK;
  }
  if (frame.type == HTTPD_WS_TYPE_CLOSE) {
    const int code =
        frame.len >= 2 ? (uint8_t(body[0]) << 8) | uint8_t(body[1]) : 1005;
    event("peer_close", code);
    result = httpd_ws_send_frame(req, &frame);
    if (result != ESP_OK) event("send_error", result);
    return ESP_FAIL;
  }
  if (frame.type == HTTPD_WS_TYPE_PING) {
    frame.type = HTTPD_WS_TYPE_PONG;
    result = httpd_ws_send_frame(req, &frame);
  } else {
    body[frame.len] = 0;
    auto reply = dispatch(context, body, frame.len);
    httpd_ws_frame_t response{};
    response.type = HTTPD_WS_TYPE_TEXT;
    response.payload = reinterpret_cast<uint8_t*>(reply.data());
    response.len = reply.size();
    result = httpd_ws_send_frame(req, &response);
  }
  if (result != ESP_OK) event("send_error", result);
  return result;
}
}  // namespace awcar
