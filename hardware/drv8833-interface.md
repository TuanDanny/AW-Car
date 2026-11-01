# Giao tiếp FPGA với hai module DRV8833

Cập nhật 01/11/2026. Adapter logic nằm ở
[drv8833_adapter.sv](../fpga/rtl/pwm/drv8833_adapter.sv), đã nối trong
`drive_core`. Chưa chốt chân vật lý Tang Nano9K hoặc đo module/motor thật.
Tham chiếu chính: [TI DRV8833 Rev.E, bảng1/2, mục6.5 và7.3.4](https://www.ti.com/lit/ds/symlink/drv8833.pdf).
Tên STBY/AO/BO dưới đây theo module đỏ chủ dự án đã gửi; cần đối chiếu board
nhận được, không suy chân chỉ từ màu PCB.

## Quy tắc adapter

`direction[0]` điều khiển bên trái, `[1]` bên phải; 0=thuận, 1=ngược.
Chọn PWM drive/coast (fast decay):

| Quyền chạy | PWM | Chiều | IN1 | IN2 | Trạng thái |
| --- | --- | --- | --- | --- | --- |
| Reset hoặc không được phép | bất kỳ | bất kỳ | 0 | 0 | Ngắt kích cầu H, thả trôi |
| Có | 0 | bất kỳ | 0 | 0 | Thả trôi |
| Có | 1 | thuận | 1 | 0 | Kích thuận |
| Có | 1 | ngược | 0 | 1 | Kích ngược |

Bảng giả định driver đã thức và nguồn hợp lệ. TI còn có trạng thái IN1=IN2=1
để phanh; adapter hiện không phát trạng thái này. PWM zero/DISABLE không có
nghĩa xe dừng cơ học ngay. `motor_pwm_pair` vẫn chịu trách nhiệm khoảng zero
và setup khi đảo chiều; adapter chỉ ánh xạ tổ hợp, không có counter/FSM/PWM thứ hai.
Reset/enable LOW kéo bốn IN xuống LOW mà không cần cạnh clock.

Mặc định hiện tại nghỉ zero40ms rồi setup1us. Hai ứng viên30/40ms được thử
về logic/timer/lệnh mới/watchdog; chưa đủ dữ liệu để gọi giá trị nào tối ưu
cơ khí. 40ms vẫn cần thử dòng đổi chiều, thời gian giảm tốc và quãng trôi
trên xe thật; không lấy số đếm timer làm bằng chứng bánh đã dừng.

## Cách nối bốn motor: một module mỗi bên

Hai cầu H trên cùng module nhận chung lệnh bên đó, nhưng mỗi cầu H nối một
motor riêng. Như vậy chỉ cần bốn tín hiệu điều khiển từ FPGA:

| Đầu ra `drive_core` | Module trái | Module phải |
| --- | --- | --- |
| `drv_left_in1` | AIN1 và BIN1 | — |
| `drv_left_in2` | AIN2 và BIN2 | — |
| `drv_right_in1` | — | AIN1 và BIN1 |
| `drv_right_in2` | — | AIN2 và BIN2 |

| Module/cầu H | Đầu ra công suất | Motor |
| --- | --- | --- |
| Trái/A | AO1–AO2 (AOUT1–AOUT2) | Trái trước |
| Trái/B | BO1–BO2 (BOUT1–BOUT2) | Trái sau |
| Phải/A | AO1–AO2 | Phải trước |
| Phải/B | BO1–BO2 | Phải sau |

Chỉ nối chung **đầu vào logic** như bảng; không nối chập các đầu AO/BO.
Hiệu chuẩn cực dây từng motor khi nâng bánh để cả hai motor cùng bên đi đúng
chiều quy ước. `pwm_left/right` và `direction` là tín hiệu trung gian/debug;
bốn chân `drv_*_in*` mới nối tới IN của driver, không nối vào AO/BO.

## Mức điện áp và cho phép chạy

- Chọn GPIO FPGA bank3,3V cho các IN: TI yêu cầu HIGH tối thiểu2V ở xIN và
  2,5V ở nSLEEP; logic1,8V không đáp ứng. Adapter RTL không chuyển điện áp.
- Chung GND FPGA/Motion/driver. VM dùng nhánh pin2S theo
  [phương án nguồn](README.md); không đưa VM vào GPIO.
- STBY của module cần xác minh tương ứng nSLEEP. Đường này thuộc mạch khóa
  độc lập/E-stop với trạng thái tắt mặc định, không lấy PWM làm STBY.
  Sau khi đưa HIGH, chờ ít nhất1ms trước lệnh chạy đầu theo mục7.3.4.
  Nếu STBY được gate bằng hai permit, Motion chỉ bắt đầu đợi khi cả hai đã
  HIGH, rồi mới gửi CMD; ARM_ZERO vẫn giữ duty0. Không dùng khoảng zero/setup
  đổi chiều để thay thời gian đánh thức. Adapter không phát STBY hoặc giám
  sát thời gian driver thức; đây là điều kiện của Motion/mạch ngoài.
- Kiểm tra pull-up STBY có sẵn trên module trước khi nối mạch gate/GPIO;
  đường này có thể được kéo lên VM. Các chân NC để trống. Nếu nFAULT thực sự
  được đưa ra thì xử lý theo hợp đồng lỗi, không mặc định NC là nFAULT.
- `enable` trong adapter lấy quyền đã kiểm tra ở top. Mạch khóa ngoài vẫn
  phải ngắt được khi FPGA chưa cấu hình, mất nguồn hoặc clock đứng; Motion
  có đường khóa riêng và không tự khôi phục lệnh sau lỗi.

## Kiểm chứng và giới hạn

Unit test kiểm tra64 tổ hợp reset/enable/PWM/chiều, kéo LOW không cần clock;
bài UART tích hợp kiểm tra số tick kích thuận/ngược tại các chân IN qua
nhiều duty, khoảng đổi chiều, reset, E-stop và timeout. Xem
[bằng chứng](../fpga/verification.md).

Đây là mô phỏng chân logic, không mô hình hóa dòng, nhiệt, nguồn, thời gian
lan truyền và bộ lọc xung đầu vào DRV8833. Duty một tick tại27MHz chỉ khoảng
37ns; không suy ra motor nhận được xung công suất đó. Cần đo miền duty hữu ích
trên driver thật. GPIO bank/pin, pull-down/gate, timing sau route và dòng
khởi động/kẹt của từng motor vẫn cần xác nhận trước khi chạy xe.
