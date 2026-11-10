# Firmware Motion

`runtime` owns Control/SPI/UART và mailbox. `web` HTTP/WS, snapshot/JSON ngoài
đường deadline. `main` khởi tạo và AP-only; không xóa NVS khi init lỗi.
