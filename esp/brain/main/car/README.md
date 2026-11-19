# Brain–Motion integration

`ai_context.hpp` là policy portable giữ generation theo phiên cloud thực;
MCP chụp context tại ingress rồi sao chép vào arguments trước callback queue.
`runtime` sở hữu UART1/parser/status5Hz/STOP và một mục tiêu MOVE thay thế.
`tools.cc` đăng ký ba tool xe và các tool audio/status tối thiểu.

MOVE dùng parser action chung cho mười động tác. AI và Web dùng cùng thang
Thanh ga, mặc định 20% tương ứng duty 56%. Thời lượng mặc định 3 giây.
Quy đổi diễn ra trước khi gửi lệnh UART với context/generation của phiên.
Các câu nói/pinyin ở `../../../../docs/voice-commands.md`.
