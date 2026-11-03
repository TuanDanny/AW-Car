# ESP-IDF WebSocket transport regression

Header stub chỉ mô tả phần HTTPD API mà transport thật sử dụng. Test biên
dịch `websocket_transport.cc` của firmware và giả lập I/O, gồm hành vi
ESP-IDF 6.1 xóa URI giữa handshake và frame. Không giả RTOS, Wi-Fi hay board.
