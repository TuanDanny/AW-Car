# Phần dùng chung

Nơi đặt đặc tả/kiểu dữ liệu giao thức UART, mã trạng thái và đơn vị đo dùng bởi
cả Brain và Motion, cùng đặc tả liên kết Motion-FPGA. Không chứa driver chỉ
dành riêng một MCU; RTL giải mã giao thức nằm trong `fpga/`.

Đã có [Motion–FPGA protocol v1](fpga-protocol.md) và
[vector nhị phân chung](fpga-vectors.hex), được đối chiếu bằng Python và test RTL.
[Hợp đồng GPIO/ARM/gate](fpga-safety.md) đã được triển khai trong FSM/top và
kiểm thử bằng mô hình. Chưa có firmware Motion hoặc giao thức Brain–Motion;
HELLO không tự bật motor. Hai liên kết có vai trò
và timeout riêng; telemetry/heartbeat không tự gia hạn quyền chạy motor.
