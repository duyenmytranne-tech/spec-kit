# SR783 Constitution

Hiến chương sản phẩm của SR783 (trợ lý hội thoại và đồng bộ tần số 7,83 Hz). Thư mục
`research/schumann-783hz/` được tổ chức như một dự án Spec Kit độc lập; hiến chương này chỉ áp
dụng cho gói nghiên cứu và sản phẩm SR783, không thay thế hiến chương của Spec Kit ở
`/.specify/memory/constitution.md` của kho mã.

## Core Principles

### I. Sự thật và an toàn trước hết (NON-NEGOTIABLE)

- Mọi phát biểu về tác dụng của 7,83 Hz MUST kèm mức bằng chứng A–D và số tài liệu tham khảo.
- Sản phẩm MUST NOT tuyên bố chẩn đoán, điều trị hay phòng ngừa bệnh.
- Câu hỏi y tế MUST nhận phản hồi khuyến nghị gặp bác sĩ; câu hỏi khủng hoảng MUST nhận ngay thông
  tin cấp cứu 115, xử lý cục bộ, không phụ thuộc mạng hay mô hình AI.

### II. Đồng nhất đến bit

- Tần số MUST được biểu diễn bằng phân số hữu tỉ p/q; pha MUST tính bằng số học số nguyên.
- Mọi giá trị trong báo cáo MUST tái sinh được bằng `tools/compute_results.py` với kết quả trùng
  từng byte; bản cài đặt JavaScript MUST cho cùng kết quả số nguyên với lõi Python (kiểm thử song
  song bắt buộc).

### III. Ngoại tuyến trước, riêng tư mặc định

- Chức năng lõi (trò chuyện cơ sở tri thức, phát nhịp, đồng bộ UTC, kiểm chứng, soi bit, toàn vẹn)
  MUST chạy không cần mạng, không tài khoản, không gửi dữ liệu đi.
- Chức năng trực tuyến (hỏi Claude, phòng nhiều thiết bị) MUST là tùy chọn, có đồng ý của người dùng
  và có đường lui ngoại tuyến.

### IV. An toàn thị giác và thính giác

- Giao diện MUST NOT có vùng sáng nhấp nháy quá 3 lần/giây (WCAG 2.3.1); 7,83 Hz chỉ được thể hiện
  bằng âm thanh và chuyển động chậm, không bằng thay đổi độ sáng.
- Âm lượng MUST bị chặn ở 50 % (−6 dBFS), có tăng/giảm dần, và giới hạn thời lượng phiên.

### V. Tự sửa lỗi và chống giả mạo

- Dữ liệu lưu MUST được bảo vệ bằng mã Hamming mở rộng SECDED và thẻ SHA-256: sửa lỗi 1 bit, phát
  hiện lỗi 2 bit và khôi phục an toàn.
- Nhật ký MUST là chuỗi băm SHA-256; gói phát hành MUST có tệp kê khai SHA256SUMS và gốc băm được
  bảo vệ SECDED(72,64).

### VI. Đa năng, tối thiểu phụ thuộc, trường tồn

- Ứng dụng MUST là một tệp HTML chạy trên trình duyệt hiện đại của điện thoại, máy tính bảng, máy
  tính; lõi tham chiếu MUST chỉ dùng thư viện chuẩn Python.
- Không xóa cấu trúc cũ; chỉ bổ sung. Mọi xóa bỏ cần chấp thuận của quản trị viên.

### VII. Nghiệm thu bằng mô phỏng người dùng

- Trước khi phát hành, bộ kiểm thử tự động và kịch bản mô phỏng nhiều kiểu người dùng MUST chạy
  qua toàn bộ chức năng; lỗi phát hiện MUST được sửa và chạy lại tới khi đạt 100 %.

## Ràng buộc an ninh và pháp lý

- Tuân thủ Luật Bảo vệ quyền lợi người tiêu dùng 19/2023/QH15, Luật Quảng cáo (sửa đổi bởi Luật
  75/2025/QH15), Nghị định 98/2021/NĐ-CP về trang thiết bị y tế (nếu có mục đích y tế), và các
  QCVN về an toàn, tương thích điện từ khi có phần cứng.
- Không lưu bí mật; dữ liệu nhận qua phòng nhiều thiết bị là dữ liệu không tin cậy.

## Quy trình phát triển và cổng chất lượng

1. Đặc tả (`spec.md`) → kế hoạch (`plan.md`) → nhiệm vụ (`tasks.md`) → triển khai → nghiệm thu.
2. Cổng: `python -m pytest tests` xanh 100 %; `node acceptance/simulate_users.cjs` đạt 100 %;
   `python -m sr783 verify` xác nhận SHA256SUMS và gốc băm.

## Governance

Hiến chương này có hiệu lực cao nhất đối với SR783. Sửa đổi phải ghi lý do, tăng phiên bản theo
SemVer và cập nhật các mẫu liên quan.

**Version**: 1.0.0 | **Ratified**: 2026-11-03 | **Last Amended**: 2026-11-03
