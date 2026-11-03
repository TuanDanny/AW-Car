# Brain AW-Car

`control_core` là lõi C++ độc lập ESP-IDF, dùng chung cho firmware và host simulator.
`brain_runtime` nối UART, GPTimer, WebSocket và các tool Xiaozhi. `aw_car_network`
quản lý AP+STA riêng profile AW-Car. Không tạo PWM hoặc giả firmware Motion thật.
Các giới hạn vận tốc mặc định chỉ dành cho thử bàn/giao thức, chưa hiệu chuẩn xe.
