# Kiểm thử

Hiện có test công cụ kiểm tra kho: README thư mục, snapshot đã stage, file ignore,
tên nhánh và hook chặn commit/push vào main. Test dùng kho Git tạm, không push
lên GitHub. Chạy bằng `python -m unittest discover -s tests`.
Kiểm tra đuôi HDL bắt buộc `.sv` cho cả RTL/testbench, cả worktree và index;
netlist trong build đã ignore không bị áp quy tắc nguồn.

Chưa có test firmware/phần cứng. Khi thêm tính năng, đặt test tương ứng tại đây
hoặc trong project MCU nếu bộ test ESP-IDF yêu cầu, rồi ghi lệnh chạy thực tế.

`test_fpga_runner.py` kiểm tra runner không bỏ qua compile lỗi, mã lỗi simulator
hoặc timeout; kiểm tra đường dẫn tool tương đối và môi trường subprocess.
Đồng thời kiểm tra compiler nhận đủ nguồn `.sv` và tùy chọn SystemVerilog.
Test RTL thực nằm ở [fpga/tb](../fpga/tb/README.md), chạy riêng
bằng `python tools/run_fpga_tests.py` và được yêu cầu trong CI.
