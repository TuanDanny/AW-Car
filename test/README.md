# Kiểm thử simplev1

`python -m unittest discover -s test` chạy kiểm tra cấu trúc/vector và native core.
`host_tests.cpp` dùng đúng source shared của firmware. Browser và RTL kiểm riêng.
Giả lập không chứng minh Wi-Fi/audio/timing FreeRTOS hoặc motor thật.

`test_ota_image.py` kiểm role/chip/project/hash trước upload. Ca lỗi receiver/reset
và rollback phải thử board thật bằng utils/test_ota_receiver.py và bản test health;
không đánh dấu đạt từ cấu hình bootloader hoặc mô phỏng.
