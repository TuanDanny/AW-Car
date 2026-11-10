# Brain–Motion integration

`ai_context.hpp` là policy portable giữ generation theo phiên cloud thực;
MCP chụp context tại ingress rồi sao chép vào arguments trước callback queue.
`runtime` sở hữu UART1/parser/status5Hz/STOP và một mục tiêu MOVE thay thế.
`tools.cc` đăng ký ba tool xe và các tool audio/status tối thiểu.
