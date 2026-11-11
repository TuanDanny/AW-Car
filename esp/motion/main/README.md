# Firmware Motion

`runtime` owns Control/SPI/UART và mailbox. `web` HTTP/WS, snapshot/JSON ngoài
đường deadline. `main` khởi tạo AP+STA; lái xe chỉ AP, không xóa NVS khi init lỗi.
`network_activity.hpp` là predicate C++ thuần dùng chung với host test: intent
Waking/Reversing vẫn bận dù PWM0; giữ kiểm pending/OTA và STA đã online.

`Kconfig.projbuild`: đề-pa mũ thử nghiệm mặc định tắt, gain mặc định100% không
boost. Chỉ cấu hình khi build sau khi đo motor/dòng; Web chỉ quan sát trạng
thái này. Sáu action mới đi qua cùng mailbox/task/timeout với bốn action cũ.
