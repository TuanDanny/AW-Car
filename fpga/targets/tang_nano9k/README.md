# Tang Nano9K simplev1

Top `simplev1_nano9k`, Gowin Education1.9.11.03, deviceGW1NR-9C,
partGW1NR-LV9QN88PC6/I5. Clock P52/27MHz, S2 P3 active-low1,8V.
POR1024clock với INIT0; motor được mask LOW ngay khi nhấn S2 và trong POR.

| Chức năng | Package pin | Điện áp/pull |
| --- | --- | --- |
| MOSI/MISO/SCLK/CS |25/26/29/30|3,3V; MOSI/SCLK down, CS up |
| Encoder trái/phải |27/28|3,3V; trái down, phải NONE (pull-up ngoài) |
| DRV trái IN1/IN2 |35/40|3,3V, down |
| DRV phải IN1/IN2 |41/42|3,3V, down |
| LED1..6 |10/11/13/14/15/16|1,8V active-low, observer |

Đây là số chân package, không phải vị trí header/GPIO ESP32. Giữ nguyên chân
cấu hình/JTAG/MSPI/SSPI; không đấu3,3V vào nút/LED1,8V onboard.

`build.tcl` sinh project ở `build/fpga/gowin`, bật SystemVerilog2017, mapped
netlist, report timing dạng text, CST thực tế. Chạy từ root qua
`python utils/build_fpga.py --gowin-only`. Công cụ không nạp board.

SDC chỉ có clock27MHz và budget routing37,037ns với uncertainty0,2ns.
Năm D pin FF lấy mẫu async đầu được false-path chính xác; stage1→stage2,
logic còn lại và reset→driver vẫn tính timing. Không tạo clockSPI giả.
MISO: ba tick nhận cạnh (~111ns) cộng đường output phải nhỏ hơn nửaSPI500ns;
master phải giữ CS setup/hold/gap2us. Không phải cam kết SI/MTBF vật lý.

Netlist chức năng sau PnR chạy cùng black-box `tb_nano9k` và primitive Gowin cài
sẵn; không chép thư viện hãng. Không annotate SDF; STA routed được báo riêng.
Không gọi PASS nếu report thiếu, SDC inactive hoặc slack âm, dù tool exit0.
