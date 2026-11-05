# Bring-up AW-Car không motor — checklist

Ngày05/11 đã nạp SRAM; ngày06/11 người dùng giao lưu Flash và thử reset/liên
kết ba board. Tiến độ và giới hạn ở [báo cáo](flash-link-report.md); bảng dưới
giữ tiêu chí thử, không có nghĩa toàn bộ đã đạt. ARM/CMD/gate/công suất vẫn
ngoài mốc đang thử. Không chọn thiết bị/JTAG theo index lưu từ lần LED.

## Chuẩn bị và điều kiện dừng

- [ ] Chỉ có Nano9K cần nạp trên Programmer; nhận diện lại GW1NR-9C/id0x1100481B.
  Nếu Windows đảo USB Debugger A/0/1, nhận diện board lại, không thử index đoán.
- [ ] Ghi source commit, source hashes, Gowin version và bitstream SHA256 của
  lần build đã review; full regression/mapped/STA PASS. Không dùng led_test.fs.
- [ ] So schematic với revision thực, kiểm chiều J5/J6, GND và điện áp từng bank.
- [ ] Ngắt VM/pin2S, driver STBY/nSLEEP bị khóa vật lý; Motion vẫn LOCKED.
  Có thể chưa nối driver; đo các chân IN bằng logic analyzer3,3V.
- [ ] Chưa có gate/E-stop/chốt lỗi thì chỉ đo UART/encoder/reset, không coi là
  nghiệm thu an toàn và không mở khóa Motion để demo.
- [ ] Analyzer và generator đúng điện áp, chung GND; encoder OUT5V đi conditioner.
  Reset onboard pin3 ở1,8V: dùng nút S2, không cấp3,3V vào nút.

## Đo từng bước sau phê duyệt nạp

| Bước | Phép thử | Kỳ vọng / bằng chứng lưu |
| --- | --- | --- |
| 1 | Power-up/config, chưa lệnh | IN4 và fpga_permit/gate_clear LOW; ghi waveform từ trước DONE; cần bias/gate ngoài khi tristate |
| 2 | Nhấn/nhả nút package3, reset khi có UART | POR/reset về DISARMED; nếu safety/gate LOW hoặc thả nổi thì chuyển FAULT là đúng; không phát PWM/ARM/MOVE cũ |
| 3 | Thu UART không cấp quyền | 1152008N1, STATUSv2 length34/frame47, CRC đúng, snapshot mới10ms |
| 4 | Xung OUT_L riêng rồi OUT_R riêng | Chỉ đúng count/period/age đổi; mode bit4=1, direction-known bit7=0 |
| 5 | Frame CRC/version/length/session/seq sai | Không áp CMD, diagnostic đúng; malformed không được gia hạn watchdog |
| 6 | GPIO recovery/HELLO/ARM_ZERO theo contract | Ack pha đúng; STATUS ARM_PENDING gửi đủ; vẫn zero tới CMD hợp lệ mới |
| 7 | CMD và sáu hướng trong mô hình hoặc fixture không VM đã review | Duty đúng1350tick,20kHz; đảo nghỉ40ms/setup1us; không hai IN HIGH trái quy tắc |
| 8 | Ngừng CMD, tiếp tục quan sát | Watchdog50ms từ lệnh hợp lệ cắt quyền; cần recovery/ARM mới |
| 9 | Ngừng STATUS/reset/rút UART/clock-stop | Motion timeout mới30ms hạ driver_permit; không reconnect tự ARM |
| 10 | CLEAR trong FAULT: trước/đúng/sau250ms | Timeout thắng khi trùng; clear thành công về DISARMED, không ARM tự động |
| 11 | Gate/E-stop riêng, FPGA mất clock/chưa cấu hình/mất nguồn | Driver physical gate OFF độc lập; phải có phần cứng mới được đánh dấu đạt |

Các bước ARM/CMD chỉ là phương án fixture không công suất, **không phải quyền
sửa CONFIG_AWCAR_ENABLE_DRIVER hoặc motioncfg validated**. Nếu firmware LOCKED
chặn bước đó, ghi NOT RUN và thiết kế fixture riêng để duyệt trước; không lách khóa.

Không nối giả safety_ok/gate_fault_n HIGH chỉ để hiển thị DISARMED. Khi gate
chưa có, input pull-down có thể giữ FAULT; UART vẫn phải hoạt động và output
vẫn OFF. Bench số dùng healthHIGH để kiểm logic, không phải hướng dẫn nối tắt
phần cứng. Một số revision cũ đảo silk S1/S2: package3 và thông mạch là chuẩn.

## Điều kiện kết thúc

- [ ] Lưu logic-analyzer trace/UART frame CRC và kết quả từng mục PASS/FAIL/NOT RUN.
- [ ] Chưa có báo cáo gate/E-stop/mất nguồn thì vẫn chặn VM/motor.
- [ ] Nghiệm thu này không tự sửa pinout, nâng quyền hoặc merge FPGA vào main.
- [ ] Chỉ đề xuất thử công suất ở một phiên được phê duyệt, có sơ đồ gate/nguồn
  và ngưỡng dòng/tốc độ riêng. Không dùng mức LOW của FPGA như bảo đảm default-off.
