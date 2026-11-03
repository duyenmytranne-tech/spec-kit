<a id="c4"></a>

# CHƯƠNG 4. LIÊN KẾT CHẶT CHẼ ĐẾN TẦNG BIT

## 4.1. Mô hình liên kết tám tầng

**Bảng 4.1.** Từ hiện tượng vật lý đến từng bit, và cách kiểm chứng mỗi mắt xích

| Tầng | Đại lượng | Biểu diễn bit | Sai số / giới hạn | Kiểm chứng trong gói |
|---|---|---|---|---|
| T1 Vật lý | SR mode 1 ≈ 1 pT, 7,5–8 Hz | – | Biến thiên tự nhiên | Bảng 1.1, 1.2 |
| T2 Cảm biến | Từ kế điện thoại 0,15 µT/LSB | 16 bit | 1 pT = 6,667·10⁻⁶ LSB | `physics.magnetometer` |
| T3 Số hóa | ADC 24 bit | 146,24 dB lý tưởng | Nhiễu nền, 50 Hz | Bảng 2.1 |
| T4 Xử lý tín hiệu | Ô phổ 10 phút | Ô số 4698 | Δf = 0,001667 Hz | `physics.cavity.fft_bin_10min` |
| T5 AI | Ước lượng f₁ | Số thực, hạt giống SplitMix64 | MAE 0,0299 Hz (lai) | Bảng 2.2 |
| T6 Sinh tín hiệu | DDS, Timer1 | M = 700617; OCR1A = 15963 | +0,6563 ppm; +15,040 ppm | Bảng 2.4, 2.5 |
| T7 Ứng dụng | Tần số 783/100, pha số nguyên | (p·Δt) mod 1000q | Lệch đồng hồ 1 ms → 2,82° | Bảng 4.3 |
| T8 Toàn vẹn | SECDED(72,64), SHA-256 | 72 bit/từ; 256 bit | Sửa 1 bit, phát hiện 2 bit | Bảng 4.5; SHA256SUMS |

## 4.2. Biểu diễn số 7,83

Số 7,83 = 783/100 không có biểu diễn nhị phân hữu hạn, nên mọi định dạng đều lưu một giá trị gần đúng;
chuẩn IEEE 754 quy định cách làm tròn về giá trị gần nhất, khi hòa thì về số chẵn [22].

**Bảng 4.2.** Biểu diễn 7,83 (làm tròn nửa về chẵn, tính bằng số hữu tỉ và đối chiếu `struct`; nguồn: `bits`)

| Định dạng | Mã | Giá trị lưu chính xác | Sai số tuyệt đối |
|---|---|---|---|
| IEEE 754 binary16 | `0x47D4` | 7,828125 | −1,875·10⁻³ |
| IEEE 754 binary32 | `0x40FA8F5C` | 7,8299999237060546875 | −7,62939·10⁻⁸ (−9,74 ppb) |
| IEEE 754 binary64 | `0x401F51EB851EB852` | 7,8300000000000000710542735760100185871124267578125 | +7,10543·10⁻¹⁷ |
| Dấu phẩy tĩnh Q8.8 | `0x07D4` (2004) | 7,828125 | −1,875·10⁻³ |
| Dấu phẩy tĩnh Q16.16 | `0x0007D47B` (513147) | 7,8300018310546875 | +1,83105·10⁻⁶ |
| BCD đóng gói | `0x783` | 0111 1000 0011 | 0 (dấu chấm ngầm định) |

Chuỗi bit binary32: dấu `0`, số mũ `10000001` (129 → 2^(129−127) = 2²), phần định trị
`11110101000111101011100`.

![Hình 3. Bản đồ bit IEEE 754 của số 7,83](figures/fig3_ieee754_bits.svg)

## 4.3. Pha hữu tỉ và đồng bộ đến từng bit

Biểu diễn tần số bằng phân số p/q và thời gian bằng mili giây nguyên cho pha
(p·Δt mod 1000q)/(1000q) **chính xác tuyệt đối**: không trôi, mọi thiết bị cùng mốc cho cùng tử số. Với
7,83 Hz, mẫu số là 100 000, độ phân giải pha 0,0036°.

**Bảng 4.3.** Vector kiểm thử pha (nguồn: `synth.phase_vectors`; khớp tuyệt đối Python ↔ JavaScript)

| p/q | t (ms UTC) | t0 (ms) | Tử số / mẫu số | Pha |
|---|---|---|---|---|
| 783/100 | 1793664000000 | 0 | 0 / 100000 | 0,0000° |
| 783/100 | 1793664012345 | 0 | 66135 / 100000 | 238,0860° |
| 783/100 | 1793664000127 | 1793664000000 | 99441 / 100000 | 357,9876° |
| 7792/1000 | 1793664012345 | 0 | 192240 / 1000000 | 69,2064° |

**Bảng 4.4.** Lệch đồng hồ và lệch pha ở 7,83 Hz (nguồn: `synth.offset_phase_error`)

| Lệch đồng hồ | 1 ms | 3,55 ms | 10 ms | 20 ms | 50 ms |
|---|---|---|---|---|---|
| Lệch pha | 2,82° | 10,01° | 28,19° | 56,38° | 140,94° |

Muốn lệch pha dưới 10° thì đồng hồ hai thiết bị phải khớp trong 3,548 ms. Trên thiết bị, ứng dụng tính
thời điểm hiện tại theo micro giây (đồng hồ hệ điều hành hiệu chuẩn bằng `performance.now()`), vì lượng tử
1 ms của đồng hồ hệ thống tự nó đã gây tới 2,82° lệch pha; công thức vẫn là số nguyên với mẫu số 10⁶·q. Mã phiên mẫu:
`SR783-1-783-100-1793664000000-I-9336D787` (8 ký tự cuối là đầu băm SHA-256 của phần thân).

## 4.4. Mã Hamming mở rộng SECDED

Xây dựng tổng quát cho k bit dữ liệu [23]: chọn r nhỏ nhất với 2ʳ ≥ k + r + 1; bit chẵn lẻ ở vị trí lũy
thừa của 2; dữ liệu ở các vị trí còn lại; vị trí 0 là bit chẵn lẻ tổng. Hội chứng s = XOR các vị trí có
bit 1 chỉ thẳng vị trí lỗi; bit chẵn lẻ tổng phân biệt lỗi đơn (sửa được) với lỗi kép (phát hiện).

Ví dụ liên kết với 7,83:

- Ba chữ số BCD 7, 8, 3 qua SECDED(8,4): `0111` → `01101001`; `1000` → `10010110`; `0011` → `00111100`.
- Giá trị thanh ghi OCR1A `0x3E5B` qua SECDED(22,16): `0x0FCAAC`.
- Từ binary64 `0x401F51EB851EB852` qua SECDED(72,64): `0x410FA8F5C247AE0A32`.

**Bảng 4.5.** Tiêm lỗi vét cạn (nguồn: `secded.fault_injection`)

| Mã | Bit/từ | Lỗi 1 bit thử | Sửa đúng | Lỗi 2 bit thử | Phát hiện |
|---|---|---|---|---|---|
| SECDED(8,4) | 8 | 8 | 100 % | 28 | 100 % |
| SECDED(22,16) | 22 | 22 | 100 % | 231 | 100 % |
| SECDED(72,64) | 72 | 72 | 100 % | 2556 | 100 % |

## 4.5. SHA-256 và niêm phong toàn gói

- Kiểm chứng cài đặt SHA-256 với vector chuẩn NIST [24]: SHA-256("abc") =
  `ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad`; SHA-256("") =
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- **Kê khai**: `SHA256SUMS` liệt kê băm của mọi tệp (tương thích `sha256sum -c`).
- **Gốc băm**: `ROOT_HASH.txt` = SHA-256 của toàn bộ `SHA256SUMS`; một giá trị 256 bit niêm phong cả gói.
- **Gốc được bảo vệ**: 256 bit gốc tách thành 4 từ 64 bit, mỗi từ mã SECDED(72,64) trong
  `ROOT_HASH.secded.txt`: lật 1 bit trong bản lưu gốc vẫn khôi phục được, lật 2 bit bị phát hiện.
- **Chuỗi băm nhật ký**: hᵢ = SHA-256(hᵢ₋₁ ‖ "\n" ‖ JSON chuẩn hóa của sự kiện i), h₀ = 64 số 0. Hai sự kiện
  mẫu cho h₁ = `40019af5338913243e1738d03d40ff3c30c5a848169e832724993b11cae2f4eb`, h₂ =
  `05744a7b43519f409ce81ce807f556c24629c205c0d0fbaf2f8900025f9e7d9d`.

## 4.6. Đồng nhất Python ↔ JavaScript

Ứng dụng SR783 cài đặt lại toàn bộ lõi bằng JavaScript (BigInt). Bộ nghiệm thu chạy trong Chromium so
khớp với `results.json` do Python sinh: biểu diễn IEEE 754 32/64 bit và giá trị thập phân chính xác;
7 cấu hình DDS (từ điều chỉnh và f_out đến 15 chữ số); Timer1 (OCR1A, f, ppm, TCCR1B); 4 vector pha;
3 ví dụ SECDED; bản ghi cài đặt (2 từ mã và thẻ); mã phiên; chuỗi băm; 4 số đầu SplitMix64 với hạt
giống 0 (`0xE220A8397B1DCDAF`, …); vector SHA-256. Kết quả ở Phụ lục C.

## 4.7. Ma trận truy vết yêu cầu

| Yêu cầu | Nội dung trong báo cáo | Bằng chứng định lượng | Kiểm thử tự động |
|---|---|---|---|
| R0 | Cấu trúc, thể thức, tài liệu có trạng thái xác minh | 53 tài liệu, mức A–D | `test_report.py` (trích dẫn, mục lục, hình) |
| R1 | Chương 2 | Bảng 2.1–2.7, Hình 4, 5, 7, 9 | `test_core.py`, `test_results.py` |
| R2 | Chương 3 | Bảng 3.1–3.5, Hình 2, 6 | `test_report.py` (số liệu khớp `results.json`) |
| R3 | Chương 4 | Bảng 4.1–4.5, Hình 3; SHA256SUMS | `test_secded.py`, `test_integrity.py`, nghiệm thu đối chiếu bit |
| R4 | Chương 5, `specs/001-sr783-tro-ly-dong-bo/`, `app/` | 7 câu chuyện, 30 yêu cầu, 12 tiêu chí | `test_spec.py`, `test_app.py`, `acceptance/simulate_users.cjs` |
