<a id="c2"></a>

# CHƯƠNG 2. 7,83 Hz TRONG LĨNH VỰC AI VÀ MÁY TÍNH

## 2.1. Chuỗi xử lý số khi đo cộng hưởng Schumann

Một trạm đo hiện đại là một hệ thống máy tính: cảm biến → khuếch đại → lọc chống chồng phổ → ADC → gắn
thời gian GPS → phổ Welch → loại nhiễu → khớp hàm Lorentz → tham số mode (biên độ, tần số, độ rộng) [10], [11].

**Ngân sách bit của ADC**: dải động lý tưởng 6,02·N + 1,76 dB.

**Bảng 2.1.** Dải động lý tưởng theo số bit (nguồn: `physics.adc`)

| Số bit N | 12 | 16 | 24 | 32 |
|---|---|---|---|---|
| Dải động (dB) | 74,00 | 98,08 | 146,24 | 194,40 |

Tín hiệu Schumann (cỡ pT) nằm cạnh nhiễu điện lưới 50 Hz ở Việt Nam và các hài của nó, mạnh hơn nhiều
bậc; vì vậy trạm cần ADC 24 bit, bộ lọc chắn 50 Hz và vị trí xa đường dây.

**Độ phân giải tần số**: với bản ghi 10 phút (T = 600 s), Δf = 1/T = 0,001667 Hz và 7,83 Hz rơi đúng ô
phổ thứ 4698 (vì 7,83 × 600 = 4698 là số nguyên).

## 2.2. AI và học máy trong nghiên cứu Schumann

| Hướng | Công trình | Nội dung | Mức |
|---|---|---|---|
| Khớp Lorentz tăng cường bằng học sâu | Cano-Domingo và cộng sự 2025 [13] | Ba chiến lược bộ mã hóa tự động, khử nhiễu và xử lý nhiều mode cùng lúc, thích nghi tính không dừng | B |
| Chương trình xử lý mở | Salinas và cộng sự 2022 [11] | Python, bản ghi 10 phút, Welch 6–25 Hz, loại nhiễu nhân tạo | A |
| Phát hiện sự kiện liên quan động đất | Cano-Domingo 2022 (VAE + LSTM) [14]; 2025 (CNN + RNN) [15] | Thăm dò; chưa phải công cụ dự báo | C |

Các bài toán AI tự nhiên của lĩnh vực: (1) hồi quy tham số mode từ phổ nhiễu; (2) phân loại và loại bỏ
nhiễu nhân tạo; (3) phát hiện xung Q (Q-burst) và sự kiện thoáng qua; (4) dự báo chuỗi thời gian; (5) bài
toán ngược suy ra phân bố sét toàn cầu từ nhiều trạm. Rủi ro điển hình: rò rỉ dữ liệu giữa tập huấn
luyện và kiểm thử, tính không dừng theo mùa, và tuyên bố quá mức (đặc biệt về động đất).

## 2.3. Thí nghiệm tái lập: ước lượng f₁ từ phổ nhiễu

**Thiết kế** (`sr783/srml.py`): phổ mô phỏng trên lưới 5,00–11,00 Hz bước 0,05 Hz (121 ô); mode 1 với
f₁ ∈ [7,4; 8,2] Hz, độ rộng toàn phần 1,2–2,6 Hz; mode 2 quanh 13,6–14,8 Hz; nền 1/f; nhiễu nhân 12 %
(tương đương trung bình Welch); 35 % mẫu có một vạch nhiễu nhân tạo hẹp (độ lệch chuẩn 0,04 Hz) mạnh
0,8–2 lần mode 1. Tập huấn luyện 1200 phổ (hạt giống 7831), tập kiểm thử 400 phổ (hạt giống 7832, trong
đó 140 phổ có nhiễu vạch). Năm phương pháp: lấy đỉnh cực đại; khớp Lorentz Levenberg–Marquardt; khớp
Lorentz bền vững (tái trọng số Cauchy); hồi quy ridge trên log-phổ (λ = 100 chọn bằng tập kiểm định);
phương pháp lai (ridge khởi tạo cho khớp bền vững).

**Bảng 2.2.** Kết quả trên 400 phổ kiểm thử (nguồn: `ml.metrics`)

| Phương pháp | MAE chung (Hz) | RMSE chung (Hz) | MAE không nhiễu vạch (Hz) | MAE có nhiễu vạch (Hz) | Tỉ lệ sai > 0,2 Hz |
|---|---|---|---|---|---|
| Đỉnh cực đại | 0,3283 | 0,5606 | 0,1356 | 0,6861 | 39,75 % |
| Khớp Lorentz | 0,0634 | 0,2692 | 0,0266 | 0,1316 | 1,50 % |
| Khớp Lorentz bền vững | 0,0496 | 0,2367 | 0,0283 | 0,0891 | 0,75 % |
| Ridge (học máy) | 0,0531 | 0,0688 | 0,0481 | 0,0622 | 1,00 % |
| **Lai học máy + Lorentz** | **0,0299** | **0,0395** | 0,0283 | **0,0327** | **0,00 %** |

![Hình 7. Sai số tuyệt đối trung bình khi ước lượng f₁](figures/fig7_ml_results.svg)

**Nhận định**: (1) Lấy đỉnh cực đại thất bại nặng khi có nhiễu vạch: MAE 0,6861 Hz, 72,14 % mẫu sai
quá 0,2 Hz. (2) Khớp Lorentz thuần vật lý chính xác nhất khi sạch (0,0266 Hz) nhưng dễ bám nhầm vào vạch
nhiễu nếu khởi tạo sai (RMSE 0,4523 Hz ở nhóm có nhiễu). (3) Học máy ridge bền vững (RMSE 0,0688 Hz)
nhưng kém chính xác hơn khi sạch. (4) Kết hợp hai cách cho kết quả tốt nhất ở mọi nhóm và không có mẫu
nào sai quá 0,2 Hz: học máy chọn "vùng đúng", vật lý cho "giá trị chính xác". Đây là lập luận định lượng
cho hướng "AI lai vật lý" mà các nghiên cứu gần đây theo đuổi [13].

![Hình 9. Một phổ kiểm thử có vạch nhiễu nhân tạo](figures/fig9_example_fit.svg)

## 2.4. Giao diện não – máy tính và điện não đồ

- **Dải tần**: theo bảng thuật ngữ IFCN 2017, alpha là 8–13 Hz, theta là 4 đến dưới 8 Hz [33]. Vì vậy
  7,83 Hz thuộc theta trên; trùng dải không chứng minh quan hệ nhân quả với Schumann [33], [40].
- **BCI dựa trên SSVEP**: người nhìn một nguồn nhấp nháy tần số f sinh đáp ứng EEG tại f. Hệ đánh vần
  40 ký tự của Chen và cộng sự đạt tốc độ truyền thông tin tới 5,32 bit/s bằng điều chế kết hợp tần số –
  pha [16]. Trên màn hình tần số làm tươi cố định, tần số không chia hết cho tần số làm tươi được tạo
  bằng kích thích hình sin lấy mẫu [17].

**Bảng 2.3.** Tạo 7,83 Hz trên màn hình (nguồn: `synth.display`)

| Làm tươi (Hz) | Khung/chu kỳ | Bật/tắt nguyên khung gần nhất | Sai số bật/tắt |
|---|---|---|---|
| 60 | 7,6628 | 60/8 = 7,5000 Hz | −4,21 % |
| 75 | 9,5785 | 75/10 = 7,5000 Hz | −4,21 % |
| 90 | 11,4943 | 90/11 = 8,1818 Hz | +4,49 % |
| 120 | 15,3257 | 120/15 = 8,0000 Hz | +2,17 % |
| 144 | 18,3908 | 144/18 = 8,0000 Hz | +2,17 % |
| 165 | 21,0728 | 165/21 = 7,8571 Hz | +0,35 % |
| 240 | 30,6513 | 240/31 = 7,7419 Hz | −1,12 % |

Với kích thích hình sin lấy mẫu ở 60 Hz, mã độ sáng 8 bit của 16 khung đầu là
`80 DD FF D0 6E 17 03 3E A2 F1 F7 B2 4C 07 0F 5E` (quy tắc làm tròn nửa lên, khớp tuyệt đối giữa Python và
JavaScript).

![Hình 5. Kích thích hình sin lấy mẫu 7,83 Hz trên màn hình 60 Hz](figures/fig5_display_60hz.svg)

**Cảnh báo an toàn**: 7,83 lần/giây vượt ngưỡng 3 lần/giây của tiêu chí WCAG 2.3.1 nếu vùng nhấp nháy
đủ lớn và đủ tương phản [36]; khoảng 0,3–3 % dân số có đáp ứng nhạy cảm ánh sáng, dải 15–25 Hz kích
thích mạnh nhất nhưng dải nguy cơ trải 1–65 Hz [35]. Kích thích 7,83 Hz bằng ánh sáng chỉ được dùng trong
phòng thí nghiệm có sàng lọc và giám sát.

## 2.5. Sinh tín hiệu 7,83 Hz chính xác trên phần cứng và phần mềm

**Tổng hợp số trực tiếp (DDS)**: từ điều chỉnh M = round(f·2ᴺ/f_clk), tần số ra f_out = M·f_clk/2ᴺ [26].

**Bảng 2.4.** DDS cho 7,83 Hz (làm tròn nửa về chẵn; nguồn: `synth.dds`)

| N bit | f_clk | M (thập phân) | M (hex) | f_out (Hz) | Sai số |
|---|---|---|---|---|---|
| 32 | 48 kHz | 700617 | `0x000AB0C9` | 7,830005139112473 | +0,6563 ppm |
| 32 | 44,1 kHz | 762576 | `0x000BA2D0` | 7,830001786351204 | +0,2281 ppm |
| 32 | 96 kHz | 350308 | `0x00055864` | 7,829993963241577 | −0,7710 ppm |
| 24 | 48 kHz | 2737 | `0x000AB1` | 7,830619812011719 | +79,16 ppm |
| 32 | 16 MHz | 2102 | `0x00000836` | 7,830560207366943 | +71,55 ppm |
| 48 | 16 MHz | 137746817 | `0x00000835D981` | 7,830000015474070 | +0,001976 ppm |
| 24 | 1 MHz | 131 | `0x000083` | 7,808208465576172 | −2783 ppm |

![Hình 4. Sai số tần số DDS theo độ rộng bộ tích lũy pha](figures/fig4_dds_error.svg)

**Bộ định thời vi điều khiển**: ATmega328P ở 16 MHz, Timer1 chế độ CTC đảo chân OC1A cho
f = f_clk/(2·N·(1 + OCR1A)) [27].

**Bảng 2.5.** Chọn bộ chia cho 7,83 Hz (nguồn: `synth.timer1`)

| Bộ chia N | OCR1A | Hợp lệ (≤ 65535) | f thực (Hz) | Sai số |
|---|---|---|---|---|
| 1 | 1021710 | không | – | – |
| 8 | 127713 | không | – | – |
| 64 | 15963 (`0x3E5B`) | có | 7,830117765 | +15,040 ppm |
| 256 | 3990 (`0x0F96`) | có | 7,830117765 | +15,040 ppm |
| 1024 | 997 (`0x03E5`) | có | 7,828156313 | −235,465 ppm |

Cấu hình chọn: TCCR1A = `0x40` (`01000000`: COM1A0 = 1, đảo OC1A), TCCR1B = `0x0B` (`00001011`:
WGM12 = 1 chọn CTC, CS12:10 = 011 chọn chia 64), OCR1AH = `0x3E`, OCR1AL = `0x5B`. Bộ chia 64 và 256 cho
cùng tần số vì 64 × 15964 = 256 × 3991 = 1 021 696.

**Bảng 2.6.** Sai số nguồn dao động lấn át sai số lượng tử (nguồn: `synth.clock_tolerance`)

| Nguồn dao động | Dải tần số thực của "7,83 Hz" |
|---|---|
| Thạch anh ±20 ppm | 7,829843 – 7,830157 Hz |
| RC hiệu chuẩn ±1 % | 7,751700 – 7,908300 Hz |
| RC xuất xưởng ±2 % | 7,673400 – 7,986600 Hz |
| RC xuất xưởng ±10 % | 7,047000 – 8,613000 Hz |

Mạch IC 555 với R1 = 11,0 kΩ, R2 = 86,6 kΩ, C = 1,00 µF cho danh nghĩa 7,8322 Hz (+0,028 %) theo
f = 1/(ln2·(R1 + 2R2)·C) (công thức gần đúng của datasheet 1,44/((R1 + 2R2)C) cho 7,8176 Hz) [28], nhưng với
điện trở ±1 % và tụ ±5 % thì dải thực là 7,385–8,328 Hz. Kết luận: một sản phẩm "7,83 Hz" dùng bộ dao
động RC hoặc 555 có thể lệch hàng phần trăm; chỉ thạch anh hoặc chuẩn ngoài mới giữ được vài chục ppm.

**Âm thanh số**: ở 44,1 kHz một chu kỳ 7,83 Hz dài 5632,183908 mẫu, ở 48 kHz là 6130,268199 mẫu (không
nguyên). Bộ đệm lặp liền mạch cho âm đẳng thời hoặc nhịp phách hai tai với âm mang 200 Hz phải dài
100 s (4 800 000 mẫu ở 48 kHz). Bộ dao động của trình duyệt lưu tần số dạng binary32, tức 7,83 Hz thành
7,8299999237060546875 Hz, sai −9,74 ppb, nhỏ hơn rất nhiều sai số đồng hồ âm thanh.

## 2.6. Truyền thông ELF và giới hạn thông tin

Sóng ELF xuyên được nước biển hàng trăm feet nên từng dùng để liên lạc một chiều với tàu ngầm: hệ thống
của Hải quân Mỹ (Clam Lake, Wisconsin và Republic, Michigan) hoạt động khoảng 76 Hz, điều tần giữa 72 và
80 Hz để mã hóa bit 0/1, vận hành 1989–2004 [20]; Nga có trạm ZEVS 82 Hz. Băng thông hẹp làm tốc độ cực
thấp, đúng như giới hạn Shannon C = B·log₂(1 + SNR) [21].

**Bảng 2.7.** Dung lượng kênh minh họa (nguồn: `physics.shannon`)

| Trường hợp | B (Hz) | SNR 10 dB | SNR 0 dB | SNR −10 dB | SNR −20 dB |
|---|---|---|---|---|---|
| Băng thông mode 1 (f/Q, Q ≈ 5) | 1,566 | 5,417 bit/s | 1,566 bit/s | 0,2153 bit/s | 0,02248 bit/s |
| Dải điều tần 72–80 Hz | 8,000 | 27,68 bit/s | 8 bit/s | 1,1 bit/s | 0,1148 bit/s |

Mọi tuyên bố "truyền thông tin, năng lượng chữa lành qua 7,83 Hz" đều phải chịu giới hạn này.

## 2.7. An ninh máy tính: kênh ẩn từ trường tần số thấp

Máy tính phát từ trường tần số thấp khi tải CPU thay đổi. ODINI đạt tối đa 40 bit/s ở 100–150 cm, kể cả
qua lồng Faraday [18]; MAGNETO dùng từ kế điện thoại thu 0,2–5 bit/s trong vòng khoảng 12 cm, kể cả khi
điện thoại ở chế độ máy bay [19]. Biện pháp phòng vệ: che chắn, gây nhiễu, phân vùng khoảng cách [19].
Trong bối cảnh kênh nhiễu, mã sửa lỗi như Hamming và băm toàn vẹn như SHA-256 là nền tảng để biến bit
thô thành dữ liệu tin cậy, cũng là lý do SR783 dùng chúng ([Chương 4](05-chuong-4-tang-bit.md#c4)).
