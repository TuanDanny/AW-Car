# Bằng chứng kiểm thử RTL

## Encoder/snapshot — 23/10/2026

Đã chạy trên Windows với Icarus Verilog/VVP **13.0 stable (v13_0)**, package
MSYS2 UCRT64 `iverilog 1~13.0-2`. Tool/binary ở `build/toolchain/`, không commit.
Máy khác có thể dùng Icarus trong PATH; CI chạy package Ubuntu 24.04 và in version.

```powershell
$env:PATH = (Join-Path (Get-Location) 'build/toolchain/ucrt64/bin') + ';' + $env:PATH
python tools/run_fpga_tests.py
```

| Testbench | Kết quả | Bằng chứng |
| --- | --- | --- |
| tb_encoder_units | PASS | Reset assert/nhả, lọc N=1/3, ngưỡng N-1/N/N+1, 16 chuyển A/B, inversion và count4 wrap |
| tb_encoder_pair | PASS | 10 seed x 10.000 chuyển mỗi bánh; glitch, invalid sticky; snapshot trước cạnh đếm và timer/sequence/timestamp wrap |
| tb_encoder_timing | PASS | Tham số mặc định, 810.000 clock = 3 snapshot10ms, pha khởi động khác zero không tạo count |

Lệnh trả mã 0; compile không có warning. Thêm 3 test runner và 8 test cấu
trúc repo đều đạt. Không có phép đo trên FPGA hoặc xe; chưa có báo cáo tổng
hợp/PnR/timing, chưa chứng minh toàn lõi chứa được trên Nano 1K.

Nguồn phân phối công cụ: [MSYS2 Icarus](https://packages.msys2.org/package/mingw-w64-ucrt-x86_64-iverilog).
Toolchain cục bộ không thay đổi PATH hệ thống hoặc yêu cầu tắt phần mềm bảo vệ.
