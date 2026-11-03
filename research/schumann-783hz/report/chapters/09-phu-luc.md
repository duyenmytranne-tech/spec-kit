<a id="phu-luc"></a>

# PHỤ LỤC

<a id="pl-a"></a>

## Phụ lục A. Hướng dẫn tái lập

Yêu cầu: Python ≥ 3.9 (chỉ thư viện chuẩn) cho mọi tính toán; pytest cho bộ kiểm thử; pandoc,
Node.js + Playwright/Chromium để dựng HTML/PDF/DOCX và chạy mô phỏng người dùng.

```bash
cd research/schumann-783hz
python tools/compute_results.py --check     # results.json trùng từng byte
python tools/build_figures.py --check       # 9 hình SVG trùng từng byte
python tools/build_app.py --check           # ứng dụng = mẫu + cơ sở tri thức
python tools/build_report.py --check        # báo cáo tổng hợp = ghép các chương
python -m pytest tests -q                   # bộ kiểm thử tự động
node acceptance/simulate_users.cjs          # mô phỏng 7 kiểu người dùng
python -m sr783 verify                      # SHA256SUMS + gốc băm + gốc SECDED
sha256sum -c SHA256SUMS                     # kiểm tra độc lập bằng công cụ hệ điều hành
```

<a id="pl-b"></a>

## Phụ lục B. Bản đồ số liệu

| Bảng / Hình | Khóa trong `results/results.json` | Mã sinh |
|---|---|---|
| Bảng 1.1, Hình 1 | `physics.cavity` | `sr783/physics.py: cavity_modes` |
| Bảng 1.2 | `physics.diurnal_vn` | `physics.diurnal_vn` |
| Bảng 2.1 | `physics.adc` | `physics.adc_dynamic_range` |
| Bảng 2.2, Hình 7, Hình 9 | `ml` | `sr783/srml.py: run` |
| Bảng 2.3, Hình 5 | `synth.display` | `sr783/synth.py: display_frames` |
| Bảng 2.4, Hình 4 | `synth.dds`, `synth.dds_curves` | `synth.dds`, `synth.dds_error_curve` |
| Bảng 2.5 | `synth.timer1` | `synth.avr_timer1_ctc` |
| Bảng 2.6 | `synth.clock_tolerance`, `synth.ne555` | `synth.clock_tolerance`, `synth.ne555` |
| Bảng 2.7 | `physics.shannon` | `physics.shannon_table` |
| Bảng 3.2, Hình 2 | `physics.generator`, `physics.field_ladder`, `physics.icnirp` | `physics.generator_table` |
| Hình 6 | `synth.harmonics` | `synth.pulse_harmonics` |
| Bảng 4.2, Hình 3 | `bits` | `sr783/bits.py: representations` |
| Bảng 4.3, 4.4 | `synth.phase_vectors`, `synth.offset_phase_error` | `synth.phase_vector` |
| Bảng 4.5 | `secded.fault_injection` | `tools/compute_results.py: secded_examples` |
| Mục 4.5 | `integrity`, `prng` | `sr783/integrity.py`, `sr783/prng.py` |

<a id="pl-c"></a>

## Phụ lục C. Kết quả kiểm thử và nghiệm thu

**C.1. Bộ kiểm thử tự động** (`python -m pytest tests`): 48/48 đạt, gồm lõi bit (IEEE 754, DDS, Timer1, pha,
SplitMix64, WAV, CLI), SECDED (vét cạn SECDED(8,4); ngẫu nhiên SECDED(22,16), SECDED(72,64); bảo vệ gốc
băm), SHA-256 và niêm phong (tiêm lỗi vào bản sao gói), tái lập trùng từng byte (`results.json`, 9 hình,
ứng dụng, báo cáo), kiểm tra độc lập bằng `sha256sum -c`, tính nhất quán của báo cáo (53 tài liệu đều được trích, mọi liên kết nội bộ, 9 hình,
hơn 50 con số đối chiếu với `results.json`), đặc tả Spec Kit (đề mục theo mẫu, FR-001…FR-030,
SC-001…SC-012, danh mục kiểm tra, hợp đồng khớp vector) và tệp ứng dụng (khế ước Artifact, ngoại tuyến,
cơ sở tri thức nhúng nguyên văn, không có cấu trúc nhấp nháy).

**C.2. Mô phỏng người dùng** (`node acceptance/simulate_users.cjs`, Chromium): 67/67 phép kiểm đạt.

| Kiểu người dùng | Phép kiểm chính | Kết quả |
|---|---|---|
| P6 Kỹ sư phần mềm | 27 phép đối chiếu bit Python ↔ JavaScript; băm cơ sở tri thức; WAV Python so với JavaScript | 27/27; băm trùng; 48 000 mẫu, 0 mẫu khác |
| P1 Người dùng phổ thông (điện thoại) | hỏi đáp qua giao diện, lệnh bắt đầu/dừng, câu khủng hoảng; bộ câu hỏi chuẩn; bề rộng 360 px | 44/44 chủ đề, 3/3 khủng hoảng, 3/3 y tế, 10/10 lệnh, 4/4 câu không bị hiểu nhầm là lệnh; không cuộn ngang |
| P2 Nhóm đồng bộ (2 thiết bị, đồng hồ lệch 3 ms) | tạo/tham gia mã phiên; pha cùng thời điểm; lệch pha; mã sai | pha trùng tuyệt đối; 20/20 lần < 10°, trung bình ≈ 8,5° (lý thuyết 8,46°); mã sai bị từ chối |
| P3 Kỹ sư kiểm định | dữ liệu mẫu 7,85 Hz; nhiễu thuần; CSV Schumann có dòng kém và ngoài dải | 7,8498 Hz, Đạt; Không xác định; chọn 7,792 Hz → 974/125; từ chối 9,6 Hz |
| P4 Kiểm thử độ bền | lật 1 bit ở cả 144 vị trí; 400 cặp lỗi 2 bit; chuỗi băm | 144/144 tự sửa; 400/400 phát hiện và khôi phục; chuỗi hợp lệ, phát hiện sửa đổi |
| P5 Người nhạy cảm ánh sáng | ghi hình ≈ 60 khung/s trong khi phát; giao diện tối | 0 lần nhấp nháy/giây; bước độ chói lớn nhất dưới 0,01; màu nền tối đúng token |
| P7 Người đọc báo cáo | liên kết nội bộ, hình trong bản HTML | 24 liên kết, 0 hỏng; 9/9 hình hiển thị |

**C.3. Lỗi phát hiện trong vòng nghiệm thu và cách khắc phục** ("thất bại là tài sản của nghiên cứu")

| # | Phát hiện | Nguyên nhân | Khắc phục | Kiểm lại |
|---|---|---|---|---|
| 1 | Bộ câu hỏi chuẩn chỉ đạt 37/44 | Từ khóa quá chung ("7 83", "schumann") lấn át chủ đề cụ thể | Bỏ từ khóa chung, thêm lớp dự phòng chung | 44/44 |
| 2 | "tần số 7.83 có nguy hiểm không" bị hiểu là lệnh đặt tần số | Biểu thức lệnh quá rộng | Lệnh tần số phải kết thúc ngay sau con số | 4/4 câu không thành lệnh |
| 3 | Phép đo nhấp nháy chỉ 8,6 rồi 15,2 khung/s | Chụp ảnh tuần tự chậm hơn ngưỡng Nyquist 15,66 khung/s | Dùng luồng khung hình của bộ tổng hợp hiển thị | ≈ 60 khung/s, 0 nhấp nháy |
| 4 | Lệch pha đo được 10,15° khi đồng hồ chỉ lệch 3 ms | Pha tính theo mili giây nguyên, lượng tử ±1 ms (±2,82°) | Đồng hồ micro giây hiệu chuẩn; cập nhật hợp đồng | 20/20 lần < 10°, sai lý thuyết < 0,1° |
| 5 | Kiểm thử đòi ≥ 30 nhiệm vụ đã làm | Kỳ vọng sai của chính bài kiểm thử | Kiểm đúng 28 đã làm + 4 việc phần cứng tương lai | đạt |
| 6 | `sha256sum -c` báo 1 tệp sai dù `sr783 verify` đạt | Lệnh pandoc đầu tiên dùng `-o -` tạo tệp tạm tên "-"; `sha256sum` hiểu "-" là đầu vào chuẩn | Sửa lệnh; chuyển (không xóa) tệp tạm ra khỏi gói; cấm tên tệp bắt đầu bằng "-"; thêm kiểm thử bằng `sha256sum` | `sha256sum -c` đạt |
| 7 | markdownlint (bước CI của kho mã) báo 148 lỗi trên tệp Markdown mới | Danh mục tài liệu đánh số liên tục qua nhiều danh sách; trích dẫn liền nhau bị hiểu là liên kết tham chiếu; liên kết chéo giữa các tệp chương; dấu "\|" trong ô bảng | Đổi định dạng danh mục, tách trích dẫn, liên kết chéo dạng tệp#neo (tự chuyển khi ghép), bỏ dấu "\|" khỏi ô bảng | 0 lỗi với markdownlint 0.18 và 0.24 |
| 8 | `git diff --check` (bước CI) báo khoảng trắng cuối dòng | CSS tô màu mã do pandoc sinh | Bước dựng HTML loại khoảng trắng cuối dòng | sạch |

<a id="pl-d"></a>

## Phụ lục D. Thuật ngữ Anh – Việt

| Tiếng Anh | Tiếng Việt |
|---|---|
| Schumann resonance | cộng hưởng Schumann |
| Earth–ionosphere cavity / waveguide | khoang / ống dẫn sóng Trái Đất – tầng điện ly |
| quality factor (Q) | hệ số phẩm chất |
| induction coil magnetometer | từ kế cuộn cảm ứng |
| Lorentzian fit | khớp hàm Lorentz |
| Welch periodogram | phổ Welch |
| phase accumulator, tuning word | bộ tích lũy pha, từ điều chỉnh |
| clear timer on compare match (CTC) | xóa bộ định thời khi so khớp |
| binaural beats, isochronic tones | nhịp phách hai tai, âm đẳng thời |
| sampled sinusoidal stimulation | kích thích hình sin lấy mẫu |
| covert channel, air gap | kênh ẩn, cách ly vật lý |
| syndrome, overall parity | hội chứng, bit chẵn lẻ tổng |
| manifest, root hash, hash chain | tệp kê khai, gốc băm, chuỗi băm |
| clock offset, drift, slewing | lệch đồng hồ, trôi, bù dần |

<a id="pl-e"></a>

## Phụ lục E. Toàn vẹn gói nghiên cứu

1. `SHA256SUMS` chứa băm SHA-256 của mọi tệp trong `research/schumann-783hz/` (trừ chính nó và hai
   tệp gốc băm), sắp xếp theo đường dẫn, định dạng của `sha256sum`.
2. `ROOT_HASH.txt` = SHA-256 của nội dung `SHA256SUMS`.
3. `ROOT_HASH.secded.txt` chứa 4 từ mã SECDED(72,64) (18 ký tự hex mỗi dòng) của 256 bit gốc băm.
4. `python -m sr783 verify` tính lại mọi băm, so với `SHA256SUMS`, so gốc băm, giải mã và sửa lỗi
   bản gốc SECDED; kết quả `ok: true` nghĩa là toàn gói đồng nhất đến từng bit với bản đã niêm phong.
5. Tệp `.gitattributes` cố định ký tự xuống dòng LF để băm không đổi khi lấy mã về trên Windows.
