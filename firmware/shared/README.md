# Giao thức dùng chung

`brain_motion_codec`: BM-v1 (SET_TWIST20/STATUS30byte), dùng cùng Brain/Motion.
`fpga_codec`: v2 tường minh (CMD19/STATUS47byte). C++17, little-endian,
CRC16/CCITT-FALSE, parser bounded/timeout, không ESP-IDF/driver/GPIO.
Test dùng Python CRC/vector độc lập.

- [BM-v1](brain-motion-protocol.md): lease/session/seq, neutral giữ ARM;
  HELLO trong FAULT chỉ mở phục hồi, CLEAR không ARM.
- [FPGA v2](fpga-protocol-v2.md): encoder một OUT, count/period/age và diagnostics.
- [GPIO/gate](fpga-safety.md): driver_permit riêng, phục hồi xác nhận,
  snapshot stale30+1ms và watchdog FPGA50ms.
- [V1](fpga-protocol.md) và vector cũ giữ hồi quy RTL baseline main;
  Motion không fallback v1. Có vector v2 riêng47byte.

Đã có Motion vòng hở và test host/RTL/console; chưa thử UART các board/gate/
motor. Brain đầy đủ ở nhánh AI/PR13 draft. Nhánh Motion chỉ đồng bộ contract/
codec, không gom toàn bộ RTL v2. [Bằng chứng](../../docs/motion-verification.md).

WS2812 GPIO48 (`AWCAR_STATUS_LED_GPIO`) chỉ báo trạng thái. StatsTask100ms
chọn màu bằng policy C++ chung, ghi RMT khi đổi màu, không thêm I/O vào ISR/
control/UART. Fault đỏ; LOCKED/chờ FPGA hoặc gate xanh dương; sẵn sàng cục bộ
xanh lá, không đồng nghĩa ARM. Console status có indicator và số lần ghi/lỗi.
