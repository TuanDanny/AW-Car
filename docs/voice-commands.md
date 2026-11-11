# Câu lệnh thoại simplev1

Chọn AI trên Web, bấm Bắt đầu nghe hoặc BOOT. Mỗi lệnh có tốc độ riêng; bỏ tốc độ
thì dùng30%, không ghi nhớ mức của câu trước. Phần trăm là dutyPWM, chưa phải
vận tốc đo được. Hành động mặc định3s, cho phép100–3000ms; không xếp hàng.

| Nghĩa | Câu tiếng Trung | Pinyin |
| --- | --- | --- |
| Tiến, mặc định3giây/30% | 前进。 | Qián jìn. |
| Lùi, mặc định3giây/30% | 后退。 | Hòu tuì. |
| Quay trái, mặc định3giây/30% | 原地左转。 | Yuán dì zuǒ zhuǎn. |
| Quay phải, mặc định3giây/30% | 原地右转。 | Yuán dì yòu zhuǎn. |
| Tiến2giây,60% | 前进两秒，速度百分之六十。 | Qián jìn liǎng miǎo, sù dù bǎi fēn zhī liù shí. |
| Lùi2giây,40% | 后退两秒，速度百分之四十。 | Hòu tuì liǎng miǎo, sù dù bǎi fēn zhī sì shí. |
| Quay trái tại chỗ2giây,50% | 原地左转两秒，速度百分之五十。 | Yuán dì zuǒ zhuǎn liǎng miǎo, sù dù bǎi fēn zhī wǔ shí. |
| Quay phải tại chỗ2giây,50% | 原地右转两秒，速度百分之五十。 | Yuán dì yòu zhuǎn liǎng miǎo, sù dù bǎi fēn zhī wǔ shí. |
| Tiến2giây, mặc định30% | 前进两秒。 | Qián jìn liǎng miǎo. |
| Dừng và vềManual | 停车。 | Tíng chē. |

## Động tác mới trên nhánh motion-primitives

Chỉ dùng sau khi nạp đồng bộ Brain/Motion bản mới. Bốn lệnh trên vẫn giữ
nguyên ý nghĩa; “quay tại chỗ” khác “vừa tiến vừa rẽ”. Cung dùng ga bên trong
bằng50% bên ngoài; lùi trái/phải nói về hướng **đầu xe xoay**.

| Nghĩa / action | Câu tiếng Trung | Pinyin |
| --- | --- | --- |
| Tiến rẽ cong trái / forward_left | 一边前进，一边向左转弯。 | Yì biān qián jìn, yì biān xiàng zuǒ zhuǎn wān. |
| Tiến rẽ cong phải / forward_right | 一边前进，一边向右转弯。 | Yì biān qián jìn, yì biān xiàng yòu zhuǎn wān. |
| Lùi, đầu xe xoay trái / backward_left | 后退，车头向左转。 | Hòu tuì, chē tóu xiàng zuǒ zhuǎn. |
| Lùi, đầu xe xoay phải / backward_right | 后退，车头向右转。 | Hòu tuì, chē tóu xiàng yòu zhuǎn. |
| Ga trái0, phải tiến / pivot_left | 左侧不给油，右侧前进。 | Zuǒ cè bù gěi yóu, yòu cè qián jìn. |
| Ga phải0, trái tiến / pivot_right | 右侧不给油，左侧前进。 | Yòu cè bù gěi yóu, zuǒ cè qián jìn. |

Bỏ mức ga/thời gian vẫn dùng30%/3giây cho từng câu. Pivot không phanh giữ
bánh phía ga0. Câu nói do cloud nhận dạng/chọn tool; bảng không phải bằng
chứng đã thử tiếng nói thật trên bản firmware mới.

Đợi hành động kết thúc giữa các câu; không cần nói DỪNG giữa từng lượt thử.
Sau DỪNG, muốn lái bằng AI lại phải chọnAI và bắt đầu lượt nghe mới. Tránh chỉ nói
“nhanh hơn” khi cần một mức cụ thể: AI có thể hiểu khác hoặc bỏ trường speed.
Web/log Motion cho biết duty thực đã yêu cầu:30%=405,40%=540,50%=675,
60%=810,80%=1080,100%=1350; dấu phụ thuộc hướng.
