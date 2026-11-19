# Câu lệnh thoại simplev1

Chọn AI trên Web, bấm Bắt đầu nghe hoặc BOOT. Mỗi câu dùng mức ga riêng,
chuẩn theo [Thanh ga Web](dashboard.md). Bỏ mức ga thì dùng 20%, tương ứng
56% duty mục tiêu. Hành động mặc định 3 giây, cho phép 100–3.000 ms.

| Nghĩa | Câu tiếng Trung | Pinyin |
| --- | --- | --- |
| Tiến, mặc định 3 giây / ga 20% | 前进。 | Qián jìn. |
| Lùi, mặc định 3 giây / ga 20% | 后退。 | Hòu tuì. |
| Quay trái, mặc định 3 giây / ga 20% | 原地左转。 | Yuán dì zuǒ zhuǎn. |
| Quay phải, mặc định 3 giây / ga 20% | 原地右转。 | Yuán dì yòu zhuǎn. |
| Tiến2giây,60% | 前进两秒，速度百分之六十。 | Qián jìn liǎng miǎo, sù dù bǎi fēn zhī liù shí. |
| Lùi2giây,40% | 后退两秒，速度百分之四十。 | Hòu tuì liǎng miǎo, sù dù bǎi fēn zhī sì shí. |
| Quay trái tại chỗ2giây,50% | 原地左转两秒，速度百分之五十。 | Yuán dì zuǒ zhuǎn liǎng miǎo, sù dù bǎi fēn zhī wǔ shí. |
| Quay phải tại chỗ2giây,50% | 原地右转两秒，速度百分之五十。 | Yuán dì yòu zhuǎn liǎng miǎo, sù dù bǎi fēn zhī wǔ shí. |
| Tiến2giây, ga mặc định 20% | 前进两秒。 | Qián jìn liǎng miǎo. |
| Dừng và vềManual | 停车。 | Tíng chē. |

## Rẽ cong và quay quanh một bên

Rẽ cong dùng duty bên trong bằng một nửa bên ngoài. Khi lùi rẽ, trái/phải
là hướng **đầu xe xoay**.

| Nghĩa / action | Câu tiếng Trung | Pinyin |
| --- | --- | --- |
| Tiến rẽ cong trái / forward_left | 一边前进，一边向左转弯。 | Yì biān qián jìn, yì biān xiàng zuǒ zhuǎn wān. |
| Tiến rẽ cong phải / forward_right | 一边前进，一边向右转弯。 | Yì biān qián jìn, yì biān xiàng yòu zhuǎn wān. |
| Lùi, đầu xe xoay trái / backward_left | 后退，车头向左转。 | Hòu tuì, chē tóu xiàng zuǒ zhuǎn. |
| Lùi, đầu xe xoay phải / backward_right | 后退，车头向右转。 | Hòu tuì, chē tóu xiàng yòu zhuǎn. |
| Ga trái0, phải tiến / pivot_left | 左侧不给油，右侧前进。 | Zuǒ cè bù gěi yóu, yòu cè qián jìn. |
| Ga phải0, trái tiến / pivot_right | 右侧不给油，左侧前进。 | Yòu cè bù gěi yóu, zuǒ cè qián jìn. |

Khi quay quanh một bên, phía bánh trong nhận duty 0.

Đợi hành động kết thúc giữa các câu; không cần nói DỪNG giữa từng lượt thử.
Sau DỪNG, muốn lái bằng AI lại phải chọnAI và bắt đầu lượt nghe mới. Tránh chỉ nói
“nhanh hơn” khi cần một mức cụ thể: AI có thể hiểu khác hoặc bỏ trường speed.
Nói **前进，油门百分之一** (qián jìn, yóu mén bǎi fēn zhī yī) để yêu cầu
Tiến ở ga 1%. Ở lệnh đi thẳng, ga 1% cho duty mục tiêu khoảng **608 tick**,
ga 20% cho **756 tick**, ga 100% cho **1.350 tick**. Duty hiển thị có thể tăng
ngắn lúc đề-pa.
