# Phần dùng chung

Nơi đặt đặc tả/kiểu dữ liệu giao thức UART, mã trạng thái và đơn vị đo dùng bởi
cả Brain và Motion, cùng đặc tả liên kết Motion-FPGA. Không chứa driver chỉ
dành riêng một MCU; RTL giải mã giao thức nằm trong `fpga/`.

Trạng thái: chưa có wire format hay mã nguồn. Ghim phiên bản giao thức và có
test hai đầu trước khi dùng để điều khiển xe. Hai liên kết có vai trò và timeout
riêng; telemetry/heartbeat không tự gia hạn quyền chạy motor.
