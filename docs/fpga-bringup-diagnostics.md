# Nghiệm thu RTL và đưa lên Tang Nano9K

Mốc02/11/2026. Mục tiêu là giảm rủi ro trước thử motor; mô phỏng không bảo đảm
bitstream chạy đúng trên board khi chưa gán chân/đặt timing/đo nguồn.

## Phần đã chuẩn bị trong RTL

`aw_car_top` là top duy nhất,17 tín hiệu một bit, lõi `drive_core` bên trong.
UART STATUS v2 giữ34 byte payload/47 byte frame, truyền cả số đếm/period/age,
trạng thái Safety và word lỗi16bit. [Bảng chẩn đoán](../firmware/shared/fpga-protocol-v2.md)
phân biệt lịch sử cảnh báo và lỗi khóa. Snapshot stall/invariant khóa đầu ra
và cần reset; reset vẫn không tự ARM. Không có chương trình tự chạy motor
để thử máy khi boot.

Giám sát này phát hiện **các điều kiện đã định nghĩa**; không tìm được mọi lỗi
thuật toán, mọi bit-flip, trượt bánh, sai chiều cơ khí hoặc chập công suất.
Không thể tự gửi UART khi FPGA mất clock/nguồn. ESP32 phải từ chối STATUS cũ/
sai CRC/sai phiên, hạ permit khi không có snapshot mới trong30ms + chu kỳ
kiểm tra không quá1ms theo hợp đồng hiện có. E-stop/gate độc lập vẫn bắt buộc.
Firmware Motion và việc in log console trên ESP32 chưa được triển khai;
đã có wire contract, test UART và decoder PC để ghép vào firmware thật.

## Cổng nghiệm thu trước nạp

1. Xác nhận đúng **Tang Nano9K/GW1NR-LV9QN88PC6/I5** và revision board.
   [Tài liệu Sipeed](https://wiki.sipeed.com/hardware/en/tang/Tang-Nano-9K/Nano-9K)
   ghi clock27MHz; dùng chu kỳ clock danh định37,037ns. Không chọn Nano1K.
2. Đối chiếu từng chân với [schematic Sipeed](https://dl.sipeed.com/fileList/TANG/Nano%209K/2_Schematic/Tang_Nano_9k_3672_Schematic.pdf).
   Bank có mức3,3V và1,8V; không mặc định mọi GPIO nhận3,3V hoặc5V. Chốt OUT
   encoder sau chuyển mức, TX/RX ESP32, reset/POR, gate và trạng thái mặc định.
   Chưa có bảng chân thực nên không phát hành CST với số pin đoán.
   Dùng4 chân IN1/IN2 hiện tại, không câu theo nhãn PWM/DIR của sơ đồ cũ.
3. Chạy Gowin Education đúng device: tổng hợp, place-and-route và STA. Kiểm
   tài nguyên/pin, clock constraints, setup/hold/slack, đường async vào FF đồng
   bộ, unconstrained paths và cảnh báo. Yosys generic không thay bước này.
4. Duyệt sơ đồ default-OFF khi FPGA chưa cấu hình/reset/mất nguồn, Motion treo
   hoặc mất clock. Xác nhận E-stop ngắt được driver độc lập cả khi IN đang HIGH.

Các cổng2–4 **chưa có bằng chứng hoàn thành**; không gọi source hiện tại là
bitstream Tang đã nghiệm thu. Không ghi đè các bản vẽ đang được chỉnh để tự
hợp thức hóa bảng pin hoặc sơ đồ gate.

## Trình tự thử trên bàn

| Bước | Thử | Điều kiện đạt |
| --- | --- | --- |
| 1 | Chưa nối motor/VM, nạp bitstream và reset | DISARMED, permitLOW, cả4 INLOW; không tự chạy |
| 2 | Thu UART | CRC/length/version đúng, timestamp/sequence mới; ESP32 ghi state/fault và giải mã mask |
| 3 | Xung encoder độc lập | BootHIGH không đếm giả; count/period/age thay đổi đúng bên, wrap không tạo tốc độ âm |
| 4 | UART nhiễu/CRC sai/sequence cũ | Có cảnh báo phù hợp, không áp dụng lệnh lỗi, watchdog không được gia hạn |
| 5 | ARM/CMD bằng fixture, đo4 IN | Đủ tiến/lùi/rẽ/quay, duty đo phù hợp, zero40ms/setup1us; chưa suy ra rotor dừng sau40ms |
| 6 | Encoder đứng khi yêu cầu chạy | Cờ12/13 sau ngưỡng đã chọn; phân biệt tốc độ thấp/đĩa/dây/ma sát trước kết luận hỏng |
| 7 | Mất CMD/STATUS, reset, E-stop, cắt clock có kiểm soát | Driver khóa; nhả lỗi/reset không khôi phục lệnh cũ |
| 8 | Nối driver và motor, bánh kê cao, nguồn giới hạn dòng | Dòng/áp/nhiệt chấp nhận được; dừng độc lập hoạt động trước thử xe trên sàn |

Có thể dùng [Gowin Analyzer Oscilloscope — SUG114](https://cdn.gowinsemi.com.cn/SUG114E.pdf)
để bắt tín hiệu nội bộ/triggers khi debug trên board. Đây là tùy chọn của
Gowin, chưa tích hợp IP GAO vào RTL độc lập hãng hiện tại. Thêm GAO phải chạy
lại fit/timing vì bộ bắt tín hiệu dùng tài nguyên FPGA.

## Chấm điểm

Điểm tự đánh giá kỹ thuật chỉ áp dụng cho logic/kiểm thử, không phải xác suất
an toàn hay chứng chỉ. Điểm cuối cùng và kết quả đợt kiểm tra nằm trong
[verification.md](../fpga/verification.md); các mục chưa có board evidence ở
trên không được cộng điểm như đã nghiệm thu.
