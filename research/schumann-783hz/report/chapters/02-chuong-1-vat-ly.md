<a id="c1"></a>

# CHƯƠNG 1. CƠ SỞ VẬT LÝ CỦA TẦN SỐ 7,83 Hz

## 1.1. Lịch sử phát hiện

Năm 1952, W. O. Schumann chứng minh về lý thuyết rằng khoảng không giữa một quả cầu dẫn điện (Trái Đất)
và một lớp vỏ dẫn điện (tầng điện ly) có các dao động riêng không bức xạ ra ngoài [1]. Năm 1960, Balser
và Wagner công bố bằng chứng thực nghiệm đầu tiên về các cộng hưởng này trên tạp chí *Nature* [2]. Từ
đó, mạng lưới trạm đo trên khắp thế giới ghi nhận liên tục các mode quanh 7,8; 14,3; 20,8; 27,3 và
33,8 Hz [3], [4]. Năm 2011, vệ tinh C/NOFS phát hiện dấu hiệu cộng hưởng Schumann ở độ cao khoảng
400–800 km, phía trên "trần" của khoang, buộc các mô hình phải tính tới biên dưới "rò" của tầng điện ly [7].

## 1.2. Cơ chế: khoang cộng hưởng Trái Đất – tầng điện ly

Mặt đất và nước biển dẫn điện tốt; tầng điện ly (độ cao khoảng 60–100 km) cũng dẫn điện. Khoảng không
giữa chúng là một ống dẫn sóng hình cầu. Mỗi tia sét là một xung điện từ băng rộng; phần năng lượng ở tần
số cực thấp (ELF) lan quanh Trái Đất với suy hao rất nhỏ. Khi bước sóng xấp xỉ chu vi Trái Đất, các sóng
đi vòng quanh giao thoa tăng cường, tạo cộng hưởng. Vệ tinh OTD ước lượng trung bình 44 ± 5 tia sét
mỗi giây trên toàn cầu (khoảng 1,4 tỉ tia mỗi năm), chủ yếu trên đất liền nhiệt đới [6], nên khoang
luôn được "gõ" liên tục.

## 1.3. Tần số lý tưởng và tần số quan sát

Với khoang không tổn hao bán kính a, các mode là f_n = c/(2πa)·√(n(n+1)). Lấy c = 299 792 458 m/s và
a = 6 371 008,8 m (bán kính trung bình IUGG) cho c/(2πa) = 7,4892 Hz.

**Bảng 1.1.** Tần số mode lý tưởng và quan sát (nguồn tính: `results.json → physics.cavity`)

| Mode n | Lý tưởng (Hz) | Quan sát danh nghĩa (Hz) | Tỉ số quan sát/lý tưởng |
|---|---|---|---|
| 1 | 10,59 | 7,83 | 0,739 |
| 2 | 18,34 | 14,30 | 0,780 |
| 3 | 25,94 | 20,80 | 0,802 |
| 4 | 33,49 | 27,30 | 0,815 |
| 5 | 41,02 | 33,80 | 0,824 |

Tần số quan sát thấp hơn vì tầng điện ly dẫn điện hữu hạn và có cấu trúc theo độ cao, làm khoang tổn hao
và "chậm" sóng [3]. Bước sóng của mode 1 là c/7,83 Hz ≈ 38 288 km, bằng 0,9565 chu vi Trái Đất
(40 030 km): con số 7,83 Hz về bản chất là "tần số có bước sóng bằng vòng quanh hành tinh".

![Hình 1. Phổ cộng hưởng Schumann minh họa và tần số khoang lý tưởng](figures/fig1_sr_spectrum.svg)

## 1.4. Đặc trưng định lượng

- **Biên độ**: thành phần từ của mode 1 hiếm khi vượt 1 pT; điện trường thường được dẫn ở mức dưới
  hoặc khoảng 1 mV/m (số liệu điện trường kém thống nhất giữa các nguồn) [3], [4].
- **Hệ số phẩm chất Q = f_n/Δf_n** thấp, cỡ khoảng 4 đến 10 tùy mode và điều kiện, tức đỉnh phổ rộng
  (độ rộng toàn phần cỡ 1–2,5 Hz ở mode 1) [3], [4].
- **Biến thiên**: tần số mode 1 dao động trong khoảng xấp xỉ 7,5–8 Hz theo giờ trong ngày, mùa, chu kỳ
  Mặt Trời; các sự kiện tia X và proton Mặt Trời làm dịch tần số, còn biên độ chủ yếu theo hoạt động sét [8].
- **Chu kỳ ngày đêm**: cường độ thường cực đại khi các "ống khói" giông sét nhiệt đới hoạt động mạnh
  vào chiều tối địa phương [3], [4]:

**Bảng 1.2.** Cực đại cường độ cổ điển theo UT và giờ Việt Nam (UTC+7) (nguồn: `physics.diurnal_vn`)

| UT | Giờ Việt Nam | Vùng sét chủ đạo |
|---|---|---|
| 08 giờ | 15 giờ | châu Á – Hải đảo Đông Nam Á |
| 14 giờ | 21 giờ | châu Phi |
| 20 giờ | 03 giờ sáng hôm sau | châu Mỹ |

Việt Nam nằm sát "ống khói" Hải đảo Đông Nam Á, một trong ba vùng sét lớn nhất thế giới; một trạm ELF
đặt tại Việt Nam sẽ có góc nhìn gần nguồn hiếm có.

## 1.5. Quan trắc

- **Trạm mặt đất**: dùng từ kế cuộn cảm ứng (đo hai thành phần từ ngang) và ăng-ten điện trường, đặt xa
  đường dây điện. Trạm Hylaty (Ba Lan) đo dải 0,03–300 Hz với đồng hồ đồng bộ GPS [10]; trạm Sierra
  Nevada (Tây Ban Nha) công bố chương trình Python xử lý bản ghi 10 phút bằng phương pháp Welch trên dải
  6–25 Hz, có bước loại nhiễu nhân tạo, trích biên độ, tần số và độ rộng mode [11].
- **Vệ tinh**: C/NOFS ghi được hàng chục nghìn trường hợp ở độ cao 400–800 km [7].
- **Hành tinh khác**: tàu Huygens ghi tín hiệu quanh 36 Hz trên Titan, được giải thích là mode thứ hai
  của cộng hưởng kiểu Schumann do plasma từ quyển Sao Thổ kích thích [9].
- **Việt Nam**: đài địa từ Phú Thụy (mã PHU, 21,029° B; 105,958° Đ) hoạt động từ năm 1978 và là thành
  viên INTERMAGNET [12], nhưng đo từ trường địa từ tần số thấp, không phải phổ ELF cộng hưởng Schumann.
  Chưa ghi nhận trạm quan trắc Schumann chuyên dụng công khai ở Việt Nam: đây là khoảng trống nghiên cứu.

## 1.6. Ứng dụng khoa học đã được kiểm chứng

| Ứng dụng | Cơ sở | Bằng chứng |
|---|---|---|
| Theo dõi hoạt động sét toàn cầu | Sét là nguồn kích thích duy nhất đáng kể [3], [6] | A |
| "Nhiệt kế nhiệt đới toàn cầu" | Biên độ dài hạn tương quan với dị thường nhiệt độ nhiệt đới [5] | B |
| Theo dõi tầng điện ly, thời tiết không gian | Tần số dịch theo tia X, proton Mặt Trời [8] | A |
| Nghiên cứu khí quyển hành tinh | Cộng hưởng kiểu Schumann trên Titan [9] | B |
| Dự báo động đất | Nghiên cứu thăm dò, chưa kiểm chứng [14], [15] | C |

## 1.7. Những ngộ nhận phổ biến

**Bảng 1.3.** Đối chiếu tuyên bố phổ biến với bằng chứng

| Tuyên bố | Thực tế | Mức | Tài liệu |
|---|---|---|---|
| "7,83 Hz là nhịp tim Trái Đất, luôn cố định" | Là ẩn dụ phổ thông; tần số dao động khoảng 7,5–8 Hz | A | [3], [8] |
| "Tần số Schumann đang tăng lên 13 Hz, 40 Hz" | Không có dữ liệu khoa học ủng hộ; ảnh phổ đồ lan truyền có vạch do sét gần, mất dữ liệu, sự cố thiết bị | D | [42], [43], [44] |
| "7,83 Hz chính là sóng não alpha" | Theo IFCN, alpha là 8–13 Hz; theta là 4 đến dưới 8 Hz, nên 7,83 Hz thuộc theta trên | A | [33] |
| "NASA lắp máy phát Schumann trên tàu vũ trụ" | Không có tài liệu công khai; công trình thật của NASA là phát hiện SR từ vệ tinh | D | [7], [44] |
| "Tần số 432 Hz, 528 Hz chữa lành, liên quan Schumann" | Không có bằng chứng; Schumann là sóng điện từ, không phải âm thanh | D | [3] |
