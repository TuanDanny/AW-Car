# Firmware Motion

`runtime` owns Control/SPI/UART và mailbox. `web` HTTP/WS, snapshot/JSON ngoài
đường deadline. `main` khởi tạo AP+STA; lái xe chỉ AP, không xóa NVS khi init lỗi.
`network_activity.hpp` là predicate C++ thuần dùng chung với host test: intent
Waking/Reversing vẫn bận dù PWM0; giữ kiểm pending/OTA và STA đã online.
