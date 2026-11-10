# Câu lệnh thoại simplev1

Chọn AI trên Web, bấm Bắt đầu nghe hoặc BOOT. Mỗi lệnh có tốc độ riêng; bỏ tốc độ
thì dùng30%, không ghi nhớ mức của câu trước. Phần trăm là dutyPWM, chưa phải
vận tốc đo được. Hành động mặc định1s, cho phép100–3000ms; không xếp hàng.

| Nghĩa | Câu tiếng Trung | Pinyin |
| --- | --- | --- |
| Tiến2giây,60% | 前进两秒，速度百分之六十。 | Qián jìn liǎng miǎo, sù dù bǎi fēn zhī liù shí. |
| Lùi2giây,40% | 后退两秒，速度百分之四十。 | Hòu tuì liǎng miǎo, sù dù bǎi fēn zhī sì shí. |
| Quay trái tại chỗ2giây,50% | 原地左转两秒，速度百分之五十。 | Yuán dì zuǒ zhuǎn liǎng miǎo, sù dù bǎi fēn zhī wǔ shí. |
| Quay phải tại chỗ2giây,50% | 原地右转两秒，速度百分之五十。 | Yuán dì yòu zhuǎn liǎng miǎo, sù dù bǎi fēn zhī wǔ shí. |
| Tiến2giây, mặc định30% | 前进两秒。 | Qián jìn liǎng miǎo. |
| Dừng và vềManual | 停车。 | Tíng chē. |

Đợi hành động kết thúc giữa các câu; không cần nói DỪNG giữa từng lượt thử.
Sau DỪNG, muốn lái bằng AI lại phải chọnAI và bắt đầu lượt nghe mới. Tránh chỉ nói
“nhanh hơn” khi cần một mức cụ thể: AI có thể hiểu khác hoặc bỏ trường speed.
Web/log Motion cho biết duty thực đã yêu cầu:30%=405,40%=540,50%=675,
60%=810,80%=1080,100%=1350; dấu phụ thuộc hướng.
