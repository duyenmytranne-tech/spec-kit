<a id="c6"></a>

# CHƯƠNG 6. THẢO LUẬN, HẠN CHẾ, KẾT LUẬN VÀ KIẾN NGHỊ

## 6.1. Thảo luận tổng hợp

Ba lớp sự thật về 7,83 Hz cần được tách bạch. **Lớp vật lý** vững chắc: cộng hưởng Schumann có thật,
đo được liên tục, dùng được cho khoa học khí quyển và tầng điện ly. **Lớp kỹ thuật** cũng vững chắc và
định lượng được đến từng bit: cách sinh, đo, biểu diễn, truyền và bảo vệ tín hiệu 7,83 Hz trong máy tính
và thiết bị. **Lớp sức khỏe** hiện chủ yếu ở mức C–D: một số thí nghiệm sơ bộ thú vị, nhưng chưa có
bằng chứng lâm sàng đủ để quảng cáo tác dụng. Rủi ro sức khỏe rõ ràng nhất lại nằm ở hình ảnh nhấp nháy
7,83 lần/giây, không nằm ở từ trường yếu.

Từ đó, cách "tận dụng tối đa" 7,83 Hz một cách có trách nhiệm là đặt sản phẩm vào lớp vật lý và kỹ thuật:
giáo dục, đồng bộ hoạt động nhóm, kiểm chứng thiết bị, nghiên cứu dữ liệu ELF bằng AI, và trải nghiệm
thư giãn có nhãn trung thực. SR783 được đặc tả và xây dựng theo đúng định hướng đó.

## 6.2. Hạn chế của nghiên cứu

1. Báo cáo là nghiên cứu tài liệu, mô hình và mô phỏng; chưa có phép đo phần cứng hay thử nghiệm trên người.
2. Thí nghiệm học máy dùng phổ mô phỏng; kết quả cần được kiểm định lại trên dữ liệu trạm thật [11].
3. Một số tài liệu chỉ xác minh được qua tóm tắt hoặc nguồn thứ cấp (trạng thái V2–V3); các giá trị
   ICNIRP cần đối chiếu bảng gốc trước khi dùng cho mục đích pháp lý.
4. Trường của máy phát là ước lượng từ mô hình cuộn dây; sản phẩm thật có thể khác nhiều.
5. Báo cáo do trợ lý AI soạn thảo; đã kiểm thử tự động nhưng cần hội đồng chuyên gia thẩm định.

## 6.3. Kết luận

1. 7,83 Hz là giá trị danh nghĩa của mode 1 cộng hưởng Schumann; tần số thực dao động khoảng 7,5–8 Hz,
   thấp hơn mô hình khoang lý tưởng (10,59 Hz) vì tổn hao của tầng điện ly; không có bằng chứng tần số
   "đang tăng".
2. Từ trường tự nhiên khoảng 1 pT, nhỏ hơn mức tham chiếu công chúng ICNIRP ở 7,83 Hz (652,4 µT) khoảng
   6,5·10⁸ lần; máy phát tiêu dùng mẫu chỉ tạo 62,8 pT ở 1 m.
3. Điện thoại không đo được cộng hưởng Schumann (thiếu khoảng 17 bậc nhị phân độ phân giải), nhưng
   kiểm chứng được tần số máy phát ở cự ly dưới 3,33 cm.
4. AI có giá trị thực trong xử lý dữ liệu Schumann; phương pháp lai học máy + khớp Lorentz đạt
   MAE 0,0299 Hz, không có mẫu sai quá 0,2 Hz trong 400 phổ kiểm thử.
5. Ở tầng bit, chất lượng một sản phẩm "7,83 Hz" do nguồn dao động quyết định (thạch anh ±20 ppm so với
   RC đến ±10 %), không do độ phân giải bộ tổng hợp (dưới 1 ppm ở 48 kHz, 32 bit).
6. Chưa có bằng chứng lâm sàng vững chắc về lợi ích sức khỏe của tín hiệu 7,83 Hz; ánh sáng nhấp nháy
   7,83 Hz là rủi ro thật với người nhạy cảm ánh sáng.
7. Đặc tả SR783 (Spec Kit) và bản mẫu chạy trực tiếp trên thiết bị đa năng đáp ứng yêu cầu "nói chuyện
   và đồng bộ tần số", với đồng bộ pha chính xác tuyệt đối theo số học hữu tỉ, tự sửa lỗi SECDED và niêm
   phong SHA-256.

## 6.4. Kiến nghị

**Đối với cơ quan quản lý**

1. Bộ Khoa học và Công nghệ phối hợp Bộ Y tế, Bộ Công Thương, Bộ Văn hóa, Thể thao và Du lịch rà soát
   quảng cáo sản phẩm "7,83 Hz/Schumann" có tuyên bố sức khỏe theo Luật Quảng cáo sửa đổi 2025 và Luật
   Bảo vệ quyền lợi người tiêu dùng 2023 [45], [46].
2. Yêu cầu sản phẩm có tuyên bố y tế thực hiện phân loại, công bố hoặc đăng ký lưu hành theo Nghị định
   98/2021/NĐ-CP và văn bản sửa đổi [47].
3. Nghiên cứu xây dựng hướng dẫn kỹ thuật (TCVN) về ghi nhãn và phương pháp đo cho thiết bị phát trường
   tần số cực thấp tiêu dùng, dùng phiếu kiểm định ở Bảng 3.5 làm điểm xuất phát.
4. Khuyến nghị nền tảng video áp dụng ngưỡng nhấp nháy WCAG 2.3.1 cho nội dung "tần số" [36].

**Đối với cơ sở nghiên cứu**

1. Đặt trạm quan trắc cộng hưởng Schumann thử nghiệm tại Việt Nam (gần "ống khói" sét Hải đảo Đông Nam
   Á), dữ liệu mở có SHA256SUMS và gốc băm có mã sửa lỗi; tận dụng kinh nghiệm vận hành đài địa từ Phú Thụy [12].
2. Phát triển mô hình AI lai vật lý cho dữ liệu ELF thật; công bố bộ dữ liệu và mã nguồn để tái lập.
3. Thực hiện thử nghiệm ngẫu nhiên có đối chứng, đăng ký trước, cho mọi tuyên bố về giấc ngủ, căng thẳng.

**Đối với doanh nghiệp và nhà phát triển**

1. Định vị sản phẩm 7,83 Hz là giáo dục, thư giãn, đồng bộ nhóm, kiểm chứng; ghi mức bằng chứng; không
   dùng ánh sáng nhấp nháy; giới hạn âm lượng.
2. Áp dụng hiến chương SR783 (đồng nhất đến bit, ngoại tuyến, tự sửa lỗi, niêm phong) cho phần mềm liên quan.

**Đối với người tiêu dùng**: xem mục 3.9.
