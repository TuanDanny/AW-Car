# Stock audio pipeline

AudioService, Opus, I²S simplex và ESP-SR AFE của Xiaozhi v2.5.2. Chỉ
NoAudioCodecSimplex được dùng với INMP441/MAX98357A; tên upstream này
chỉ module I²S không có codec điều khiển, không phải âm thanh giả.
Không có CarChat/VAD guard bổ sung. Wake word không được bật trong profile.

MAX98357A dùng I²S48kHz; mic giữ16kHz. Decoder theo metadata từng packet,
rate converter Espressif đổi mẫu trước playback. Lỗi đổi mẫu làm bỏ frame,
không phát PCM chưa chuyển ở clock khác; ResetDecoder cũng reset filter.
Log một frame sau mỗi đổi rate ghi số mẫu vào/ra để đối chiếu thời lượng.
