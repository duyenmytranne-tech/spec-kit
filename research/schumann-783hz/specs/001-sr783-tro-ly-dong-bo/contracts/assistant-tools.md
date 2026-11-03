# Contract: trợ lý hội thoại

## Thứ tự xử lý một câu người dùng

**Bước 1 – Khủng hoảng** (từ khóa `kb.safety.crisis_terms`, đã bỏ dấu) → thông điệp cố định có số 115,
xử lý trên thiết bị, không gửi đi.

**Bước 2 – Lệnh** (xử lý trên thiết bị ở mọi chế độ):

| Ý định | Ví dụ | Hiệu ứng |
|---|---|---|
| start | "bắt đầu đẳng thời 10 phút", "bat dau hai tai" | đặt chế độ/thời lượng nếu có, bắt đầu tại pha 0 kế tiếp |
| stop | "dừng", "dừng lại", "tắt âm" | giảm âm 1 s rồi dừng |
| freq | "tần số 7,79", "đặt tần số là 7.792" | đặt p/q nếu 1–40 Hz (bỏ qua nếu là câu hỏi "là gì") |
| volume | "âm lượng 20" | 0–50 %, giá trị lớn hơn bị chặn ở 50 % |
| code | "mã phiên", "tạo mã" | tạo mã phiên |
| join | dán `SR783-1-…` | kiểm tra mã và tham gia |
| status | "trạng thái" | đọc trạng thái phiên |
| tab | "soi bit" | mở mục Soi bit |

**Bước 3 – Y tế** (từ khóa `kb.safety.medical_terms`) → thông điệp không tư vấn điều trị, kèm tài liệu.

**Bước 4 – Chủ đề tri thức**: chuẩn hóa (chữ thường, bỏ dấu, `đ→d`, ký tự khác chữ số → khoảng trắng);
điểm của chủ đề = tổng số từ của các từ khóa khớp nguyên cụm; điểm cao nhất thắng, hòa thì chủ đề
đứng trước thắng; không khớp → câu trả lời dự phòng.

**Bước 5 – Trực tuyến (tùy chọn)**: nếu bật và người dùng đồng ý, câu không phải lệnh được gửi tới Claude
với quy tắc: tiếng Việt, ≤ 120 từ, chỉ dựa trên dữ kiện cơ sở tri thức, ghi mức bằng chứng và tài
liệu, không tư vấn điều trị. Lỗi không cấp quyền → tắt trực tuyến và trả lời ngoại tuyến.

## Thao tác trang mà trợ lý trực tuyến được gọi

| Tên | Đầu vào | Trả về |
|---|---|---|
| `get_status` | – | mô tả trạng thái phiên |
| `set_frequency` | `{hz: string}` | kết quả đặt tần số (1–40 Hz) |
| `start_session` | `{mode?, minutes?}` với mode ∈ {I, B, M} | xác nhận |
| `stop_session` | – | xác nhận |
| `set_volume` | `{percent: number}` | xác nhận (chặn 50 %) |
| `make_session_code` | – | mã phiên |

Âm thanh chỉ bắt đầu sau thao tác của người dùng; lượt bấm Gửi mở khóa âm thanh trước khi gọi Claude.
