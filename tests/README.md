# Kiểm thử

Hiện có test công cụ kiểm tra kho: README thư mục, snapshot đã stage, file ignore,
tên nhánh và hook chặn commit/push vào main. Test dùng kho Git tạm, không push
lên GitHub. Chạy bằng `python -m unittest discover -s tests`.
Kiểm tra đuôi HDL bắt buộc `.sv` cho cả RTL/testbench, cả worktree và index;
netlist trong build đã ignore không bị áp quy tắc nguồn.

Brain có kiểm thử phần mềm host, chưa có nghiệm thu phần cứng:

- `test_brain_core.py`: compile và chạy chính lõi C++/VoiceGate của firmware;
  thời gian chủ động, epoch, ARM/STOP, sáu hướng, timeout và lệnh cũ.
- `test_brain_web.py`: HTTP/WebSocket và xác thực với cùng lõi C++; cần
  `dashboard/requirements-dev.txt`. Functional tests dùng clock chủ động;
  bài soak riêng dùng thời gian thực, không nới deadline để che lỗi.
- `test_motion_serial_peer.py`: test peer độc lập Python, UART phân mảnh,
  CRC/resync và lease. Không phải firmware Motion/PID.
- `node --test dashboard/control.test.mjs`: thứ tự giữ/nhả nút và hướng.

Xem [báo cáo Brain/dashboard](../docs/brain-dashboard-verification.md) và
[cách chạy simulator](../dashboard/README.md). Các bài FPGA bên dưới độc lập.

`test_fpga_runner.py` kiểm tra runner không bỏ qua compile lỗi, mã lỗi simulator
hoặc timeout; kiểm tra đường dẫn tool tương đối và môi trường subprocess.
Đồng thời kiểm tra compiler nhận đủ nguồn `.sv`, tùy chọn SystemVerilog và
`--full-timing` thực sự chọn clock danh định cho bài top2s.
Nguồn thử gồm top ở root, module lồng nhiều cấp và helper ngoài `rtl/` để
phát hiện runner bỏ sót thư mục con hoặc lấy nhầm nguồn testbench.
Test thêm registry đủ testbench, inventory module bỏ qua comment/trùng tên,
kiểu module từ VVP, marker PASS, JSON/hash và failure khi module mới chưa có
bài kiểm thử. Module của test lỗi không được tính là đã có bằng chứng PASS.
Test RTL thực nằm ở [fpga/tb](../fpga/tb/README.md), chạy riêng
bằng `python tools/run_fpga_tests.py` và được yêu cầu trong CI.

`test_fpga_protocol.py` kiểm tra layout/endianness, CRC chuẩn và vector Motion–
FPGA chung; reference dùng thư viện Python thay vì gọi lại hàm CRC của RTL.
