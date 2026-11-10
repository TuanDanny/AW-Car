# FPGA simplev1

Tang Nano9K GW1NR-LV9QN88PC6/I5, một clock 27 MHz, SystemVerilog thuần.
Đây là triển khai mới cho [contract](../docs/protocol.md), không tương thích UART
FPGA cũ. [RTL](rtl/README.md), [target](targets/tang_nano9k/README.md),
[test](../test/rtl/README.md). Đã thử SRAM, lưu embedded Flash và nạp lại từ Flash;
SPI với Motion và dấu duty Manual/AI có log board thật. Đã đo đúng cực tính cầuB
haiDRV ởManual100%, VM USB khoảng5V, chưa motor. Xem [báo cáo kiểm chứng](../docs/verification.md).

```powershell
C:/Espressif/python_env/idf6.1_py3.13_env/Scripts/python.exe utils/build_fpga.py
```

Mặc định chạy Icarus (gồm đủ 13.500.000 clock watchdog), tổng hợp/PnR/STA Gowin
và kiểm netlist sau PnR. Có `--rtl-only`, `--gowin-only`, `--test tb_spi` để chẩn
đoán; báo cáo ghi rõ phần chưa chạy. Build/log/netlist ở `build/fpga`, không commit.
Không có thao tác Programmer, COM hoặc JTAG trong flow.

SPI mode0/1MHz có setup/hold/gap CS >=2us; MOSI chỉ được chốt sau CS lên và đúng
256 bit hợp lệ. RX là SR32 snapshot tại CS xuống, luôn có seq của lệnh trước.
`applied_seq` xác nhận setpoint đã chốt; chân driver cập nhật ở biên PWM kế tiếp
(<=50us, hoặc thêm một chu kỳ zero khi đổi dấu trực tiếp). Không chờ biên PWM
để cập nhật seq vì giao dịch tiếp có thể bắt đầu sau 2us.

Motion thực hiện guard cơ khí 40ms và nhớ dấu nonzero cuối. FPGA không cộng thêm
40ms; chỉ có một chu kỳ PWM zero 50us khi đổi dấu trực tiếp. Duty0=4 chân LOW,
|duty|1350=HIGH liên tục chân được chọn. Reset/timeout khóa PWM độc lập biên.
Watchdog 500ms chỉ được làm mới bởi lệnh hợp lệ, không có lỗi chốt/ARM/session.

Encoder hai FF đồng bộ, xác nhận mức ổn định 256 tick (~9,48us); baseline đầu
không sinh cạnh giả. Đếm cạnh lên unsigned; period có sau hai cạnh, age saturate.
Chân phải P28 không pull FPGA do đã có pull-up ngoài ở level shifter; P27 chưa
dùng kéo xuống. Lọc không thay điện trở ngoài hoặc chứng minh đầu vào thả nổi an toàn.

LED1 active-low: chờ nhấp nháy mỗi500ms, liên kết còn hạn sáng liên tục; LED2–6 tắt.
Observer không phản hồi vào PWM/SPI/watchdog. STA/mô phỏng không thay đo board/motor.
