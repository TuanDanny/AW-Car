# Dữ liệu

Chỉ lưu vector giao thức và báo cáo kiểm thử đã lọc thông tin riêng tư. Firmware,
NVS, mật khẩu Internet, flash dump và log serial thô nằm ngoài Git trong build/private.

`optimization-comparison.json`: A60/B61 mẫu điện thoại, kiểm thử và giới hạn.
`optimization-phone-samples.json`: chỉ hướng và hai khoảng thời gian microsecond.
`optimization-web-render.json`: A/B HTML production trên host; không phải đo PWM.

`wiring.json` là contract chân/net của bản A3; trường `planned` phân biệt dây
dự kiến. `schematic-verification.json` ghi đối chiếu native netlist, GPIO/CST,
ERC và hash bản vẽ/PDF; không phải chứng nhận công suất hoặc PCB.
