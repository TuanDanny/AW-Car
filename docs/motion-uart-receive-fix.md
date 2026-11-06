# Sửa UART và phục hồi FPGA — 06/11/2026

Nhánh `codex/esp32-s3-motion`, nền `7a45fad` đã fast-forward từ remote có sẵn.
Ba lỗi phần mềm được sửa trong runtime/codec/link Motion. Brain và RTL FPGA
không đổi. Motion COM7 vẫn `ENABLE_DRIVER=n`, `validated=0`; gate/E-stop chưa
có, không thử motor. [Số đo và hash](motion-uart-receive-fix-report.json).

## Ba nguyên nhân

1. **Timeout parser giả do read có chờ.** Bản chỉ thêm chẩn đoán, giữ vòng
   nhận cũ, ghi 4 timeout/230,202s; header/CRC/HW errors đều0. Lỗi đầu:8byte,
   gap2.005µs, tuổi frame2.040µs. Lỗi cuối:32byte, gap2.003µs, tuổi4.014µs.
   SDK6.1 `uart_read_bytes` lặp `xRingbufferReceiveUpTo`, áp lại timeout cho
   từng item đến khi đủ length. Đọc64byte với1tick có thể giữ byte đã nhận
   quá hạn2ms của parser trước khi feed. Nay chờ ISR event tối đa1tick rồi
   đọc timeout0; kiểm epoch/generation sau chờ, hủy partial/flush trước context
   mới. Flush context thất bại khóa driver và báo Internal. Không backdate
   thời gian hoặc nới parser2ms/6ms.
2. **Bỏ nhầm event mới do dùng đồng hồ đầu vòng.** RX có thể enqueue sau khi
   control lấy `now` đầu vòng; lúc dequeue, `event.at > now` bị hiểu nhầm là
   dữ liệu tương lai. Nay lấy đồng hồ đơn điệu sau từng dequeue và trước Tick
   cuối. Vẫn từ chối dữ liệu tương lai thật và tuổi>=10ms. Lượt chỉ sửa read
   hết parser timeout nhưng queue_drops14→164/445,505s; được giữ là bản
   **chưa đạt**, không dùng làm bằng chứng hoàn tất.
3. **Không nhận lại FPGA ở một số pha counter sau reset.** Seq16bit và
   timestamp32bit có chu kỳ wrap khác nhau; hiệu so với mẫu trước reset không
   đủ nhận diện reboot. Khi Idle/Faulted, permitLOW, STATUS cũ stale và session0,
   link cần hai candidate seq/timestamp cùng tiến, cách nhau<30ms rồi mới
   rebaseline. Duplicate/thưa>=30ms không làm mới tuổi. Fault đã chốt vẫn giữ;
   Begin/Stop hoặc mới chuyển Faulted hủy candidate. Session0 không duy trì
   freshness/ARM của một phiên đang hoạt động.

Chẩn đoán parser dùng counter bounded và context reject gần nhất; mirror
một snapshot nhỏ trong critical section riêng chỉ khi lỗi đổi. Console copy
snapshot rồi mới printf, không trộn hai lần reject và không I/O/cấp phát trong
RX. Không thêm task, dependency hay ghi NVS định kỳ.

## Kiểm chứng

- Production parser C++ được đối chiếu vector/CRC Python; test giữ hạn2ms/6ms,
  partial timeout, phân loại lỗi và phục hồi. Các regression core bao phủ
  counter reboot ở nhiều pha, duplicate/sparse, biên29.999/30.000µs, fault
  latched và session0 bị từ chối khi đang ARM.
- Root:147 tests,134 đạt,13 Web tests skip do Python hiện tại thiếu dependency
  trong dashboard requirements. Không gọi các ca skip là đạt. Repo checker
  và diff check chạy riêng.
- Hai core Brain/Motion C++:5 checks đạt; Motion+RTL thực27MHz co-sim:6 checks
  được chạy lại trên source sửa link. Đây là giả lập, không đo Wi-Fi/FreeRTOS.
- Bản read0+đồng hồ sau dequeue:83.083 frame mới/830,838s,99,999Hz;
  parser/HW/queue/TX/log drops0 trong167 mẫu console. Heap ổn định350.284byte.
  Bản này chưa có fix reboot; kết quả của bản cuối ghi riêng trong JSON.
- Bản cuối đã build ESP-IDF6.1 và nạp COM7 tại0x0/0x8000/0x10000. Không flash
  merged padding qua NVS. Đọc NVS/PHY và motioncfg so từng byte với backup:
  không đổi. App/source hash, log và binary nằm trong build ignored.

Bản cuối:62.072 frame mới/620,725s trước reconfigure, parser/HW/queue/TX/log
drops0; mọi mẫu STATUS fresh, driver/logical GPIO và duty0. Heap350.268byte
ổn định. Brain age trong JSON; counter UART cũ1 không tăng trong lượt ổn định,
không thay số tích lũy bằng0. Những lần reset tiếp theo có phase riêng:

- Ghi lại đúng image FPGA/op5: fresh=false rồi true, snapshot khởi động lại,
  fault Gate1 vẫn chốt và driver/duty0.
- Giữ Motion reset8s: Brain telemetry age tới6.510ms, STATUS dừng rồi tiếp
  tục sau boot. Không tự ARM.
- Reset Brain qua USB: có boot mới, STATUS Motion nhận lại dưới150ms.
- Reprogram FPGA từ Flash ở pha counter sau: snapshot14.130→354, fresh phục
  hồi trong mẫu kế; một partial33byte bị timeout trong cửa sổ reset
  (gap109.541µs, tuổi111.848µs). Parser hủy frame dở và nhận lại frame mới.
  Không coi lỗi reset này là lỗi trong lượt ổn định hoặc che bằng xóa counter.

Sau reset, theo dõi65,080s/14mẫu Motion: parser counter giữ1, HW/queue/TX
drops0, fresh/permit đúng; không có chữ ký panic/brownout trong log thu được.
Monitor đã đóng, dây và ba board giữ kết nối đầy đủ.

JSON chứa timeline đã lọc, kết quả sau phục hồi và hash log khi đã đóng
monitor. Console lấy mẫu5s nên không suy thời gian phát hiện chính xác từ
một mẫu false/true hoặc từ giới hạn150ms ở mẫu cuối.

## Giữ nguyên ranh giới an toàn

Ba board USB, GND chung; BrainTX17→MotionRX14, MotionTX13→BrainRX18;
MotionTX15→TangRX25, TangTX26→MotionRX16. GPIO17/18 Motion hỏng không dùng.
UART115200, RX priority18/core0, threshold8/idle2, CRC/session/sequence, lease,
watchdog và mask fatal0x8800 giữ nguyên. FPGA fault0x0002 do thiếu gate và
Motion Gate fault1/đỏ là đúng; UART tốt không tự CLEAR/ARM hoặc đổi màu thành
sẵn sàng. Các mẫu driver/logical permit và duty phải luôn0.

Log console/PC không chứng minh deadline cắt pad vật lý, không thấy được xung
ngắn và không thay logic analyzer. Chưa nghiệm thu ARMED/gate/E-stop/encoder/
PWM công suất/motor. Chưa có dashboard client trong các lượt đo UART này;
không gọi chúng là nghiệm thu Web/AP+STA mới.

SDK đối chiếu trực tiếp tại
`C:/Espressif/frameworks/esp-idf-v6.1/components/esp_driver_uart/src/uart.c`.
Raw console có thể chứa thông tin mạng nên giữ private trong
`build/uart-parser-fix-20261106/`; chỉ commit số liệu lọc và SHA256. Không push
hoặc merge main trong lượt sửa này.
