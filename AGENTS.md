# AW-Car simplev1

- Ngoại lệ được người dùng giao10/11/2026: phát triển AP+STA/OTA trên
  `codex/simplev1-ota` tại D:/Project/AW-Car-ota; áp dụng docs/ota-network-plan.md.
  Manual chỉ AP192.168.4.1; router chỉ Xiaozhi/OTA/log. Yêu cầu tiếp10/11:
  đẩy source đã nghiệm thu lên origin và cập nhật main qua PR/squash sau CI;
  CI phải chạy lại trên main rồi đồng bộ simplev1. Giữ tag baseline và lịch sử,
  không force-push. Mốc hiện hành ở docs/current-release.md.

Yêu cầu được duyệt ngày 10/11/2026 thay thế kiến trúc cũ **chỉ trên nhánh simplev1**.

- Theo yêu cầu10/11/2026: chỉ giữ nhánh main (prototype v1) và simplev1 (skeleton).
  Workspace main: D:/Project/AW-Car; worktree simplev1: D:/Project/AW-Car/simplev1.
  Nhánh cũ được lưu phục hồi cục bộ rồi xóa local/remote; giữ file các worktree cũ.
- Brain: Xiaozhi + mic/loa/OLED, STA-only. Motion: AP/Web + phân xử + SPI + PID tắt mặc định.
- FPGA: SPI mode 0/1 MHz, PWM 20 kHz, encoder một OUT, clock 27 MHz. HDL chỉ .sv.
- Không PIN, ARM, validated, CLEAR_FAULT, Gate handshake hay lỗi chốt. Boot/STOP/timeout về 0.
- STOP ưu tiên, về Manual; nói chuyện độc lập. Mode/STOP đổi generation; không chạy lại lệnh cũ.
- Manual timeout 500 ms; AI 100–3000 ms, mặc định 3000 ms theo yêu cầu10/11/2026.
  Câu có chỉ định thời gian dùng giá trị riêng; PID chờ đủ encoder và hiệu chuẩn.
- Contract duy nhất: docs/protocol.md và esp/shared/include/simple/protocol.hpp.
- Không mở COM/JTAG hoặc nạp khi phiên khác đang sở hữu cổng. VM motor ngắt trước đổi firmware/dây.
- Không commit NVS, mật khẩu Internet, PIN, flash dump, build, log thô. Giữ LICENSE và dependency lock.
- Trước commit: python utils/check_repo.py; python -m unittest discover -s test; git diff --check;
  build cả hai firmware, mô phỏng RTL và Gowin đúng phần đổi. Ghi rõ phép thử chưa thực hiện.
- Mỗi thư mục nguồn có README. Phát triển trên simplev1; chỉ cập nhật main theo mốc
  được chủ dự án giao. CI chạy trên cả main và simplev1. Không di chuyển tag baseline.
