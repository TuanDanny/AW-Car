#pragma once
#include <esp_http_server.h>

#include <cstddef>
#include <string>

namespace awcar {
using WebSocketObserver = void (*)(void*, const char*, int);
using WebSocketDispatch = std::string (*)(void*, const char*, size_t);
// Register this only as a WebSocket URI handler. ESP-IDF clears req->uri
// before dispatching established frames, so routing must not inspect it.
esp_err_t ServeControlWebSocket(httpd_req_t* req, void* context,
                                WebSocketDispatch dispatch,
                                WebSocketObserver observe = nullptr);
}  // namespace awcar
