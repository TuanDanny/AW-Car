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

Hiện chưa có receiver OTA và không quảng cáo OTA. mDNS chỉ quảng cáo service
`_awcar._tcp` để tìm board. Hostnames `awcar-brain.local`, `awcar-motion.local`;
CLI chấp nhận `--ip` nếu máy/mạng không resolve mDNS. Chạy build bằng utils/build_esp.py
để tạo private key/header; giữ các file .key/.tls.key/.crt khi chuyển workspace
hoặc laptop. Chứng chỉ cố định theo vai trò, độc lập IP của router. Không tắt kiểm
chứng chỉ khi lỗi; phục hồi đúng file hoặc nạp USB lại khi đổi khóa.
