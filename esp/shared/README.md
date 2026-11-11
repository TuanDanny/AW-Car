# Lõi dùng chung

Contract ở `../../docs/protocol.md`. Code C++17, không driver/FreeRTOS/heap trên
đường điều khiển. Hai firmware include thư mục này; host test dùng cùng source.

`primitives.hpp`: ánh xạ 10 động tác có dấu và envelope đề-pa tùy chọn. Ga bên
trong của cung bằng một nửa bên ngoài; khi lùi, trái/phải là hướng đầu xe xoay.
Profile mặc định tắt; `Control` sở hữu STOP/deadline/reverse/wake trước envelope.
