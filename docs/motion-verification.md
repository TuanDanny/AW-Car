# Bằng chứng Motion 0.1

Triển khai theo quyết định 03/11/2026, chốt báo cáo 04/11/2026. Nhánh
`codex/esp32-s3-motion` từ main `094b37c`.
Brain PR #13 giữ draft. [Contract](motion-plan.md),
[firmware](../firmware/motion/README.md), [dây/gate](../hardware/motion-wiring.md).
Không merge main; không đưa CAD hoặc toàn bộ RTL/Brain vào nhánh Motion.

## Kết quả và phạm vi

| Lớp | Bằng chứng đạt | Giới hạn |
| --- | --- | --- |
| Core/codec | 38 test Motion, gồm 1.000 vector duty/direction; root 71 test | Chính C++ firmware, thời gian host |
| Brain | Root 84 Python, 3 Node test, không skip | Không thay Safari/âm thanh/backend thật |
| Hai lõi | 5 nhóm Manual/AI/ARM/STOP/CLEAR/mất cloud bằng hai core C++ | FPGA peer Python, 1.035s giả lập |
| RTL | aw_car_top 27MHz, nguồn 7ab91b2, 430ms mô phỏng | Không phải PnR/STA hoặc chân điện |
| ESP-IDF | Motion 0.1.0 LOCKED và profile enabled build/merge; Brain AW-Car/stock build | Chỉ nạp Motion LOCKED, Brain mới chưa nạp |
| COM7 | S3 rev0.2/flash16MB/PSRAM8MB; backup16MB, flash0x0000, console/NVS/GPIO LOW | Chưa nối UART/gate/motor |

### Chức năng đã kiểm chứng

- Sáu hướng, tốc độ có dấu, bão hòa giữ tỷ lệ, neutral giữ ARM, STOP bỏ ARM.
- Kích tuyến tính 200ms sau nghỉ, vùng thấp giảm boost, bên duty0 giữ0;
  lệnh20Hz không khởi động lại cú kích, nhả/hết hành động AI hủy ngay.
- Đổi chiều coast cả hai, giữ mục tiêu mới nhất, chờ chậm hoặc yên xung;
  quá hạn1500ms chốt lỗi, không tự đảo. Không xung khi có duty dừng cả xe.
- Lease đúng deadline, TTL/range/source/session/sequence/wrap, CRC/length/
  version/nhiễu/thiếu byte. Frame lỗi không được tạo quyền hoặc gia hạn.
- STATUS cũ/lặp/đứng, mất FPGA và control stall hạ quyền độc lập Brain.
  Diagnostic warning không tự khóa; mask0x8800 đòi reset FPGA.
- CLEAR về DISARMED, hủy context; ARM mới đòi HELLO mới. STOP lặp không
  kéo dài hạn DISABLE. STOP ở idle không có FPGA không sinh FAULT giả.
- Cấu hình sai/đang chạy bị từ chối. Firmware LOCKED không thể mở bằng USB.

Ghép hai lõi phát hiện ACK HELLO/STOP bị lỗi chốt ghi đè mỗi tick, khiến
phục hồi bất đồng bộ thất bại. Đã sửa và hồi quy có tick giữa HELLO/CLEAR.
Brain còn đợi đúng ACK STOP trước HELLO, tránh epoch flush nuốt phiên mới.

Co-sim qua bit UART/GPIO kiểm boot/STATUS v2, ARM_PENDING/wake, PWM vi sai,
DỪNG không lost-permit fault, FPGA mất clock được Motion ngắt độc lập và
CLEAR không ARM. Report giữ SHA256 mọi RTL; nhánh FPGA không bị sửa.

Core Motion local digest `e87c3de279a28d70`; Brain `8c48f5e0e849` tại
commit `dacf1434a61cfb16e2c01f277473de3623575669`. FPGA peer
`7ab91b2d6119af211453a1273e3dae978d8af286`. Digest là hash nguồn host local,
không phải mã commit. Hai giao thức dùng version riêng; không fallback v1.

## Board và artifact

COM7 qua CH343; sao lưu flash gốc đủ16.777.216 byte trước lần ghi đầu.
Lần cuối esptool kiểm hash sau ghi; checker reset, thử tham số sai, set/save/
load/defaults và STOP không FPGA, sau đó lưu defaults. 11 mẫu đều DISARMED,
fault0, logical/driver GPIO đọc về0, queue/tx drops0. Heap free357208 byte,
minimum352932, control stack free tối thiểu4800 byte trong cửa kiểm tra.
Không có panic/assert/watchdog. Đây là thử console/default-off, chưa đo pin
bằng oscilloscope hoặc kiểm đáp ứng ISR với kích thích ngoài.

| Artifact Motion LOCKED local | SHA-256 |
| --- | --- |
| firmware/motion/build/merged-binary.bin, offset0x0000 | `1c2fa8d954dc677d61af6a0c8f48d8b89ceed8fa6f6af54a41cd4531d1eaaa3c` |
| firmware/motion/build/aw_car_motion.elf | `afb39ece68b603819af3ab5877e25f6658cbff4499c77ba58159e56ff5d5b7a8` |

Signed v/omega và pin invalid; latency không có mẫu là null, không gọi là0us.
Backup gốc/raw flash ở build/board-motion-20261103-initial, kiểm tra cuối ở
build/board-motion-20261103-final. Tất cả ignored/private, không upload.

## Soak, CI và giao diện

Bài soak chức năng 30 phút/36.000 lệnh trên core digest cuối không fault.
Report phân biệt wall-time với thời gian giả lập và giữ history/status256.
Bộ đo RSS ban đầu tạo lại kiểu ctypes mỗi mẫu gây tăng RAM của chính bộ đo;
đã sửa tạo kiểu/hàm một lần. Số RAM từ lượt cũ không dùng để kết luận leak.
Lượt paced cuối với bộ đo sửa **đã đạt**, report local ignored ở
build/motion/soak-verified-memory.json:

| Chỉ số host | Kết quả |
| --- | ---: |
| Wall-time / thời gian mô phỏng | 1800.007s / 1800s |
| Lệnh / bước điều khiển / fault | 36,000 / 1,800,000 / 0 |
| Nhận lệnh + core step + mock TX p50 / p95 / p99 | 75.8 / 173.3 / 280.4µs |
| Max của cùng phép đo | 9721.2µs |
| RSS process Python+C++, min–max | 19.35–21.34MiB |
| RSS trong 5 phút cuối, min–max | 21.06–21.34MiB |
| Mẫu RAM / history / status capacity | 1800 / 256 / 256 |

RAM này gồm deque latency và danh sách mẫu của công cụ PC; không phải heap
ESP32. Không lấy max/p95 host làm số đo UART/FreeRTOS hoặc thời gian motor.
Native binary SHA256 `fe176e6b84c4bb7ceb5a60a25462f7677d6f52f54c8b9cbc082a0bc32ba2773f`;
harness SHA256 `7cb62ad7f638d8785848f1e2fc41327da32a0e0ee902151b2d11fabc6378e1f8`.
Lõi firmware không đổi trong lượt soak; report/hash khớp nguồn cuối.

Computer use với cùng asset/C++ Brain đã thử FAULT→Xóa lỗi→DISARMED, chưa ARM;
socket đóng khi ARMED giả lập xóa nhãn quyền và khóa nút. Viewport hẹp không
tràn ngang, không JS error. Ảnh và chi tiết ở
[nhánh Brain](https://github.com/TuanDanny/AW-Car/blob/feat/f03-xiaozhi-ai/docs/brain-motion-clear-verification.md),
không phải dashboard trên xe.

CI Motion thêm job ghép hai core/RTL với commit peer cố định và smoke load
30s thời gian ảo; không gọi smoke là endurance. Ba job của
[CI code Motion 774052e](https://github.com/TuanDanny/AW-Car/actions/runs/41679151855)
đều đạt: structure-and-rules, motion-peer-integration và fpga-simulation.
[CI Brain 545f5ae](https://github.com/TuanDanny/AW-Car/actions/runs/41679580448)
cũng đạt; commit Brain này chỉ bổ sung tài liệu so với peer dacf143 đã pin. Build ESP-IDF được thực hiện
cục bộ, không coi CI cấu trúc thay build MCU. Các test CLI Xiaozhi gốc chạy
trên Windows có11 lỗi harness (xóa thư mục tạm đang là cwd/chạy entrypoint
POSIX),1 skip; nhóm CLI này đạt trên Ubuntu trong CI Brain ở cùng commit.
Không sửa vendor CLI trong mốc Motion, không tính nhóm đó vào84 root tests.

## Chưa nghiệm thu

UART thật hai ESP/FPGA; reset đơn từng board; pin/bank/CST/timing Nano9K;
gate/E-stop/chốt lỗi, nguồn/nSLEEP/encoder/cực motor; dòng/nhiệt/kích100%/
đảo/quãng dừng. Chưa có PID, ToF/TCRT5000/IMU hoặc chống rơi/vật cản.
Mục tiêu latency p95<=2ms/p99<=5ms của Motion phải đo lại trên ESP32 có UART;
phân vị host không phải latency xe. Cần ghép/nâng bánh trước khi thử dưới sàn.

## Bổ sung04/11: monitor UART hai board

Thêm console chỉ đọc `uart`, bộ đếm byte/frame/error/TX tách Brain/FPGA,
tránh quy toàn bộ `rx_errors` tổng cho dây Brain. Build ESP-IDF6.1 đạt;
nạp COM7 tại0x0000, hash xác nhận, NVS và motioncfg giữ nguyên theo byte.
Các mẫu mới UART1 TX17/RX18 báo baud115201 (cấu hình115200), parser errors
có tăng; UART2 TX15/RX16 không có byte/lỗi. Driver vẫn LOCKED và hai GPIO
permit LOW. Không nới CRC/timeout hoặc giả safety input để cho ARM.

Người dùng đo và xác nhận GPIO17/18 trên Motion bị chập, đang ngắt nguồn
sửa. Tạm dừng board test, chưa xác nhận thông liên kết sau sửa. Còn phải đo
STATUS20Hz/age<150ms và HELLO/STOP/ARM reject hai chiều. Raw log/flash backup
chỉ giữ trong build ignored; không đưa vào PR.
