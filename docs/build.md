# Build, nạp và thu log

Chạy lệnh từ root worktree `simplev1`. Nhánh này độc lập với main và các worktree
Brain/Motion/Tang cũ; không chạy công cụ của hai phiên cùng lúc trên một board.

## Công cụ

- ESP-IDF **6.1**, chip ESP32-S3, dependency lock riêng hai firmware.
- Python 3.13; compiler C++17 cho host; Icarus với `-g2012` cho RTL.
- Gowin Education **1.9.11.03**, GW1NR-LV9QN88PC6/I5, revision C.
- KiCad 10 để mở schematic A3. Không có PCB trong mốc này.

Mặc định công cụ Windows tìm SDK ở `C:/Espressif/frameworks/esp-idf-v6.1`.
Có thể chỉ định `IDF_PATH`, `IDF_TOOLS_PATH`, `IDF_PYTHON_ENV_PATH` khi cài chỗ khác.
Chạy tool flash/serial bằng Python của SDK, vì có esptool5.6 và pyserial:

```powershell
$espPython='C:/Espressif/python_env/idf6.1_py3.13_env/Scripts/python.exe'
python utils/build_esp.py motion
python utils/build_esp.py brain
```

Lệnh build không nạp. Manifest/binary/log ở `build/motion` và `build/brain`.
Hai project độc lập, dùng chung codec/control qua `esp/shared`. Không sửa
`managed_components`; các thư mục đó do component manager dựng từ lockfile.

## Kiểm thử trên host

```powershell
python utils/check_repo.py
python -m unittest discover -s test
python utils/build_fpga.py --rtl-only --report build/rtl.json
python utils/build_fpga.py --gowin-only --report build/gowin.json
python -m pip install -r utils/requirements-test.txt
python -m playwright install chromium
python utils/simulator.py --port 8783
# Terminal khác:
python test/browser/test_dashboard.py --port 8783 --output build/browser
```

`--gowin-only` gồm tổng hợp/PnR/STA và mô phỏng netlist. Xem `--help` của runner để
chọn các phần riêng. Soak dùng một simulator khác cổng8784, tránh Web takeover
giữa test browser và tải nền:

```powershell
python utils/simulator.py --port 8784
python utils/soak.py --port 8784 --seconds 1800 --output build/soak.json
```

Các số host là thời gian nhận ACK trên localhost; không phải độ trễ ESP hay motor.

## Nạp đúng board

Ngắt VM hai DRV, giữ motor rời; xác nhận dây theo `schematic/README.md`.
COM3 Brain / COM7 Motion là nhận dạng tại lần triển khai này, có thể đổi sau khi
cắm USB. Không dùng GPIO17/18 đã hỏng của Motion. FPGA nạp JTAG, không nạp bằng COM11.

```powershell
& $espPython utils/flash_esp.py motion --port COM7 --vm-off
& $espPython utils/flash_esp.py brain --port COM3 --vm-off
python utils/program_fpga.py --vm-off --location 529
& $espPython utils/serial_log.py --ports COM3 COM7 --seconds 180 --output build/private/session
```

Flasher ESP từ chối sai VID/PID, flash size, partition layout hoặc image hash.
Chỉ ghi app đã chọn và assets Brain; đọc ngược kiểm SHA. Giữ partition table,
NVS, otadata Brain và motioncfg cũ. **Không dùng lệnh flash-all/merged image tại
0x0000** từ build output cho các board đã có dữ liệu. App Brain hiện ở0x20000,
Motion0x10000; công cụ xác định slot từ bảng phân vùng thật.

Nạp FPGA mặc định SRAM: mất điện sẽ mất bản SRAM. Flash chỉ sau khi có báo cáo
`build/bringup/spi-acceptance.json` đạt và trùng hash bitstream đang nạp:

```powershell
python utils/program_fpga.py --mode flash --vm-off --location 529
```

Công cụ chỉ chọn đúng JTAG GW1NR-9C và kiểm kết quả ngữ nghĩa; không đổi Security,
OTP hay user flash. Location529 là vị trí USB đã đo trên máy này, không phải số cố định
cho mọi máy. Giữ CRCCheck/Security ON. ReadCodes/UserCode không thay byte readback.

## Mở Web và thử

Motion phát **AW-CAR / 123456789**, mở `http://192.168.4.1`. Không PIN/Cho phép.
Manual mặc định30%; giữ nút chạy, nhả về0, DỪNG về0 và Manual. Chuyển AI rồi bấm
Bắt đầu nghe để tạo lượt mới. Ví dụ: 前进一秒, 后退一秒, 原地左转一秒,
原地右转一秒, 停车. Wi-Fi Internet của Brain nhập trên Web; không gửi mật khẩu vào log.

Web hiển thị duty mục tiêu trái/phải và ACK giao dịch FPGA trước. Không phải số đo
điện áp/tốc độ. VM5V và DMM, motor thật/2S, hiệu chuẩn encoder/PID là các phép thử riêng.
