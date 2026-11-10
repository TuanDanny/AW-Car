# Quản trị local simplev1

Service HTTPS riêng port3232, chỉ nhận IPv4 STA (gồm IPv4-mapped IPv6).
Không có endpoint lái, không dùng owner WebSocket AP. GET `/info` và `/logs?after=N`
dùng một lớp Bearer token bên trong TLS; CLI chỉ tin đúng chứng chỉ board đã build.
Khóa phát triển riêng cho mỗi vai trò được build tool sinh trong `build/private`;
không in khóa hoặc ghi vào Git. Key ID không phải khóa. Token chỉ đi trong TLS.

Ring32 mẫu trạng thái RAM, tối đa8 mẫu mỗi request; lấy mẫu500ms tại task priority1.
Đây là log chẩn đoán lấy mẫu, không phải mọi sự kiện UART/ASR hay trace từng lệnh.
Không hook vprintf/audio và không lưu hội thoại/PCM/mật khẩu. Task HTTP priority2,
core0; không gọi socket/JSON/log từ Motion control task. Tái sử dụng kết nối TLS
khi poll để tránh handshake mỗi lần; tối đa2 socket và không tăng pool dashboard.

OTA hai board dùng POST `/update`: xác thực TLS/token, chip/project/size/SHA256,
chỉ ghi slot không chạy và chọn boot sau khi image hợp lệ. Motion cần migration
USB riêng một lần trước; MAINTENANCE khóa MOVE/GPIO10 và gửi PWM0 trước ghi flash.
Health check chạy cục bộ, trial không xác nhận trong15s sẽ reboot để rollback.
Ảnh test cố ý lỗi health chỉ được dùng qua OTA với cờ test, không nạp USB.
mDNS quảng cáo service `_awcar._tcp` để tìm board; TXT ota phản ánh khả năng hiện có.
Hostnames `awcar-brain.local`, `awcar-motion.local`;
CLI chấp nhận `--ip` nếu máy/mạng không resolve mDNS. Chạy build bằng utils/build_esp.py
để tạo private key/header; giữ các file .key/.tls.key/.crt khi chuyển workspace
hoặc laptop. Chứng chỉ cố định theo vai trò, độc lập IP của router. Không tắt kiểm
chứng chỉ khi lỗi; phục hồi đúng file hoặc nạp USB lại khi đổi khóa.
