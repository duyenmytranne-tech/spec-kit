<a id="c3"></a>

# CHƯƠNG 3. THIẾT BỊ ĐẦU CUỐI VÀ SẢN PHẨM CUỐI CHO NGƯỜI DÙNG

## 3.1. Phân loại sản phẩm liên quan đến 7,83 Hz

**Bảng 3.1.** Phân loại, cơ chế, bằng chứng và khuyến nghị

| Nhóm | Ví dụ | Cơ chế vật lý | Bằng chứng tác dụng | Rủi ro chính | Khuyến nghị |
|---|---|---|---|---|---|
| A. Thiết bị đo, khoa học công dân | Từ kế cuộn cảm ứng, bộ thu ELF, cổng dữ liệu trạm | Đo SR thật | A (đo lường) | Hiểu sai ảnh phổ đồ | Kèm hướng dẫn đọc dữ liệu |
| B. Máy phát "Schumann 7,83 Hz" | Hộp nhỏ cắm USB, đặt xe, đầu giường | Cuộn dây được đóng ngắt 7,83 Hz | D cho tuyên bố sức khỏe | Quảng cáo sai; an toàn điện | Kiểm định tần số, EMC, an toàn; cấm tuyên bố chữa bệnh |
| C. Âm thanh | Nhịp phách hai tai, âm đẳng thời trên ứng dụng, video | Âm nghe được điều biên hoặc lệch tần | C | Âm lượng lớn | Giới hạn âm lượng, nhãn rõ |
| D. Hình ảnh nhấp nháy | Video "7,83 Hz", đèn chớp | Ánh sáng nhấp nháy | C | Co giật nhạy cảm ánh sáng | Không phát công khai; theo WCAG 2.3.1 |
| E. Thiết bị đeo, hỗ trợ ngủ | Băng đô, máy vi dòng, thảm PEMF có "chế độ Schumann" | Dòng điện hoặc từ trường xung | C–D | Thiết bị y tế không phép | Phân loại theo Nghị định 98/2021 nếu có mục đích y tế |
| F. Ứng dụng "đo Schumann" trên điện thoại | Ứng dụng tuyên bố đo bằng từ kế | Không khả thi vật lý | D | Thông tin sai | Thay bằng dữ liệu trạm thật |
| G. Phần mềm đồng bộ, giáo dục | SR783 (Chương 5) | Phát nhịp, kiểm chứng, giáo dục | A cho chức năng kỹ thuật | Hiểu nhầm là chữa bệnh | Mức bằng chứng trên mọi câu trả lời |

## 3.2. Máy phát "7,83 Hz": kiến trúc và độ lớn trường

Kiến trúc điển hình: nguồn USB 5 V → vi điều khiển (hoặc IC 555) → transistor → cuộn dây vài chục đến
vài trăm vòng, đóng ngắt theo xung 7,83 Hz. Mô hình tham chiếu của báo cáo: cuộn tròn phẳng 100 vòng,
dòng 10 mA, bán kính 1 cm; trường trên trục B(z) = μ0·N·I·R²/(2(R² + z²)^(3/2)).

**Bảng 3.2.** Từ trường của máy phát mẫu (nguồn: `physics.generator`)

| Khoảng cách | B | Gấp Schumann 1 pT | Số LSB từ kế điện thoại |
|---|---|---|---|
| 0 cm (tâm cuộn) | 62,8 µT | 6,28·10⁷ | 419 |
| 1 cm | 22,2 µT | 2,22·10⁷ | 148 |
| 2 cm | 5,62 µT | 5,62·10⁶ | 37,5 |
| 3 cm | 1,99 µT | 1,99·10⁶ | 13,2 |
| 5 cm | 474 nT | 4,74·10⁵ | 3,16 |
| 10 cm | 61,9 nT | 6,19·10⁴ | 0,413 |
| 30 cm | 2,32 nT | 2,32·10³ | 0,0155 |
| 1 m | 62,8 pT | 62,8 | 0,000419 |

![Hình 2. Thang độ lớn từ trường liên quan tới 7,83 Hz](figures/fig2_field_ladder.svg)

So sánh: từ trường 50 Hz trung bình trong nhà khoảng 0,07 µT (châu Âu) và 0,11 µT (Bắc Mỹ) [31]; từ
trường tĩnh Trái Đất 25–65 µT; mức tham chiếu công chúng của ICNIRP ở 7,83 Hz là 4·10⁻²/f² T = 652,4 µT
(nghề nghiệp 3262 µT), giới hạn cơ bản cho mô thần kinh trung ương 0,1/f V/m = 12,8 mV/m [30] (giá trị
được kiểm tra liên tục tại biên 8 Hz: 625,0 µT và 25 Hz: 200,0 µT). Máy phát mẫu ở 1 m mạnh hơn
Schumann khoảng 63 lần nhưng yếu hơn từ trường điện lưới trong nhà hơn 1000 lần, và nhỏ hơn mức tham
chiếu ICNIRP khoảng 10⁷ lần.

**Phổ hài**: một chuỗi xung không phải hình sin. Biên độ hài bậc n của chuỗi xung 0/A với hệ số lấp
đầy D là (2A/(nπ))·|sin(nπD)|. Sóng vuông (D = 50 %) đặt 81,06 % công suất xoay chiều ở 7,83 Hz; xung hẹp
D = 10 % chỉ đặt 21,50 %, phần còn lại rải ra 15,66; 23,49; 31,32 Hz… Một "máy phát 7,83 Hz" thực chất
phát cả một dải tần.

![Hình 6. Phổ hài của chuỗi xung 7,83 Hz](figures/fig6_pulse_harmonics.svg)

## 3.3. Điện thoại thông minh: đo được gì, không đo được gì

- **Không đo được cộng hưởng Schumann**: từ kế điện thoại AK09918 có độ nhạy điển hình 0,15 µT/LSB,
  đầu ra 16 bit, giới hạn tổng ba trục 4912 µT [29]. Tín hiệu 1 pT bằng 6,667·10⁻⁶ LSB. Muốn phân giải
  1 pT trên toàn thang cần khoảng 32,19 bit cùng nhiễu nền cỡ fT/√Hz, điều chỉ từ kế cuộn cảm ứng
  chuyên dụng đạt được [10], [11]. Các ứng dụng "đo Schumann bằng điện thoại" vì vậy không có cơ sở.
- **Kiểm chứng được máy phát ở cự ly gần**: với máy phát mẫu, tín hiệu đạt 1 LSB ở 7,42 cm và 10 LSB ở
  3,33 cm. Đặt điện thoại sát máy phát, ghi từ kế (≥ 50 mẫu/s), phân tích phổ là đủ để đo tần số thực và
  phát hiện máy phát lệch tần (chức năng "Kiểm chứng thiết bị" của SR783).
- **An ninh**: chính từ kế này cũng là bộ thu của kênh ẩn MAGNETO trong vòng khoảng 12 cm [19].

## 3.4. Âm thanh: nhịp phách hai tai và âm đẳng thời

Nhịp phách hai tai tạo bởi hai âm khác tần số ở hai tai (ví dụ 200 Hz và 207,83 Hz); nhịp 7,83 Hz chỉ
tồn tại trong cảm nhận và cần tai nghe. Âm đẳng thời là âm mang được điều biên 7,83 lần mỗi giây, nghe
được qua loa. Tổng quan hệ thống 2023 trên 14 nghiên cứu: 5 phù hợp giả thuyết "cuốn theo sóng não",
8 trái ngược, 1 hỗn hợp; phương pháp rất không đồng nhất [34]. Mức bằng chứng: C. Khuyến nghị: dùng cho
thư giãn với âm lượng nhỏ, không quảng cáo tác dụng điều trị.

Nếu mục tiêu là thư giãn, thở chậm khoảng 6 nhịp/phút (0,1 Hz) có cơ sở tốt hơn: nhiều nghiên cứu phản
hồi sinh học nhịp tim ghi nhận hiệu quả tối đa quanh nhịp này [37] (mức B). SR783 tích hợp vòng dẫn nhịp
thở chậm, không nhấp nháy.

## 3.5. Hình ảnh và ánh sáng nhấp nháy

Video "7,83 Hz" nhấp nháy toàn màn hình vi phạm tiêu chí WCAG 2.3.1 (quá 3 lần/giây trên diện tích lớn)
[36] và đặt người nhạy cảm ánh sáng (0,3–3 % dân số) vào nguy cơ co giật [35]. Đây là rủi ro sức khỏe
**có bằng chứng** duy nhất được xác định rõ trong toàn bộ nhóm sản phẩm 7,83 Hz.

## 3.6. Bằng chứng về tác động sức khỏe

**Bảng 3.3.** Tóm tắt bằng chứng

| Nghiên cứu | Thiết kế | Kết quả chính | Giới hạn | Mức |
|---|---|---|---|---|
| Elhalel và cộng sự 2019 [38] | Tế bào cơ tim chuột nuôi cấy, 7,8 Hz, 90 nT | Biên độ calci giảm, tác động chỉ trong dải 7,6–8 Hz | In vitro | C |
| Mayrovitz 2025 [39] | Thí điểm 6 nam thanh niên, 7,8 Hz tại chỗ | Giảm tưới máu da, biên độ mạch | Mẫu rất nhỏ | C |
| Saroka và cộng sự 2016 [40] | Tương quan phổ EEG và phổ SR | Phổ công suất tương tự | Tương quan, chưa lặp lại độc lập | C |
| McCraty và cộng sự 2017 [41] | 10 người, 31 ngày, HRV và từ trường | Tương quan với hoạt động địa từ | Mẫu nhỏ, quan sát | C |
| Ingendoh và cộng sự 2023 [34] | Tổng quan hệ thống 14 nghiên cứu nhịp phách hai tai | Không nhất quán | Phương pháp không đồng nhất | C |
| IARC 2002, WHO 2007 [32], [31] | Đánh giá ELF 50/60 Hz | Nhóm 2B dựa trên bệnh bạch cầu trẻ em khi trung bình > 0,3–0,4 µT; quan hệ nhân quả hạn chế | Không riêng 7,83 Hz | B |

Kết luận: chưa có bằng chứng lâm sàng đủ mạnh cho bất kỳ tác dụng điều trị nào của tín hiệu 7,83 Hz;
không có tài liệu công khai nào cho thấy NASA lắp "máy phát Schumann" trên tàu vũ trụ [44].

## 3.7. Khung pháp lý và tiêu chuẩn

**Bảng 3.4.** Văn bản áp dụng cho sản phẩm 7,83 Hz tại Việt Nam

| Vấn đề | Văn bản | Áp dụng |
|---|---|---|
| Quảng cáo trung thực | Luật Quảng cáo 16/2012/QH13, sửa đổi bởi Luật 75/2025/QH15 (hiệu lực 01/01/2026); Nghị định 342/2025/NĐ-CP [46] | Cấm tuyên bố không được chứng minh; quy định người có ảnh hưởng khi quảng cáo |
| Quyền lợi người tiêu dùng | Luật 19/2023/QH15 (hiệu lực 01/7/2024); Nghị định 55/2024/NĐ-CP [45] | Thông tin trung thực, trách nhiệm người kinh doanh |
| Trang thiết bị y tế | Nghị định 98/2021/NĐ-CP, sửa đổi bởi 07/2023/NĐ-CP và 04/2025/NĐ-CP [47] | Có mục đích y tế → phân loại A–D; loại A, B công bố tiêu chuẩn áp dụng, loại C, D đăng ký lưu hành |
| An toàn và tương thích điện từ | QCVN 4:2009/BKHCN (+SĐ 1:2016); QCVN 9:2012/BKHCN (+SĐ 1:2018) và văn bản thay thế nếu có [48] | Thiết bị điện, điện tử gia dụng |
| Phơi nhiễm trường | ICNIRP 2010 [30]; QCVN 25:2016/BYT cho 50 Hz tại nơi làm việc [49] | Tham chiếu; 7,83 Hz chưa có quy chuẩn riêng |
| Cơ quan quản lý | Bộ Khoa học và Công nghệ (sau hợp nhất với Bộ Thông tin và Truyền thông từ 01/3/2025) [52], Bộ Y tế, Bộ Công Thương, Bộ Văn hóa, Thể thao và Du lịch | Phối hợp kiểm tra |

## 3.8. Quy trình kiểm định đề xuất cho sản phẩm "7,83 Hz"

**Bảng 3.5.** Phiếu kiểm định mẫu

| Mục | Phép đo / kiểm tra | Tiêu chí đề xuất |
|---|---|---|
| K1 Tần số | Đo phổ tín hiệu (từ kế sát thiết bị hoặc đầu dò) ≥ 20 s | Giá trị tuyệt đối sai số ≤ 1 % so với công bố; ghi giá trị đo |
| K2 Độ ổn định | Đo lặp 3 lần, cách nhau 10 phút | Biến thiên ≤ 0,1 % |
| K3 Dạng sóng | Hệ số lấp đầy, phổ hài | Ghi công suất ở 7,83 Hz (%) |
| K4 Độ lớn trường | Ở 1 cm, 10 cm, 1 m | Ghi nhãn; so sánh mức tham chiếu ICNIRP |
| K5 An toàn điện | Theo QCVN 4 | Đạt |
| K6 Tương thích điện từ | Theo QCVN 9 | Đạt |
| K7 Nhãn và tuyên bố | Đối chiếu nội dung quảng cáo với bằng chứng | Không có tuyên bố chữa bệnh nếu không có đăng ký trang thiết bị y tế |
| K8 Ánh sáng | Nếu có đèn: số lần nhấp nháy/giây | ≤ 3 lần/giây hoặc dưới ngưỡng WCAG 2.3.1 |

## 3.9. Khuyến nghị cho người tiêu dùng

1. Không mua sản phẩm "7,83 Hz" vì tuyên bố chữa bệnh, chống EMF hay "đồng bộ năng lượng".
2. Nếu dùng để thư giãn, chọn âm thanh âm lượng nhỏ; tránh video nhấp nháy.
3. Người có tiền sử động kinh, dùng máy tạo nhịp tim hoặc đang mang thai nên hỏi bác sĩ trước khi dùng
   thiết bị phát tín hiệu.
4. Kiểm tra dấu hợp quy, nguồn gốc, chế độ bảo hành; dùng chức năng kiểm chứng của SR783 để đo tần số thực.
5. Gặp nguy hiểm tức thời: gọi 115.
