<a id="mo-dau"></a>

# MỞ ĐẦU

## 1. Tính cấp thiết

Con số 7,83 Hz xuất hiện ở hai thế giới rất khác nhau. Trong địa vật lý, nó là một hiện tượng đo được,
có lịch sử hơn 70 năm, dùng để theo dõi sét toàn cầu, tầng điện ly và khí hậu nhiệt đới [3], [4], [5]. Trên
thị trường tiêu dùng, nó được gắn với "nhịp tim Trái Đất", máy phát "chống stress", nhạc "chữa lành" và
các thông tin lan truyền như "tần số Schumann đang tăng". Khoảng cách giữa hai thế giới này tạo ra rủi
ro cho người tiêu dùng (quảng cáo sai, tiền mất), rủi ro an toàn (ánh sáng nhấp nháy, âm lượng lớn) và
bỏ lỡ cơ hội (ứng dụng khoa học, giáo dục, kỹ thuật thật sự của chủ đề).

Ở Việt Nam, khung pháp lý đã có đủ công cụ để xử lý các tuyên bố sai: Luật Bảo vệ quyền lợi người tiêu
dùng 2023 [45], Luật Quảng cáo sửa đổi 2025 [46], quy định về trang thiết bị y tế [47] và các quy chuẩn
an toàn điện, tương thích điện từ [48]. Điều còn thiếu là một tài liệu tổng hợp, định lượng và kiểm
chứng được, nối cơ sở vật lý với máy tính, thiết bị và người dùng.

## 2. Mục tiêu và yêu cầu đặt hàng

| Mã | Yêu cầu đặt hàng | Mục tiêu nghiên cứu | Nơi đáp ứng |
|---|---|---|---|
| R0 | Báo cáo chuẩn quốc gia | Trình bày theo cấu trúc báo cáo tổng hợp nhiệm vụ KH&CN [51], thể thức văn bản theo [50] khi xuất DOCX/PDF | Toàn bộ |
| R1 | Nghiên cứu chuyên sâu lĩnh vực AI và máy tính | Xử lý tín hiệu, học máy cho dữ liệu Schumann, BCI, sinh tín hiệu, truyền thông, an ninh | [Chương 2](03-chuong-2-ai-may-tinh.md#c2) |
| R2 | Nghiên cứu chuyên sâu thiết bị đầu cuối, sản phẩm cuối | Phân loại sản phẩm, định lượng trường, khả năng đo của điện thoại, bằng chứng, pháp lý, kiểm định | [Chương 3](04-chuong-3-thiet-bi-dau-cuoi.md#c3) |
| R3 | Liên kết chặt chẽ, chuyên sâu tầng bit | Chuỗi từ 1 pT đến từng bit; mã Hamming, SHA-256; đối chiếu bit Python ↔ JavaScript | [Chương 4](05-chuong-4-tang-bit.md#c4) |
| R4 | Đặc tả thiết bị phần mềm có hội thoại và đồng bộ tần số trên thiết bị đa năng | Đặc tả theo Spec Kit [53], bản mẫu chạy được, nghiệm thu mô phỏng người dùng | [Chương 5](06-chuong-5-dac-ta-sr783.md#c5) |

## 3. Đối tượng và phạm vi

- **Đối tượng**: cộng hưởng Schumann mode 1 (danh nghĩa 7,83 Hz) và các tín hiệu nhân tạo ở cùng tần số
  (âm thanh, ánh sáng, từ trường của thiết bị).
- **Phạm vi**: nghiên cứu tài liệu, mô hình định lượng, tính toán tầng bit, mô phỏng, xây dựng và kiểm
  thử phần mềm. Báo cáo **không** thực hiện thử nghiệm lâm sàng và **không** đo đạc phần cứng thật; các
  giá trị trường của máy phát là ước lượng từ mô hình cuộn dây có giả định nêu rõ.

## 4. Phương pháp nghiên cứu

1. **Tổng quan tài liệu có xác minh**: 53 tài liệu, mỗi tài liệu gắn trạng thái V1–V3; phát biểu về tác
   dụng gắn mức bằng chứng A–D.
2. **Mô hình hóa định lượng**: công thức khoang cộng hưởng, định luật Biot–Savart cho cuộn dây, chuỗi
   Fourier cho chuỗi xung, giới hạn Shannon.
3. **Tính toán tầng bit bằng số học hữu tỉ**: không dùng số thực ở những nơi cần chính xác tuyệt đối
   (IEEE 754, DDS, thanh ghi, pha, SECDED); kết quả tái lập trùng từng byte.
4. **Thí nghiệm học máy tái lập**: dữ liệu mô phỏng sinh bằng SplitMix64 [25], so sánh 5 phương pháp.
5. **Kỹ thuật đặc tả**: quy trình Spec-Driven Development của Spec Kit (spec → plan → tasks) [53].
6. **Kiểm thử và nghiệm thu**: bộ kiểm thử tự động, đối chiếu bit hai ngôn ngữ, mô phỏng 6 kiểu người
   dùng, đo nhấp nháy theo khung hình, niêm phong SHA-256 có bảo vệ mã Hamming.

## 5. Cấu trúc báo cáo

Ngoài Mở đầu, báo cáo gồm 6 chương, danh mục tài liệu tham khảo và phụ lục. Chương 1 trình bày cơ sở
vật lý; Chương 2 và 3 đáp ứng R1 và R2; Chương 4 đáp ứng R3; Chương 5 đáp ứng R4; Chương 6 tổng hợp
kết luận và kiến nghị. Phụ lục hướng dẫn tái lập, ghi kết quả kiểm thử và cung cấp phiếu kiểm định mẫu.
