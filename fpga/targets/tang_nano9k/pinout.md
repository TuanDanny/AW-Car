# Tang Nano9K — hợp đồng chân AW-Car và LED

**SCHEMATIC AUDITED; BOARD MEASUREMENTS PENDING.** Đây là ứng viên cho board
không gắn LCD/HDMI/microSD. Mã revision trên board chưa xác nhận; các chân dùng
đã đối chiếu giống nhau trong schematic3672 và3674. Chưa cho phép nạp/đấu motor.

Số package khác số vị trí header và GPIO ESP32. `J5.5` nghĩa chân5 của J5 theo
schematic, không đếm tùy ý từ đầu có USB. Xác nhận silk, GND và thông mạch trước
khi đấu. `—` nghĩa nối nội bộ board, không có chân header trong contract này.

| Signal | Hướng FPGA | Package | Header | Bank / VCCIO | Peer / chức năng |
| --- | --- | ---: | --- | --- | --- |
| `clk` | input | 52 | — | 1 / 3.3V | Oscillator U16.OUT |
| `arst_n` | input | 3 | — | 3 / 1.8V | Onboard S2 only |
| `rx` | input | 25 | J5.5 | 2 / 3.3V | Motion GPIO15 TX |
| `tx` | output | 26 | J5.6 | 2 / 3.3V | Motion GPIO16 RX |
| `left_out` | input | 27 | J5.7 | 2 / 3.3V | Encoder left via 5V-to-3.3V conditioner |
| `right_out` | input | 28 | J5.8 | 2 / 3.3V | Encoder right via 5V-to-3.3V conditioner |
| `motion_permit_async` | input | 29 | J5.9 | 2 / 3.3V | Motion GPIO4 logical permit |
| `recovery_req_async` | input | 30 | J5.10 | 2 / 3.3V | Motion GPIO5 |
| `safety_ok_async` | input | 33 | J5.11 | 2 / 3.3V | External safety; also Motion GPIO8 input |
| `gate_fault_n_async` | input | 34 | J5.12 | 2 / 3.3V | External latch; also Motion GPIO9 input |
| `drv_left_in1` | output | 35 | J5.14 | 2 / 3.3V | Left driver IN1, VM disconnected |
| `drv_left_in2` | output | 40 | J5.13 | 2 / 3.3V | Left driver IN2, VM disconnected |
| `drv_right_in1` | output | 41 | J5.15 | 2 / 3.3V | Right driver IN1, VM disconnected |
| `drv_right_in2` | output | 42 | J5.16 | 2 / 3.3V | Right driver IN2, VM disconnected |
| `fpga_permit` | output | 51 | J5.17 | 1 / 3.3V | External gate and Motion GPIO7 input |
| `recovery_ack` | output | 48 | J6.19 | 1 / 3.3V | Motion GPIO6 input |
| `gate_clear` | output | 49 | J6.20 | 1 / 3.3V | External latch clear request |
| `leds_n[0]` | output | 10 | — | 3 / 1.8V | Onboard LED1, active-low |
| `leds_n[1]` | output | 11 | — | 3 / 1.8V | Onboard LED2, active-low |
| `leds_n[2]` | output | 13 | — | 3 / 1.8V | Onboard LED3, active-low |
| `leds_n[3]` | output | 14 | — | 3 / 1.8V | Onboard LED4, active-low |
| `leds_n[4]` | output | 15 | — | 3 / 1.8V | Onboard LED5, active-low |
| `leds_n[5]` | output | 16 | — | 3 / 1.8V | Onboard LED6, active-low |

17 tín hiệu chức năng giữ nguyên; thêm6 output LED onboard thành23 tín hiệu.
LED1–6 là thứ tự firmware theo bảng; xác nhận silk thực trước gọi tên vị trí.
Các tín hiệu ngoài UART ở3,3V; reset và LED onboard dùng bank3,1,8V.
**Không nối ESP32/3,3V vào reset package3. Package4/JTAGSEL_N không sử dụng.**
Một số revision cũ đảo tên silk S1/S2; phải xác nhận nút nối package3 bằng
schematic/continuity, không chỉ dựa vào tên nút trên board.
Không đưa5V OUT encoder vào FPGA. Logic converter cần đúng hướng, mức điện áp
và trạng thái khi một board mất nguồn. Các chân RGB/SPI LCD ở bảng phải để trống
ngoại vi; chúng vẫn nối tới connector LCD. Pin51 có chức năng clock phụ nhưng
được cấu hình output GPIO, không tạo clock. Danh sách shared/reserved đầy đủ trong
[pinout.json](pinout.json), được checker đối chiếu CST và package database Gowin.

GND chung tại J6.23. J6.24 là3,3V, J6.18 là5V: không nối chung hai rail3,3V
của ESP32 và Nano khi mỗi board dùng USB riêng. Nối GND và tín hiệu đúng mức.
Nguồn/năng lượng của gate phải giữ default-off khi FPGA chưa cấu hình hoặc mất
nguồn. Pull-down trong CST chỉ có tác dụng sau cấu hình, không thay điện trở/gate
ngoài. Các chân IN/permit/clear cần bias OFF vật lý theo thiết kế gate sau này.

Motion tham chiếu main`4cea85c`: UART2 TX15→FPGA RX25; FPGA TX26→RX16.
GPIO4 là logical motion_permit tới FPGA. **GPIO10 driver_permit đi gate riêng**,
không phải một cổng FPGA thứ18 và không được thay bằng GPIO4. ARM/recovery theo
[contract main đã đồng bộ](../../../firmware/shared/fpga-safety.md).

## Nguồn kiểm chứng

- [Sipeed schematic3672, PDF trang2](https://dl.sipeed.com/fileList/TANG/Nano%209K/2_Schematic/Tang_Nano_9k_3672_Schematic.pdf).
- [Sipeed schematic3674, PDF trang2](https://dl.sipeed.com/fileList/TANG/Nano%209K/2_Schematic/Tang_nano_9K_3674_schematics.pdf).
- [Sipeed Nano9K specifications và cảnh báo I/O](https://wiki.sipeed.com/hardware/en/tang/Tang-Nano-9K/Nano-9K.html).
- Package database Gowin1.9.11.03 Education: `IDE/data/device/GW1NR-9C/QFN88P.json`.
  SHA256 của ba nguồn cụ thể nằm trong pinout.json. Hai PDF được tải từ Sipeed
  và giữ ở build ignored để đối chiếu; không chép tài liệu hãng vào source Git.

Chưa đo bank điện áp, thông mạch, mức idle hoặc timing trên board AW-Car.
Bài LED thật do người dùng xác nhận chỉ xác nhận board/nạp SRAM/bài LED hoạt động.
