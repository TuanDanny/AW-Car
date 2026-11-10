# Brain host tests

`python -m unittest discover -s test/brain -v` biên dịch và chạy chính
`esp/brain/main/car/ai_context.hpp` trên host. Kiểm tra metadata thiếu/sai,
callback chờ qua STOP/mode/reset/UART timeout, fresh session và context
được chụp trước khi kết nối. Không mở cổng hoặc chứng nhận phần cứng.
