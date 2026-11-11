# Brain–Motion integration

`ai_context.hpp` là policy portable giữ generation theo phiên cloud thực;
MCP chụp context tại ingress rồi sao chép vào arguments trước callback queue.
`runtime` sở hữu UART1/parser/status5Hz/STOP và một mục tiêu MOVE thay thế.
`tools.cc` đăng ký ba tool xe và các tool audio/status tối thiểu.

MOVE dùng parser action chung: bốn hướng cũ + sáu động tác cung/pivot; không
thêm tool cấp PWM hoặc quyền chạy. Giữ default30%/3s và context/generation.
Các câu nói/pinyin ở `../../../../docs/voice-commands.md`.
