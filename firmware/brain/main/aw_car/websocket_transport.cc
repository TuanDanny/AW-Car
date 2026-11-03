#include "websocket_transport.h"

namespace awcar {
esp_err_t ServeControlWebSocket(httpd_req_t* req, void* context,
                                WebSocketDispatch dispatch) {
  if (req->method == HTTP_GET) return ESP_OK;
  httpd_ws_frame_t frame{};
  auto result = httpd_ws_recv_frame(req, &frame, 0);
  if (result != ESP_OK) return result;
  const bool pong = frame.type == HTTPD_WS_TYPE_PONG;
  if (frame.len > 512 || (pong && (frame.len > 125 || !frame.final)) ||
      (!pong &&
       (frame.type != HTTPD_WS_TYPE_TEXT || !frame.final || frame.len == 0))) {
    httpd_sess_trigger_close(req->handle, httpd_req_to_sockfd(req));
    return ESP_FAIL;
  }
  char body[513];
  if (frame.len) {
    frame.payload = reinterpret_cast<uint8_t*>(body);
    result = httpd_ws_recv_frame(req, &frame, 512);
    if (result != ESP_OK) return result;
  }
  // IDF also dispatches PONGs when control-frame handling is disabled.
  // Consume their bytes without interpreting them as control JSON.
  if (pong) return ESP_OK;
  body[frame.len] = 0;
  auto reply = dispatch(context, body, frame.len);
  httpd_ws_frame_t response{};
  response.type = HTTPD_WS_TYPE_TEXT;
  response.payload = reinterpret_cast<uint8_t*>(reply.data());
  response.len = reply.size();
  return httpd_ws_send_frame(req, &response);
}
}  // namespace awcar
