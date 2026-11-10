# Mốc skeleton simplev1 đã được duyệt

Ngày10/11/2026, chủ dự án duyệt giữ source đang chạy làm nền cho các cải tiến sau.
Nhánh: `simplev1`; theo yêu cầu tiếp, cùng nội dung được đưa lên **main prototype v1**.
Mốc phục hồi: **`simplev1-skeleton-v1`** và **`prototype-v1`**. Chỉ giữ main/simplev1;
nhánh cũ lưu phục hồi cục bộ trước khi xóa. Lịch sử commit trước vẫn được giữ.

## Cấu trúc và hành vi giữ làm nền

- Motion: AP/Web Manual/AI, phân xử, UART tới Brain, SPI tới FPGA và STBY haiDRV.
- Brain: Xiaozhi tiếng Trung, mic, loa và OLED; không host dashboard.
- FPGA: SPI1MHz, PWM20kHz, encoder mộtOUT và timeout; clock27MHz.
- Manual bốn hướng; nhả về0, DỪNG về0/Manual, mất lệnh về0. Không PIN/ARM cũ.
- AI có thời lượng, lệnh mới thay cũ; tốc độ riêng từng lệnh, mặc định30%.
  Không lưu mức tốc độ của câu trước. PID giữ tắt.

## Đối chiếu source với bản đang chạy

| Board | Build / mã nhận dạng |
| --- | --- |
| Brain | `simplev1-e8adbccbfcf0` |
| Motion | `simplev1-3196afc4efb1` |
| Tang Nano9K | UserCode `0x0000A6C1`, đã lưu/reload embedded Flash |

Đã tính lại build ID từ source haiESP, kiểm SHA image với manifest và kết quả
readback đã lưu. Chín file RTL/constraints/build target đối chiếu hash với bản
Gowin đã tạo bitstream. Không nạp lại hoặc reset board để tạo mốc này.
Hash và phạm vi kiểm chứng ở [manifest baseline](../data/skeleton-baseline.json).

## Phạm vi được nghiệm thu

- Manual đủ bốn hướng, log và Web khớp; DMM cầuB haiDRV đúng cực tính ở100%, VM USB
  khoảng5V, chưa motor. Người dùng xác nhận đã thử AI và đo điện áp hoạt động đúng;
  không có bộ số đo điện áp riêng cho từng câu thoại.
- Log AI bản cuối có tiến/lùi/quay trái/quay phải; tiến60/80/100% tương ứng
  duty810/1080/1350. Lệnh tiếp không nêu tốc độ trở về30%, đúng contract.
- OLED/mic/loa/BOOT/Web nghe đã thử; sửa vòng UART chờ0tick, cửa sổ theo dõi10phút
  sau sửa không watchdog/panic. Test host, browser, RTL và Gowin ở báo cáo chi tiết.
- Source nền chứa mã là commit `f515995b8ca0017b693123aae449be80d47f0c94`.
  Commit chốt mốc bổ sung tài liệu/bằng chứng, CI và kiểm tra workspace; không sửa
  firmware, RTL hay wiring.

Đây là nền đã nghiệm thu **trên bàn**, chưa phải nghiệm thu xe chạy motor/pin2S,
PID hay PCB. Các giới hạn, frame SPI lẻ bị loại và phép đo còn thiếu giữ nguyên
trong [verification.md](verification.md). Không di chuyển tag baseline khi nâng cấp.
Xem [câu lệnh thoại](voice-commands.md), [build/nạp](build.md) và
[đấu nối](../schematic/README.md) để tái sử dụng mốc.
