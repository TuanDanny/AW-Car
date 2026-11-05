# Target FPGA vật lý

[Tang Nano 9K](tang_nano9k/README.md) bổ sung pin, POR và build Gowin cho
logical top `aw_car_top`. RTL chức năng vẫn nằm trong `fpga/rtl`; không dùng
constraints board này cho FPGA khác. Build không gọi Programmer hoặc cổng COM.
