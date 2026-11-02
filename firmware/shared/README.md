# Phần dùng chung

Nơi đặt đặc tả/kiểu dữ liệu giao thức UART, mã trạng thái và đơn vị đo dùng bởi
cả Brain và Motion, cùng đặc tả liên kết Motion-FPGA. Không chứa driver chỉ
dành riêng một MCU; RTL giải mã giao thức nằm trong `fpga/`.

Đã chốt [Brain–Motion protocol v1 — đặc tả field](brain-motion-protocol.md)
cho UART giữa hai ESP32-S3, gồm SET_TWIST, STATUS, HELLO/ARM/STOP/CLEAR và
CRC16/session/sequence; **chưa viết firmware/kiểm thử trên board**.
Đã có [Motion–FPGA protocol v1](fpga-protocol.md) và
[vector nhị phân chung](fpga-vectors.hex), được đối chiếu bằng Python và test RTL.
[Phần GPIO/ARM của hợp đồng gate](fpga-safety.md) đã được triển khai trong FSM/top
và kiểm thử bằng mô hình; thời gian thức STBY của DRV8833 cần Motion/mạch ngoài
bảo đảm, chưa mô phỏng chip công suất. Chưa có firmware Motion;
HELLO không tự bật motor. Hai liên kết có vai trò
và timeout riêng; telemetry/heartbeat không tự gia hạn quyền chạy motor.

Ngày 28/10/2026 chủ dự án chọn khung TT 4WD lái theo hai bên. Giữ CMD hai
duty/chiều và STATUS hai encoder cho hai nhóm trái/phải; chưa có bốn kênh
độc lập. Brain–Motion gửi vận tốc thẳng/tốc độ quay thay góc servo theo wire format
[BM-v1](brain-motion-protocol.md). Driver/adapter bốn motor và
giới hạn hai encoder ở [bảng linh kiện](../../hardware/components.md).

Hai bộ đọc V2 một OUT dùng protocol v2 phân biệt mode/count với v1 X4
quadrature và thêm period/age cho tốc độ thấp; xem
[kế hoạch](../../docs/single-channel-encoder-plan.md).
RTL v2 có mô phỏng và [vector golden v2](fpga-vectors-v2.hex) từ công cụ
Python dùng chung; bộ thử serializer đối chiếu từng byte/CRC với vector này.
**Chưa có firmware Motion hoặc đo kiểm trên board thật**. Mặc định
`drive_core`/`drive_core_single_out` dùng v2, STATUS 34 byte/frame 47 byte.
V1 giữ nguyên vector cũ 18/31 byte; cấu hình tương thích một OUT v1 phải đặt
`ENCODER_SINGLE_OUT=1, PROTOCOL_VERSION=1` và đọc mode bit4, không có period/age.
