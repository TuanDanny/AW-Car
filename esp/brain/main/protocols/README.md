# Xiaozhi service transport

MQTT + UDP Opus/AES và WebSocket stock v2.5.2 dùng cấu hình activation/NVS.
Giữ wire protocol và TLS thật. MCP MOVE chỉ nhận context từ metadata
`session_id` của envelope cloud, không suy từ epoch tại lúc chạy callback.
