<a id="top"></a>

# BÁO CÁO TỔNG HỢP KẾT QUẢ NGHIÊN CỨU

**NGHIÊN CỨU CHUYÊN SÂU VỀ TẦN SỐ 7,83 Hz (CỘNG HƯỞNG SCHUMANN): CƠ SỞ VẬT LÝ, ỨNG DỤNG TRONG AI – MÁY TÍNH, THIẾT BỊ ĐẦU CUỐI, LIÊN KẾT TẦNG BIT VÀ ĐẶC TẢ PHẦN MỀM ĐỒNG BỘ SR783**

| Mục | Nội dung |
|---|---|
| Mã báo cáo | SR783-BC-2026-01 |
| Phiên bản | 1.0 – bản thảo khoa học |
| Ngày hoàn thành | 03/11/2026 |
| Loại tài liệu | Báo cáo tổng hợp kết quả nghiên cứu, trình bày theo cấu trúc báo cáo tổng hợp nhiệm vụ khoa học và công nghệ [51] |
| Tổ chức chủ trì, chủ nhiệm | Để trống cho đơn vị chủ trì điền khi trình duyệt chính thức |
| Soạn thảo | Trợ lý AI Claude (Anthropic) qua Claude Code, theo yêu cầu của chủ kho mã `duyenmytranne-tech/spec-kit` |
| Trạng thái thẩm định | Đã kiểm thử tự động và mô phỏng người dùng; **cần hội đồng chuyên gia thẩm định trước khi dùng cho mục đích chính thức** |
| Gói tái lập | `research/schumann-783hz/` (mã nguồn, dữ liệu, hình, kiểm thử, ứng dụng, đặc tả) |
| Toàn vẹn | Mọi tệp liệt kê trong `SHA256SUMS`; gốc băm trong `ROOT_HASH.txt`, bản bảo vệ SECDED(72,64) trong `ROOT_HASH.secded.txt` |

## TÓM TẮT

Tần số 7,83 Hz là giá trị danh nghĩa của mode cơ bản cộng hưởng Schumann: dao động điện từ tần số cực
thấp trong khoang giữa mặt đất và tầng điện ly, được sét toàn cầu (khoảng 44 ± 5 tia mỗi giây) kích thích
liên tục [1], [2], [3], [6]. Báo cáo này nghiên cứu chủ đề theo bốn yêu cầu đặt hàng: (R1) ứng dụng trong AI
và máy tính; (R2) thiết bị đầu cuối và sản phẩm cuối cho người dùng; (R3) liên kết chặt chẽ đến tầng bit;
(R4) đặc tả một "thiết bị phần mềm" cho phép người dùng trò chuyện và đồng bộ tần số trên các thiết bị
đa năng.

Kết quả chính: (1) Mode quan sát thấp hơn mô hình khoang lý tưởng (7,83 so với 10,59 Hz, tỉ số 0,739) và
dao động trong khoảng 7,5–8 Hz; không có bằng chứng tần số "đang tăng". (2) Từ trường tự nhiên chỉ cỡ
1 pT, nhỏ hơn mức tham chiếu công chúng của ICNIRP ở 7,83 Hz (652,4 µT) khoảng 6,5·10⁸ lần; điện thoại
không thể đo cộng hưởng Schumann (1 pT bằng 6,667·10⁻⁶ bước số của từ kế), nhưng kiểm chứng được máy
phát 7,83 Hz ở cự ly dưới 3,33 cm. (3) Chưa có bằng chứng lâm sàng vững chắc về lợi ích sức khỏe; ánh
sáng nhấp nháy 7,83 lần/giây là rủi ro thật với người nhạy cảm ánh sáng. (4) Trong thí nghiệm tái lập
với 400 phổ kiểm thử, phương pháp lai học máy + khớp Lorentz đạt sai số tuyệt đối trung bình 0,0299 Hz,
tốt hơn 11 lần cách lấy đỉnh cực đại (0,3283 Hz). (5) Ở tầng bit, 7,83 Hz được phân tích từ biểu diễn
IEEE 754 (`0x40FA8F5C`), từ điều chỉnh tổng hợp số (700617 ở 48 kHz, +0,6563 ppm) đến thanh ghi vi điều
khiển (OCR1A = 15963, +15,040 ppm). (6) Bản đặc tả SR783 theo chuẩn Spec Kit và bản mẫu chạy được trên
trình duyệt đã đạt 100 % phép đối chiếu bit Python ↔ JavaScript, 44/44 câu hỏi chuẩn, 100 % lỗi 1 bit
được tự sửa và 100 % lỗi 2 bit được phát hiện.

**Từ khóa**: cộng hưởng Schumann; 7,83 Hz; tần số cực thấp (ELF); học máy; khớp Lorentz; tổng hợp số
trực tiếp; IEEE 754; mã Hamming SECDED; SHA-256; đồng bộ pha; thiết bị đầu cuối; bảo vệ người tiêu dùng.

## MỤC LỤC

- [Mở đầu](01-mo-dau.md#mo-dau)
- [Chương 1. Cơ sở vật lý của tần số 7,83 Hz](02-chuong-1-vat-ly.md#c1)
- [Chương 2. 7,83 Hz trong lĩnh vực AI và máy tính](03-chuong-2-ai-may-tinh.md#c2)
- [Chương 3. Thiết bị đầu cuối và sản phẩm cuối cho người dùng](04-chuong-3-thiet-bi-dau-cuoi.md#c3)
- [Chương 4. Liên kết chặt chẽ đến tầng bit](05-chuong-4-tang-bit.md#c4)
- [Chương 5. Đặc tả phần mềm và thiết bị trung gian SR783](06-chuong-5-dac-ta-sr783.md#c5)
- [Chương 6. Thảo luận, hạn chế, kết luận và kiến nghị](07-chuong-6-ket-luan-kien-nghi.md#c6)
- [Tài liệu tham khảo](08-tai-lieu-tham-khao.md#tltk)
- [Phụ lục](09-phu-luc.md#phu-luc)

## DANH MỤC CHỮ VIẾT TẮT

| Viết tắt | Tiếng Anh | Tiếng Việt |
|---|---|---|
| ADC | Analog-to-Digital Converter | Bộ chuyển đổi tương tự – số |
| AI / ML | Artificial Intelligence / Machine Learning | Trí tuệ nhân tạo / học máy |
| BCI | Brain–Computer Interface | Giao diện não – máy tính |
| BCD | Binary-Coded Decimal | Số thập phân mã hóa nhị phân |
| CTC | Clear Timer on Compare match | Chế độ xóa bộ định thời khi so khớp |
| DDS | Direct Digital Synthesis | Tổng hợp số trực tiếp |
| DFT / FFT | (Fast) Discrete Fourier Transform | Biến đổi Fourier rời rạc (nhanh) |
| EEG | Electroencephalography | Điện não đồ |
| ELF | Extremely Low Frequency | Tần số cực thấp (3–3000 Hz) |
| EMC | Electromagnetic Compatibility | Tương thích điện từ |
| ICNIRP | International Commission on Non-Ionizing Radiation Protection | Ủy ban Quốc tế về bảo vệ bức xạ không ion hóa |
| LSB | Least Significant Bit | Bit (bước số) nhỏ nhất |
| MAE / RMSE | Mean Absolute / Root-Mean-Square Error | Sai số tuyệt đối trung bình / căn quân phương |
| PEMF | Pulsed Electromagnetic Field | Trường điện từ xung |
| ppm / ppb | parts per million / billion | phần triệu / phần tỉ |
| SECDED | Single-Error-Correct, Double-Error-Detect | Sửa lỗi đơn, phát hiện lỗi kép |
| SNR | Signal-to-Noise Ratio | Tỉ số tín hiệu trên nhiễu |
| SR | Schumann Resonance | Cộng hưởng Schumann |
| SSVEP | Steady-State Visual Evoked Potential | Điện thế gợi thị giác trạng thái ổn định |
| UT / UTC | Universal Time (Coordinated) | Giờ quốc tế (phối hợp) |
| WCAG | Web Content Accessibility Guidelines | Hướng dẫn tiếp cận nội dung web |

## QUY ƯỚC TRÌNH BÀY

1. **Số và đơn vị**: văn bản dùng dấu phẩy thập phân theo quy ước tiếng Việt (7,83 Hz) và khoảng trắng
   ngăn nhóm nghìn (38 288 km); mã nguồn, giá trị thập lục phân và đầu ra máy tính giữ dấu chấm theo
   chuẩn lập trình (`7.83`). Đơn vị theo hệ SI; 1 pT = 10⁻¹² T, 1 µT = 10⁻⁶ T.
2. **Bit**: tiền tố `0x` cho hệ thập lục phân; chuỗi bit viết từ bit cao nhất sang bit thấp nhất.
3. **Mức bằng chứng** cho mọi phát biểu về tác dụng:
   **A** – mạnh (đo đạc lặp lại, tiêu chuẩn, văn bản chính thức);
   **B** – trung bình (nghiên cứu có kiểm soát, tổng quan còn giới hạn);
   **C** – yếu/sơ bộ (mẫu nhỏ, thí nghiệm tế bào, kết quả mâu thuẫn);
   **D** – không có bằng chứng hoặc đã bị bác bỏ.
4. **Trạng thái xác minh tài liệu**: **V1** – đã đối chiếu thư mục và số liệu then chốt qua nguồn độc
   lập khi soạn; **V2** – đã đối chiếu thư mục, nội dung theo tóm tắt hoặc nguồn thứ cấp; **V3** – theo
   tài liệu kỹ thuật phổ biến, cần đối chiếu bản gốc trước khi dùng cho mục đích pháp lý.
5. **Tái lập**: mọi con số do tính toán sinh ra đều lấy từ `results/results.json`, được tái tạo trùng
   từng byte bằng `python tools/compute_results.py --check`.
