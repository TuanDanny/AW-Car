# FSM an toàn và watchdog

`safety_fsm.sv` quản lý DISARMED/HANDSHAKE/ARM_PENDING/ARMED/FAULT/CLEAR_WAIT.
GPIO recovery mới là bắt buộc; HELLO không tự ARM. ARM_ZERO khởi tạo watchdog;
STATUS ARM_PENDING gửi đủ và Motion permit mới cho ARMED. Timeout thắng CMD
cùng cạnh; DISABLE/fault hủy phiên. Clear thành công vẫn về DISARMED và cần
phục hồi/ARM mới.

Mặc định watchdog1.350.000 tick (50ms), handshake6.750.000 (250ms), clear135.000
(5ms), hold2.700 (100us) tại27MHz. Không tự scale khi chỉ đổi clock. Chỉ CMD
mới hợp lệ khi ARMED gia hạn watchdog; heartbeat/STATUS/frame cũ không gia hạn.

Handshake/recovery, watchdog và clear dùng chung một bộ đếm theo pha vì các
pha không chạy đồng thời; mỗi lần vào pha đều nạp deadline riêng. Hold clear
dùng ngưỡng trên chính bộ đếm đó, không dùng prescaler hoặc clock sinh thêm.
Tại27MHz,74bit timer cũ còn23bit; timeout vẫn thắng lệnh/gate tới đúng hạn.
Hold bằng hoặc dài hơn clear window không thể clear thành công. Tính tương
đương và invariant phiên/recovery được kiểm bằng công cụ ở `tools/`.

Trạng thái: đã mô phỏng trạng thái, timeout/biên deadline/reset và tích hợp
trong [drive_core.sv](../drive_core.sv); đã tổng hợp generic toàn top bằng
`fpga/synth_drive.ys`. Chưa có timing sau route hoặc phép đo phần cứng.
Watchdog này cần clock FPGA; Motion phải khóa driver độc lập khi snapshot
cũ/mất phản hồi, E-stop/gate ngoài không được phụ thuộc clock FPGA.
Đặc tả đầy đủ: [hợp đồng an toàn](../../../firmware/shared/fpga-safety.md).
