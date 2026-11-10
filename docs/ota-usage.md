# OTA và log qua Wi-Fi — simplev1

Điện thoại điều khiển qua **AW-CAR → http://192.168.4.1**. Laptop nối cùng router
với hai ESP để nạp/xem log; router không mở đường lái. Không cần IP cố định `.166`.
Tên board giữ nguyên khi router đổi DHCP: `awcar-brain.local`, `awcar-motion.local`.

## Lệnh dùng hằng ngày

Mở PowerShell trong `D:/Project/AW-Car-ota` (nhánh `codex/simplev1-ota`):

```powershell
python utils/awcarctl.py discover
python utils/awcarctl.py info motion
python utils/awcarctl.py logs motion --seconds 60
python utils/awcarctl.py logs brain --seconds 60
```

Nạp riêng board cần sửa, khi xe đứng yên và VM ngắt trong mốc thử trên bàn:

```powershell
python utils/build_esp.py motion
python utils/awcarctl.py upload motion
# Hoặc Brain:
python utils/build_esp.py brain
python utils/awcarctl.py upload brain
```

Hai board đã bootstrap OTA, không chạy migration hoặc flash-all lại. FPGA vẫn
nạp JTAG riêng. OTA chỉ gửi application, không thay assets/partition/bootloader.
Nâng cấp cần thay các vùng đó phải có quy trình USB riêng.

CLI kiểm board, chip, project, SHA256 và chứng chỉ, rồi chờ build/ELF mới cùng
trạng thái `valid`. Khi mất trả lời, CLI chỉ kiểm kết quả; không tự gửi lại app.
Nếu không xác nhận được, xem `info`/log trước khi nạp tiếp. Không chạy hai uploader
trên cùng board. Motion khóa điều khiển trong lúc cập nhật; sau reboot tải lại Web
và thao tác mới. Không tự khôi phục lệnh đang giữ hoặc hành động AI cũ.

## Đổi mạng hoặc laptop

Qua AW-CAR, lưu Wi-Fi Internet mới một lần trên Dashboard; credential được chuyển
cho cả hai board. Laptop nối cùng mạng đó rồi chạy `discover`. Chứng chỉ/khóa không
phụ thuộc IP. Nếu mạng chặn mDNS, lấy IP riêng của Brain/Motion trên Web rồi thêm:

```powershell
python utils/awcarctl.py info motion --ip <Motion-STA-IP>
python utils/awcarctl.py upload brain --ip <Brain-STA-IP>
```

Giữ sáu file `{brain,motion}.{key,tls.key,crt}` trong
`build/private/management-keys` ngoài Git. Khi chuyển laptop, chép riêng thư mục
này vào nơi kín và đặt biến `AWCAR_KEY_DIR` tới đó. Đừng xóa khi dọn build. Không
gửi khóa vào chat, không dùng `verify=false` hoặc thay khóa khi OTA. Mất bộ khóa
thì cần khôi phục bản lưu hoặc bootstrap USB có kiểm soát.

User đã chọn uploader Python cho đơn giản; **không phải Arduino IDE/espota**.
Log Wi-Fi là mẫu trạng thái mỗi500ms trong RAM, không phải toàn bộ console/ASR.
Console USB vẫn cần cho lỗi boot sớm hoặc khi cả AP/STA không hoạt động.

## Phạm vi kiểm chứng

Hai ESP đã thử OTA thật, sai project/SHA, truyền dở, reset giữa truyền và rollback.
Motion giữ factory/NVS/motioncfg cũ khi migration. Xem các checkpoint trong `data`.
Benchmark dài A/B và số đo toàn đường điện thoại→PWM vẫn là phép thử riêng;
không suy chúng từ thời gian upload hoặc kiểm thử localhost.
