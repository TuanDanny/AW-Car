# Workflows

`ci.yml` chạy trên PR vào main và khi main nhận thay đổi: kiểm tra README,
quy tắc tên nhánh PR và test công cụ bằng Python. Job `fpga-simulation` cài
Icarus/Yosys trên Ubuntu24.04 rồi chạy
`python tools/run_fpga_tests.py --full-timing --timeout 1800` và bốn script
tổng hợp trong `fpga/`, gồm top hoàn chỉnh. Bài top dài chạy>=2s tại27MHz; compile, testbench lỗi, timeout hoặc lỗi
`check -assert` đều làm CI thất bại. Version được in trong log.

Gowin mapping generic chưa phải báo cáo fit/timing sau route trên chip cụ thể.

Khi có firmware/Dashboard, thêm job build/test tương ứng; job cấu trúc đạt
không chứng minh tính năng xe đã hoạt động.
