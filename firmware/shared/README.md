# Phần dùng chung

BM-v1 dùng giữa Brain và Motion: codec C++ độc lập SDK, source Brain/PC
peer và host tests tại nhánh này. [Contract](brain-motion-protocol.md) phân
biệt neutral giữ ARM, STOP bỏ ARM và CLEAR chỉ phục hồi, không cấp quyền.

Firmware Motion 0.1 đã có ở [nhánh Motion](https://github.com/TuanDanny/AW-Car/tree/codex/esp32-s3-motion/firmware/motion),
build/nạp COM7 mặc định khóa driver; chưa nghiệm thu UART hai board/gate/motor.
Motion yêu cầu FPGA v2/encoder một OUT mỗi bên, STATUS34/frame47; không suy
chiều đo từ chiều yêu cầu. Tham khảo [contract v2 hiện tại](https://github.com/TuanDanny/AW-Car/blob/codex/esp32-s3-motion/firmware/shared/fpga-protocol-v2.md)
và [hai đường permit/gate](https://github.com/TuanDanny/AW-Car/blob/codex/esp32-s3-motion/hardware/motion-wiring.md).

[Protocol v1](fpga-protocol.md), [vectors](fpga-vectors.hex) và
[safety baseline](fpga-safety.md) ở checkout AI giữ cho tương thích/hồi quy.
Phần RTL v2 phát triển ở nhánh FPGA, không tự nhập vào Brain. Hai liên kết
UART có session/CRC/sequence/timeout riêng; heartbeat không cấp quyền chạy.
