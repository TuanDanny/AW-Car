# AW-Car simplev1

Yêu cầu được duyệt ngày 10/11/2026 thay thế kiến trúc cũ **chỉ trên nhánh simplev1**.

- Workspace: D:/Project/AW-Car/simplev1; không sửa/xóa worktree khác.
- Brain: Xiaozhi + mic/loa/OLED, STA-only. Motion: AP/Web + phân xử + SPI + PID tắt mặc định.
- FPGA: SPI mode 0/1 MHz, PWM 20 kHz, encoder một OUT, clock 27 MHz. HDL chỉ .sv.
- Không PIN, ARM, validated, CLEAR_FAULT, Gate handshake hay lỗi chốt. Boot/STOP/timeout về 0.
- STOP ưu tiên, về Manual; nói chuyện độc lập. Mode/STOP đổi generation; không chạy lại lệnh cũ.
- Manual timeout 500 ms; AI 100–3000 ms, mặc định 1000 ms. PID chờ đủ encoder và hiệu chuẩn.
- Contract duy nhất: docs/protocol.md và esp/shared/include/simple/protocol.hpp.
- Không mở COM/JTAG hoặc nạp khi phiên khác đang sở hữu cổng. VM motor ngắt trước đổi firmware/dây.
- Không commit NVS, mật khẩu Internet, PIN, flash dump, build, log thô. Giữ LICENSE và dependency lock.
- Trước commit: python utils/check_repo.py; python -m unittest discover -s test; git diff --check;
  build cả hai firmware, mô phỏng RTL và Gowin đúng phần đổi. Ghi rõ phép thử chưa thực hiện.
- Mỗi thư mục nguồn có README. Push riêng simplev1 sau kiểm tra; không merge main.
