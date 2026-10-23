# Workflows

`ci.yml` chạy trên PR vào main và khi main nhận thay đổi: kiểm tra README,
quy tắc tên nhánh PR và test công cụ bằng Python. Job `fpga-simulation` cài
Icarus trên Ubuntu 24.04 rồi chạy `python tools/run_fpga_tests.py`; compile,
testbench lỗi hoặc timeout đều làm CI thất bại. Version được in trong log.

Khi có firmware/Dashboard, thêm job build/test tương ứng; job cấu trúc đạt
không chứng minh tính năng xe đã hoạt động.
