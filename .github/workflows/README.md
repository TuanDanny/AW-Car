# Workflows

`ci.yml` chạy trên PR vào main và khi main nhận thay đổi: kiểm tra README,
quy tắc tên nhánh PR và test công cụ bằng Python. Job `fpga-simulation` cài
Icarus/Yosys trên Ubuntu24.04 rồi chạy
`python tools/run_fpga_tests.py --full-timing --timeout 1800` và bốn script
tổng hợp trong `fpga/`, gồm top hoàn chỉnh. Bài top dài chạy>=2s tại27MHz; compile, testbench lỗi, timeout hoặc lỗi
`check -assert` đều làm CI thất bại. Version được in trong log.

Gowin mapping generic chưa phải báo cáo fit/timing sau route trên chip cụ thể.

`brain.yml` chạy khi nhánh feat/f03-xiaozhi-ai nhận thay đổi Brain/workflow,
hoặc PR tương ứng vào main. Job xiaozhi-host-tests chạy bộ kiểm thử công cụ
build/release của Xiaozhi bằng Python 3.13 trên Ubuntu24.04. Đây chưa phải
compile ESP-IDF hoặc kiểm thử runtime của ESP32.

Job cấu trúc hoặc host test đạt không chứng minh tính năng xe đã hoạt động.
