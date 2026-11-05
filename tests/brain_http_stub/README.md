# ESP-IDF WebSocket transport regression

Header stub chỉ mô tả phần HTTPD API mà transport thật sử dụng. Test biên
dịch `websocket_transport.cc` của firmware và giả lập I/O, gồm hành vi
ESP-IDF 6.1 xóa URI giữa handshake và frame. Không giả RTOS, Wi-Fi hay board.

Test thêm short-write socket và policy reconnect dùng cùng header C++ firmware.
Không dùng SDK giả để kết luận độ trễ Wi-Fi hoặc FreeRTOS thật.
