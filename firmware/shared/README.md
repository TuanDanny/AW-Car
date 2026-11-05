# Giao thức dùng chung

Một nguồn codec C++17 cho mỗi liên kết, không phụ thuộc ESP-IDF/RTOS/GPIO:

- `brain_motion_codec.h/.cc`: BM-v1, SET_TWIST20/STATUS30byte; chung Brain/Motion.
- `fpga_codec.h/.cc`: FPGA v2 tường minh, CMD19/STATUS47byte; Motion không fallback v1.
- `status_indicator.h`: policy LED chung hai board, mask lỗi0x88ff, cache đổi màu/retry1Hz.

[BM-v1](brain-motion-protocol.md) giữ neutral/STOP/CLEAR tách quyền; CRC16/CCITT-FALSE,
little-endian, session/sequence/TTL và parser timeout có test reference Python.
[FPGA v2](fpga-protocol-v2.md) có encoder một OUT/bên, count/period/age và diagnostics.
[GPIO/gate](fpga-safety.md) mô tả driver_permit độc lập, snapshot stale30+1ms,
watchdog FPGA50ms và phục hồi không tự ARM. [Bảng dây](../../hardware/motion-wiring.md).

[V1](fpga-protocol.md)/vector cũ giữ hồi quy RTL baseline main trong checkout này.
RTL v2 không nằm trong mốc tích hợp Brain+Motion; co-sim dùng peer commit7ab91b2
riêng. Không nạp RTL v1 baseline để ghép Motion v2. UART hai MCU đã thử ở source
riêng, nhưng bản integration chưa được flash; gate/FPGA/motor chưa nghiệm thu.
Xem [bằng chứng Motion](../../docs/motion-verification.md) và
[MERGE-READINESS](../../docs/MERGE-READINESS.md).
