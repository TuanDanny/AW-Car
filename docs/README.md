# Tài liệu

Lưu yêu cầu, quyết định kỹ thuật và kết quả thử nghiệm.

- [AP+STA, WebSocket và dashboard tối giản](brain-network-reliability.md):
  reconnect có backoff, log đóng kết nối, STOP gộp và phép đo COM3/COM7.

- [Xóa lỗi Motion trên dashboard](brain-motion-clear-verification.md): ACK phục hồi,
  UI hẹp/mất socket và bằng chứng browser; chưa nạp lại Brain.
- [Bằng chứng Brain/dashboard](brain-dashboard-verification.md): bản Manual/AI,
  C++ host, WebSocket, firmware build, soak và giới hạn nghiệm thu phần cứng.

- [Rà soát issue #1](issue-1-technical-review.md): kiến trúc, lỗi thiết kế cần
  tránh, phạm vi 1 mic và lộ trình nghiệm thu; ghi chú F01 về giữ tốc độ,
  kích đề-pa, quãng đường và mã Gray.
- [Quy trình Git](workflow.md): nhánh tính năng, squash merge và bảo vệ main.
- [Kế hoạch FPGA và toàn hệ thống](fpga-drive-plan.md): quyết định mới nhất,
  FPGA phát PWM motor, phân tải, công cụ và các điều kiện nghiệm thu.
- [Thiết kế và kiểm thử RTL](fpga-rtl-design-test-plan.md): module, ca thử,
  luồng Icarus/Gowin không cần Quartus và điều kiện chọn board trước khi mua.

Quy tắc dành cho agent nằm ở [AGENTS.md](../AGENTS.md); không sao chép thành
nhiều bộ quy tắc khác nhau.
