# AW-Car

Xe TT 4WD dùng **hai ESP32-S3, Tang Nano 9K và một INMP441**. Hai nhóm
motor trái/phải lái bằng chênh lệch tốc độ, không có servo lái. Brain phụ trách
Xiaozhi, Web, OLED I²C và âm thanh; Motion giữ quyền truyền động; FPGA đọc
encoder một OUT mỗi bên và phát PWM. DoA dành cho nâng cấp.

Tác giả: **TuanDanny**. Cộng tác viên: **Minh Nho** và **Nhan Duc**.

## Trạng thái mốc 03–04/11/2026

Đây là nhánh **codex/esp32-s3-motion**, tạo từ main `094b37c`. Motion 0.1 có
hai UART, vòng hở, kích đề-pa, chờ đảo chiều, lease và khóa driver độc lập.
Đã build ESP-IDF 6.1 và thử console/NVS/đầu ra mặc định LOW trên COM7.
**Bản nạp mặc định khóa driver, từ chối ARM.** PID và cảm biến để mốc tiếp.

Brain/dashboard phát triển riêng ở `feat/f03-xiaozhi-ai`, PR #13 giữ draft;
mic/OLED/RGB và Safari đã được thử trước đó. Bản Brain đã nạp lại COM3 để chẩn đoán mạng/UART. Ngày04/11 xác nhận
GPIO17/18 trên Motion thông0–5Ω cả hai chiều khi rút nguồn/dây. Đã đổi
UART Brain sang MotionTX13/RX14 (BrainRX18/TX17), nạp COM7 và kiểm tra
UART hai chiều~20Hz/0lỗi; monitor210s với Android STOP/Cho phép đạt. Console
`uart` có bộ đếm riêng hai peer.

**RTL trong nền main của checkout này còn bản cũ.** Motion yêu cầu protocol
v2/encoder một OUT của `feat/f01-fpga-drive` (`7ab91b2` trong lần co-sim),
không tự fallback v1. Không lấy RTL baseline ở checkout này để nạp ghép.
Tang Nano 9K đã có; chưa nghiệm thu CST/PnR/STA hoặc UART/gate/motor thật.

- [Kế hoạch Motion](docs/motion-plan.md), [bằng chứng kiểm thử](docs/motion-verification.md).
- [Đấu nối và gate](hardware/motion-wiring.md), [BM-v1](firmware/shared/brain-motion-protocol.md),
  [Motion–FPGA v2](firmware/shared/fpga-protocol-v2.md).
- [Issue #1](https://github.com/TuanDanny/AW-Car/issues/1) và
  [kế hoạch toàn hệ thống](docs/fpga-drive-plan.md).

## Cấu trúc

| Thư mục | Nội dung |
| --- | --- |
| [firmware/brain](firmware/brain/README.md) | Brain/Xiaozhi, phát triển ở nhánh AI |
| [firmware/motion](firmware/motion/README.md) | ESP-IDF, core C++ và adapter FreeRTOS/UART/GPIO |
| [firmware/shared](firmware/shared/README.md) | Codec và hợp đồng hai liên kết UART |
| [fpga](fpga/README.md) | RTL baseline; bản v2 triển khai ở nhánh FPGA |
| [dashboard](dashboard/README.md) | Giao diện ở nhánh AI |
| [hardware](hardware/README.md) | Nguồn, cơ khí và bảng dây |
| [docs](docs/README.md) | Kế hoạch và bằng chứng |
| [tests](tests/README.md) | Host/regression/co-sim |
| [tools](tools/README.md) | Công cụ kiểm tra, giả lập và board |

## Kiểm tra và làm việc

Ba nhánh theo [AGENTS.md](AGENTS.md) và [quy trình Git](docs/workflow.md).
Giữ main ổn định; PR chỉ squash merge sau nghiệm thu, không tự merge mốc này.

```sh
git config --local core.hooksPath .githooks
python tools/check_repo.py
python -m unittest discover -s tests
git diff --check
```

Host tests cần compiler C++17 (`g++`/`clang++`, hoặc biến `CXX`). Build MCU,
co-sim và board check có hướng dẫn riêng tại README Motion. Thử phần mềm
không thay phép đo Wi-Fi/RTOS/I²S/GPIO/dòng motor hoặc quãng dừng trên xe.

Motion ngắt driver độc lập khi Brain/FPGA mất liên kết. Gate/E-stop phải tắt
được khi MCU hoặc clock FPGA hỏng; không dùng UART làm đường E-stop duy nhất.
Chỉ tiến tới PID/cảm biến sau khi Manual local, hướng quay và dừng đã đạt.
