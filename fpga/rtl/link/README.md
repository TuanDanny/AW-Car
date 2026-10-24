# Liên kết Motion–FPGA

Bảy module SystemVerilog cho UART/giao thức, không chứa PWM/FSM/watchdog:

- `uart_rx.sv`: đồng bộ RX hai FF, kiểm tra start giữa bit, nhận8N1. Stop LOW
  báo framing_error; LOW liên tục11bit báo break_error một lần, đợi HIGH để
  phục hồi. Byte chỉ có nghĩa khi valid một clock.
- `uart_tx.sv`: ready/valid, chỉ lấy data khi ready; truyền đủ start/8data/stop,
  done sau stop đầy đủ. Pulse valid khi busy không được xếp hàng.
- `crc16_byte.sv`: tổ hợp CCITT-FALSE từng byte, polynomial1021; parser/TX
  bắt đầu FFFF, không tính hai byte preamble.
- `frame_rx.sv`: type điều khiển01..05, payload tối đa6; CRC/length/type/version
  đúng mới pulse frame_valid. Không đọc staging ngoài pulse. Timeout2ms giữa
  byte/5ms toàn frame; timeout thắng byte đúng hạn. Framing/break/flush hủy
  frame; preamble lồng có thể cần bỏ một frame rồi phục hồi. Không có FIFO32byte.
- `frame_tx.sv`: đóng băng snapshot/session/state/fault ở handshake, STATUS31byte.
  Busy báo snapshot_dropped, không queue. Giữ byte khi downstream chưa ready;
  CRC chỉ tiến khi nhận byte. byte_last/session/state đi cùng snapshot đóng băng.
- `command_guard.sv`: đúng phiên, sequence mới modulo16, duty/flags/chiều hợp lệ
  và command_enable mới phát command_valid cặp. ALLOW_REVERSE mặc định0.
  HELLO đề nghị phiên; ARM_ZERO/CLEAR_FAULT chỉ yêu cầu FSM. DISABLE đúng
  format/CRC giảm quyền kể cả phiên cũ, không đổi mốc sequence.
- `fpga_link.sv`: nối các khối, nhận snapshot/xuất sự kiện; rst_n phải nhả đồng
  bộ ở lớp tích hợp. status_sent chỉ pulse sau stop bit CRC cuối; context_load
  hủy xác nhận đang chờ, không dùng busy serializer làm xác nhận ARM.

UART dùng CLK_HZ/BAUD dương, chia làm tròn `(CLK_HZ + BAUD/2)/BAUD`, ít nhất
8tick/bit; mặc định27MHz/115200 =234tick/bit. Parser timeout >=1 và đủ dài cho
baud/frame. Chỉ đổi CLK_HZ không tự đổi timeout54000/135000 tick mặc định.

FSM cấp phiên/sequence_base qua context_load; đổi/hủy phiên cũng pulse tín
hiệu này, flush parser/TX, bỏ sự kiện cùng clock và xóa duty lưu. Quyền
command_enable chỉ từ ARMED và bị chặn ở timeout. Không dùng UART/HELLO làm
quyền chạy hoặc dùng lại duty nếu thiếu command_valid mới. TX có thể hoàn tất
byte cũ khi flush: Motion loại frame thiếu CRC/sai phiên, không coi byte cũ là
snapshot mới.

Trạng thái: đã có reference/vector/testbench và tổng hợp generic; chưa có
firmware Motion hoặc đo liên kết thực. Xem
[wire protocol](../../../firmware/shared/fpga-protocol.md) và
[hợp đồng safety](../../../firmware/shared/fpga-safety.md).
Script: `yosys -s fpga/synth_link.ys`, chạy từ root sau khi có `fpga/build/`.
Top toàn lõi: [drive_core.sv](../drive_core.sv).
