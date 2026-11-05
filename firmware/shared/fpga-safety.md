# Hợp đồng an toàn Motion–FPGA

RTL tương ứng ở nhánh FPGA: `safety_fsm.sv`, `drive_core.sv` và
`aw_car_top.sv`. Contract GPIO dùng cho v1/v2; Motion 0.1 bắt buộc v2 từ
nhánh FPGA, không dùng RTL v1 baseline trong checkout Motion từ main.
Đã có Motion C++/ESP-IDF và co-sim; chưa nghiệm thu mạch gate/motor thực tế.

Đổi chiều hiện nghỉ PWM40ms và setup1us. Watchdog50ms không tạm dừng trong
interlock. Motion tiếp tục gửi CMD mới/hợp lệ theo vòng điều khiển; FPGA cập
nhật mục tiêu đang chờ mà không đếm lại WAIT_ZERO. Khoảng40ms chỉ là giá trị
thử logic, không thay cho giảm tốc/đo tốc độ và dòng trước đảo chiều trên xe.

## Tín hiệu ngoài UART

| Tín hiệu logic | Hướng | Vai trò |
| --- | --- | --- |
| motion_permit | Motion -> FPGA | Permit logic, mặc định LOW; giữ tới ACK DISABLE khi DỪNG bình thường |
| driver_permit | Motion -> gate | GPIO riêng mặc định LOW, khóa driver ngay độc lập UART |
| recovery_req | Motion -> FPGA | Mặc định LOW; yêu cầu phục hồi mới, chỉ khi Motion permit LOW |
| recovery_ack | FPGA -> Motion | Xác nhận yêu cầu GPIO; sau ARM dùng để báo đã gửi xong STATUS ARM_PENDING |
| safety_ok | Mạch an toàn -> FPGA và gate | HIGH khi E-stop/nguồn hợp lệ; LOW khóa ngay độc lập clock |
| gate_fault_n | Chốt lỗi ngoài -> FPGA | HIGH khi chốt gate đã được clear; LOW giữ driver tắt |
| gate_clear | FPGA -> chốt ngoài | Yêu cầu clear; không thay quyền khóa trực tiếp của E-stop/Motion |
| fpga_permit | FPGA -> gate | HIGH chỉ trong ARMED với các điều kiện hợp lệ |

Các tín hiệu trên là mức logic, chưa phải pinout hay thiết kế điện. Gate ngoài
cho phép driver khi **driver_permit, fpga_permit, safety_ok và gate_fault_n đều HIGH**.
motion_permit chỉ tới FPGA, không thay driver_permit.
Pull-down/trạng thái khi chưa cấu hình phải giữ driver tắt. Chốt lỗi ngoài
ưu tiên SET khi E-stop/nguồn lỗi, kể cả lỗi ngắn hoặc FPGA mất clock. Chỉ
nhận clear khi lỗi vật lý đã hết và cả hai permit LOW; nhả nút/nguồn trở lại
không tự clear. Mô hình test khởi động với chốt lỗi LOW, cần clear chủ động.

`drive_core` capture LOW bất đồng bộ và nhả qua hai FF cho safety/gate/permit;
đồng bộ riêng recovery_req, đợi mẫu đầu hợp lệ trước khi xử lý. PWM/permit
còn được mask trực tiếp bởi reset và các điều kiện raw. Các đường mask/reset
này cần review recovery/removal, glitch và timing ở target; simulation không
chứng minh metastability. Reset ngoài phải thực sự assert khi cấp nguồn.

## Trình tự phục hồi và ARM

1. Motion khóa cả hai permit, ngừng phát lệnh truyền động, xóa hàng đợi TX/RX cũ. Sau reset
   phải quan sát FPGA ack LOW; FPGA cần quan sát req LOW và permit LOW sau
   khi input hợp lệ. GPIO HIGH còn sót lúc boot không mở cửa handshake.
2. Motion nâng req, đợi ack HIGH; FPGA hủy phiên và flush link. Motion hạ req,
   đợi ack LOW. Từ đây chỉ có một cửa nhận HELLO; req không phải quyền chạy.
3. Để UART yên ít nhất 5 ms rồi gửi HELLO với session mới khác zero và sequence
   khởi đầu. Chỉ HELLO trong cửa này mới cài phiên; HELLO khi chạy bị bỏ qua.
   Toàn cửa req/HELLO và bước HANDSHAKE có timeout 250 ms mặc định.
4. Khi không có FAULT: gửi ARM_ZERO với sequence mới. FPGA vào ARM_PENDING,
   PWM/permit vẫn LOW và **bắt đầu watchdog 50 ms ngay tại đây**.
5. FPGA gửi STATUS đúng session với state ARM_PENDING, đợi UART phát đủ stop
   bit CRC cuối rồi mới nâng ack. Motion phải nhận/kiểm tra CRC, session,
   snapshot mới và state ARM_PENDING, đồng thời thấy ack HIGH sau chuỗi ack
   HIGH->LOW của bước 2. Không nâng permit chỉ vì thấy một GPIO HIGH.
6. Motion mới nâng permit. FPGA vào ARMED, không reset watchdog ở cạnh này;
   duty vẫn zero cho đến CMD hợp lệ mới. CMD từ PID mới, không phát lại cache.
   Nếu permit lên trước xác nhận STATUS thì FPGA chốt FAULT.

Với DRV8833, nếu gate điều khiển STBY/nSLEEP theo permit, Motion phải bảo đảm
driver được đưa HIGH đủ ít nhất1ms trước CMD chạy đầu tiên. Chờ từ khi cả
hai permit thực sự HIGH; ARM_ZERO vẫn giữ duty0. Khoảng chờ nằm trong lease
50ms đang chạy, không gia hạn watchdog. Adapter không giám sát STBY hoặc
thay thời gian thức bằng zero/setup khi đảo chiều. Điều kiện điện và bảng nối:
[đấu nối Motion/DRV8833](../../hardware/motion-wiring.md). Mô hình hiện kiểm
tra chân IN, chưa mô phỏng chip ngủ/thức hay nguồn công suất.

Session32 không tự bảo đảm duy nhất sau reset hai đầu và không phải xác thực.
Motion phải tạo session mới, không tái dùng trong thời gian buffer có thể còn
dữ liệu cũ, flush buffer và thực hiện đủ GPIO/STATUS handshake. Firmware cần
kiểm thử lại hợp đồng này; mô hình hiện dùng session tăng cho từng phục hồi.
Đường GPIO riêng và permit bổ sung chân I/O so với phương án chỉ có UART.

Nếu đang FAULT: hoàn thành bước 1–3 để có phiên phục hồi, gửi CLEAR_FAULT với
sequence mới trong khi permit LOW và lỗi vật lý đã hết. Session do HELLO mở
trong FAULT hết hạn sau250ms tính từ lúc HELLO được nhận, dù state vẫn FAULT.
CLEAR_FAULT phải đến trước hạn; timeout thắng nếu trùng clock, chốt bit6 và
hủy phiên. Sau đó phải làm lại GPIO recovery + HELLO, không chỉ gửi lại UART.
FAULT chưa có phiên/cửa phục hồi đang mở không bị áp timeout người vận hành.
FPGA giữ gate_clear
ít nhất 100 us, chờ gate_fault_n HIGH, tối đa 5 ms. Timeout/permit lên/req mới/
lỗi quay lại sẽ chốt FAULT. Thành công xóa lỗi, hủy phiên và về DISARMED;
**phải làm lại toàn bộ phục hồi rồi ARM**, không mở motor ngay sau clear.

```mermaid
stateDiagram-v2
    [*] --> DISARMED
    DISARMED --> HANDSHAKE: GPIO mới + HELLO
    HANDSHAKE --> ARM_PENDING: ARM_ZERO / bắt đầu 50 ms
    ARM_PENDING --> ARMED: STATUS gửi đủ + Motion permit
    ARMED --> DISARMED: DISABLE / hủy phiên
    ARM_PENDING --> FAULT: timeout hoặc lỗi
    ARMED --> FAULT: timeout hoặc lỗi
    HANDSHAKE --> FAULT: hết hạn hoặc lỗi
    DISARMED --> FAULT: lỗi ngoài
    FAULT --> CLEAR_WAIT: phục hồi + CLEAR_FAULT
    CLEAR_WAIT --> DISARMED: gate xác nhận / hủy phiên
    CLEAR_WAIT --> FAULT: lỗi hoặc hết hạn
```

## Watchdog và trạng thái

Mặc định 27 MHz: 1.350.000 tick = 50 ms. Nếu ARM được nhận ở t0 thì hết hạn
ở cạnh t0+N; CMD hợp lệ một tick trước hạn được nhận, CMD đúng cạnh hết hạn
bị loại. Chỉ CMD mới được guard chấp nhận **khi ARMED** gia hạn. HELLO,
ARM lặp, CLEAR, dữ liệu sai/duplicate/sai phiên và STATUS không gia hạn.
DISABLE hợp lệ giảm quyền dù sai phiên/sequence; hủy phiên và duty đang chờ.

| safety_state8 | Ý nghĩa |
| --- | --- |
| 0 | DISARMED |
| 1 | HANDSHAKE, đã cài phiên, chưa ARM |
| 2 | ARM_PENDING, watchdog đã chạy, đang chờ xác nhận |
| 3 | ARMED, có thể nhận CMD |
| 4 | FAULT, lỗi chốt |
| 5 | CLEAR_WAIT, đang yêu cầu clear chốt ngoài |

| Bit fault16 | Ý nghĩa |
| --- | --- |
| 0 | Watchdog hết hạn |
| 1 | E-stop/nguồn không hợp lệ hoặc chốt gate báo lỗi |
| 2 | Motion permit mất khi ARMED |
| 3 | Vi phạm phục hồi: req khi đang arm/chạy, permit quá sớm hoặc trong clear |
| 4 | PWM từ chối lệnh nội bộ, cần xem lỗi tích hợp |
| 5 | Gate không xác nhận clear trong hạn |
| 6 | Handshake hết hạn |
| 7 | Mã trạng thái FSM không hợp lệ |
| 8–15 | V1 dự phòng; v2 là diagnostic sticky, xem [bảng v2](fpga-protocol-v2.md) |

Lỗi có thể tích lũy; reset xóa FSM nhưng không được tự clear chốt phần cứng.
STATUS đóng băng state/fault lúc nhận snapshot, có thể cũ tới một chu kỳ mẫu
cộng thời gian UART. Không dùng STATUS thay đường E-stop/gate trực tiếp.
Tham số timer phải >=1; CLEAR_HOLD_CYCLES phải nhỏ hơn CLEAR_CYCLES. Đổi clock
phải đổi toàn bộ timer/PWM cùng lúc, không chỉ CLK_HZ.

## Khi FPGA mất clock hoặc Motion lỗi

Watchdog FPGA không đếm khi mất clock. Motion dùng đồng hồ riêng: từ mẫu mới
CRC đúng, đúng phiên cuối cùng, nếu quá 30 ms thì hạ permit trong 1 ms tiếp.
Sequence snapshot dùng delta modulo16 `0 < delta < 32768`; bản tin lặp/cũ/
đảo thứ tự không làm mới tuổi. Reset/session mới phải quay về quy trình ARM.
Mô hình test phát lại metadata snapshot cũ ngay cả khi clock FPGA đứng để
kiểm tra bộ giám sát Motion. Motion 0.1 đã thực hiện trong core/ESP-IDF;
co-sim kiểm mất clock, chưa đo ngắt GPIO trên board có dây.

Trước ARM, Motion xác nhận hai decoder đã khởi tạo (encoder_status bit2/3)
và snapshot mới. V2 bit0/1 là PERIOD_VALID, khác v1 sticky invalid.
V2 fault&0x8800 cần reset FPGA; cảnh báo encoder/RX sticky khác không tự
khóa. Motion 0.1 dùng timeout không xung theo tốc độ/độ phân giải riêng; chưa PID.

Lease Brain hết, PID/cảm biến lỗi phải làm Motion ngừng CMD và hạ permit;
không để tác vụ UART tự phát lại duty. GPIO permit tĩnh chưa chống mọi lỗi
treo MCU/lỗi chung: watchdog phần cứng ngoài còn phải xét theo thiết kế điện.
Driver disable có thể thả trôi; quãng dừng tiến/lùi/quay phải thử riêng. Chưa có
nghiệm thu mạch gate/driver, PCB, PnR/STA hoặc bằng chứng chạy motor thật.
RTL adapter DRV8833 đã có trong nhánh FPGA; không thay mạch gate ngoài.

## DỪNG bình thường — hai đường permit

Motion 0.1 hạ driver_permit ngay, gửi DISABLE hợp lệ, chờ STATUS DISARMED
trong 30ms rồi mới hạ logical motion_permit. Giữ nguyên guard lost-permit của
RTL; không bỏ guard để tránh FAULT. Nếu timeout/lỗi vật lý/control stall thì
hạ cả hai ngay và chốt lỗi, không chờ UART. CLEAR chỉ làm khi cả hai LOW.
Không dùng chính GPIO logic tới FPGA làm đường gate duy nhất ở cách ghép này.
