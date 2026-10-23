# Kiểm thử

Hiện có test công cụ kiểm tra kho: README thư mục, snapshot đã stage, file ignore,
tên nhánh và hook chặn commit/push vào main. Test dùng kho Git tạm, không push
lên GitHub. Chạy bằng `python -m unittest discover -s tests`.

Chưa có test firmware/phần cứng. Khi thêm tính năng, đặt test tương ứng tại đây
hoặc trong project MCU nếu bộ test ESP-IDF yêu cầu, rồi ghi lệnh chạy thực tế.

`test_fpga_runner.py` kiểm tra runner không bỏ qua compile lỗi, mã lỗi simulator
hoặc timeout. Test RTL thực nằm ở [fpga/tb](../fpga/tb/README.md), chạy riêng
bằng `python tools/run_fpga_tests.py` và được yêu cầu trong CI.
