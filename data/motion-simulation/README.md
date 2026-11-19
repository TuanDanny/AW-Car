# Mô phỏng động tác cơ bản — chưa phải nghiệm thu xe

Sinh bằng `python utils/motion_primitives_sim.py` từ root. Cần matplotlib theo
`utils/requirements-motion-sim.txt`; `--no-plots` chỉ dùng thư viện chuẩn.

- `results.json`: thông số minh họa, sai số đối chiếu giải tích và mô hình ma sát.
- `paths.csv`, `startup.csv`: dữ liệu số có thể kiểm tra độc lập.
- `primitives.png`: dấu và tỷ lệ duty của động tác, mô hình lý tưởng.
- `paths.png`: tròn/số 8, đường chuẩn và ảnh hưởng sai lệch hai bên giả định.
- `startup.png`: đề-pa mũ, tỷ lệ rẽ, phản ví dụ ga cuối quá thấp.

Đơn vị chiều dài trừu tượng: b=1. Không dùng chiều rộng ngoài xe làm track width;
không gán PWM thành mm/s của AW-Car. Ngưỡng ma sát, hằng số thời gian, sai lệch
hai bên là ví dụ tự đặt, không phải thông số đã đo. Không có dữ liệu dòng điện,
nhiệt, nguồn, cảm biến hay log riêng tư. Xem `docs/motion-primitives-study.md`.
