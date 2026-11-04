# Brain AW-Car

`control_core` là lõi C++ độc lập ESP-IDF, dùng chung cho firmware và host simulator.
`brain_runtime` nối UART, GPTimer, WebSocket và các tool Xiaozhi. `aw_car_network`
quản lý AP+STA riêng profile AW-Car. Không tạo PWM hoặc giả firmware Motion thật.
`websocket_transport` xử lý frame trên handler riêng, độc lập `req->uri`
vốn bị ESP-IDF xóa sau handshake; có hồi quy host tại `tests/brain_http_stub`.
Các giới hạn vận tốc mặc định chỉ dành cho thử bàn/giao thức, chưa hiệu chuẩn xe.
SSID AP là `AW-CAR`; `CONFIG_AWCAR_AP_PASSWORD` trong sdkconfig cục bộ có
thể đặt mật khẩu cố định, được giữ lại trong NVS. PIN dashboard vẫn đổi mỗi boot.

`network_policy.h` tách reconnect/backoff khỏi I/O, kiểm thử trên host.
`socket_writer.h` hoàn tất short-write trước khi HTTPD coi một frame đã gửi.
UART RX dùng event/idle riêng, không đợi polling tick 10 ms của audio profile.
Xem [báo cáo mạng/WS](../../../../docs/brain-network-reliability.md).

WS2812 do status task nền sở hữu; đã xóa tool/handler RGB thử nghiệm.
Policy ở `firmware/shared/status_indicator.h`; không thêm LED I/O vào control/UART.

Mất STATUS ở DISARMED cũng thu context đúng một lần để nhận lại sequence
sau peer reboot. RememberSelectedWifi chỉ chạy khi người dùng đổi cấu hình,
đưa entry được chọn lên đầu danh sách NVS; không sửa dependency Wi-Fi.
