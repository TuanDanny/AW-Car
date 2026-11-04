# Kiểm thử

`test_status_indicator.py` compile policy C++ chung hai board: ưu tiên lỗi,
mask diagnostic, chờ LOCKED/FPGA/gate, cache chỉ ghi khi màu đổi và retry1s.
Đây là test phần mềm, màu vật lý/build được ghi trong docs/motion-verification.md.

Hiện có test công cụ kiểm tra kho: README thư mục, snapshot đã stage, file ignore,
tên nhánh và hook chặn commit/push vào main. Test dùng kho Git tạm, không push
lên GitHub. Chạy bằng `python -m unittest discover -s tests`.
Kiểm tra đuôi HDL bắt buộc `.sv` cho cả RTL/testbench, cả worktree và index;
netlist trong build đã ignore không bị áp quy tắc nguồn.

`test_motion_core.py` chạy chính lõi C++ firmware: sáu hướng, kích theo tỷ lệ,
chờ đảo, encoder không xung, STOP/lease/phiên/sequence, fault/recovery và cấu
hình. `test_motion_codec.py` đối chiếu reference Python, golden v2, 1.000
vector ngẫu nhiên và frame lỗi. Cần compiler C++17 hoặc biến môi trường CXX.

`motion_cosim.sv` là fixture ghép core Motion với `aw_car_top` từ checkout
FPGA v2 riêng qua bit UART/GPIO. Chạy bằng `tools/motion_rtl_cosim.py`; không
thêm fixture này vào danh sách RTL triển khai. Host/RTL chưa thay test board.

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
