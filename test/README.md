# Kiểm thử simplev1

`python -m unittest discover -s test` chạy kiểm tra cấu trúc/vector và native core.
`host_tests.cpp` dùng đúng source shared của firmware. Browser và RTL kiểm riêng.
Giả lập không chứng minh Wi-Fi/audio/timing FreeRTOS hoặc motor thật.

`test_motion_primitives_sim.py`: 20 kiểm thử offline; lưới 6.561 tổ hợp ga/rẽ,
quỹ đạo đối chiếu giải tích, giảm bước tích phân, STOP không có đuôi mũ,
refresh 20 Hz không kích đề-pa lại, và phản ví dụ ma sát/độ lệch hai bên.
Chạy bằng Python chuẩn; không cần matplotlib cho unit test.

`test_primitives_native.py`: chạy C++ firmware qua ctypes, đối chiếu 1.111
action/mức ga với số hữu tỷ Python và envelope với hàm mũ Python (dưới1tick).
Kiểm cả timeout/STOP/đổi chiều/wake/bảo trì khi envelope bật bằng thông số test.

`test_ota_image.py` kiểm role/chip/project/hash trước upload. Ca lỗi receiver/reset
và rollback phải thử board thật bằng utils/test_ota_receiver.py và bản test health;
không đánh dấu đạt từ cấu hình bootloader hoặc mô phỏng.
