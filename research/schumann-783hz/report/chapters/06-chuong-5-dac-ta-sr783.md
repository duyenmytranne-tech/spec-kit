<a id="c5"></a>

# CHƯƠNG 5. ĐẶC TẢ PHẦN MỀM VÀ THIẾT BỊ TRUNG GIAN SR783

## 5.1. Yêu cầu và cách tiếp cận

Yêu cầu bổ sung của người đặt hàng: *"đặc tả một thiết bị phần mềm dựa trên 7,83 Hz, người dùng có thể
nói chuyện và đồng bộ tần số, tận dụng tối đa tính ứng dụng của 7,83 Hz… phần mềm máy tính hoặc thiết bị
trung gian trực tiếp trên các thiết bị công nghệ đa năng"*. Đặc tả được lập theo quy trình Spec-Driven
Development của Spec Kit [53] ngay trong gói nghiên cứu:

| Tài liệu | Vai trò |
|---|---|
| `.specify/memory/constitution.md` | Hiến chương sản phẩm: 7 nguyên tắc (sự thật và an toàn, đồng nhất đến bit, ngoại tuyến, an toàn thị giác – thính giác, tự sửa lỗi, trường tồn, nghiệm thu mô phỏng) |
| `specs/001-sr783-tro-ly-dong-bo/spec.md` | Đặc tả: 7 câu chuyện người dùng, 30 yêu cầu chức năng, 12 tiêu chí thành công |
| `plan.md`, `research.md`, `data-model.md`, `contracts/` | Kế hoạch kỹ thuật, quyết định, mô hình dữ liệu, 4 hợp đồng |
| `tasks.md`, `quickstart.md`, `checklists/requirements.md` | Nhiệm vụ (đã làm/tương lai), hướng dẫn nhanh, kiểm tra chất lượng đặc tả |
| `app/sr783-standalone.html`, `app/sr783.html` | Bản mẫu chạy được: tệp độc lập ngoại tuyến và bản Artifact |
| `python -m sr783` | Phần mềm dòng lệnh cho máy tính: soi bit, pha, mã phiên, xuất WAV bit-exact |

## 5.2. Tóm tắt các câu chuyện người dùng

| # | Câu chuyện | Ưu tiên | Giá trị |
|---|---|---|---|
| US1 | Trò chuyện có kiểm chứng (gõ hoặc nói, đọc to) | P1 | Hiểu đúng, chặn thông tin sai, điều khiển bằng lời |
| US2 | Phát và đồng bộ nhịp 7,83 Hz trên nhiều thiết bị | P1 | Lớp thiền, nhóm nghiên cứu nghe cùng pha, không cần máy chủ |
| US3 | Đồng bộ theo tần số Schumann thực đo | P2 | Dùng giá trị tự nhiên thật thay vì con số danh nghĩa |
| US4 | Kiểm chứng thiết bị "7,83 Hz" | P2 | Bảo vệ người tiêu dùng bằng phép đo |
| US5 | Toàn vẹn dữ liệu và tự sửa lỗi | P3 | SECDED + SHA-256 |
| US6 | Soi bit và giáo dục | P3 | Nối con số với phần cứng |
| US7 | Thiết bị trung gian ngoại vi | P3 (tương lai) | Đo SR thật, chuẩn thời gian |

## 5.3. Kiến trúc

![Hình 8. Kiến trúc SR783](figures/fig8_architecture.svg)

- **Thiết bị phần mềm**: một tệp HTML (khoảng 100 KB), chạy trên trình duyệt của điện thoại, máy tính
  bảng, máy tính, TV; không cài đặt, không tài khoản, không mạng.
- **Lõi đồng bộ**: tần số p/q; pha số nguyên theo mili giây UTC; âm thanh khởi động đúng pha 0 kế tiếp;
  độ trôi giữa đồng hồ âm thanh và UTC được đo mỗi 5 s và bù bằng co giãn thời gian 4 s khi vượt 2 ms.
- **Trợ lý hội thoại**: lớp an toàn → lệnh → cơ sở tri thức 32 chủ đề có mức bằng chứng; khi mở trong
  Claude, người dùng có thể bật "Hỏi Claude": câu hỏi tự do được trả lời theo cùng quy tắc bằng chứng,
  và Claude có thể gọi 6 thao tác của trang (trạng thái, đặt tần số, bắt đầu, dừng, âm lượng, mã phiên).
- **Phòng nhiều thiết bị** (khi mở trong Claude): các thiết bị cùng mã phiên vào cùng phòng, chia sẻ
  hiện diện và ước lượng lệch đồng hồ bằng ping/pong; ngoài Claude vẫn đồng bộ được theo UTC.
- **Thiết bị trung gian phần mềm cho máy tính**: CLI `python -m sr783` xuất tệp WAV bit-exact để phát
  trên loa, TV, hệ thống âm thanh không chạy được ứng dụng.
- **Thiết bị trung gian phần cứng (tương lai)**: cuộn cảm ứng + ADC 24 bit + TCXO hoặc GPS 1 PPS,
  USB-C/BLE, xuất CSV theo hợp đồng.

## 5.4. Tận dụng tối đa tính ứng dụng của 7,83 Hz

| Ứng dụng thật của 7,83 Hz | Chức năng SR783 | Giá trị cho người dùng | Mức bằng chứng của nền tảng |
|---|---|---|---|
| Hiện tượng khoa học đo được | Trợ lý giải thích, tài liệu, mức bằng chứng | Hiểu đúng, chống tin giả | A |
| Tần số tự nhiên thay đổi | Đồng bộ theo f₁ thực đo | Gắn trải nghiệm với dữ liệu thật | A |
| Nhịp chung toàn cầu | Đồng bộ pha nhiều thiết bị theo UTC | Hoạt động nhóm cùng nhịp | A (kỹ thuật) |
| Thư giãn bằng âm thanh nhịp nhàng | Âm đẳng thời, nhịp phách, dẫn nhịp thở 6/phút | Thư giãn an toàn, không hứa chữa bệnh | B–C |
| Bảo vệ người tiêu dùng | Kiểm chứng máy phát bằng cảm biến điện thoại | Phát hiện thiết bị lệch tần | A |
| Giáo dục STEM, kỹ thuật nhúng | Soi bit, DDS, Timer1, SECDED, SHA-256 | Học từ con số đến phần cứng | A |
| Nghiên cứu AI cho dữ liệu ELF | Định dạng dữ liệu cho thiết bị trung gian, phương pháp lai | Nền cho trạm đo tại Việt Nam | B |

## 5.5. An toàn, pháp lý và quyền riêng tư

- Không nhấp nháy ở 7,83 Hz; vòng pha quay một vòng mỗi 30 chu kỳ (3,83 s); tôn trọng thiết lập giảm
  chuyển động của hệ điều hành.
- Âm lượng tối đa 50 %, tăng dần 3 s, giảm dần 1 s, phiên 1–120 phút; nhắc tai nghe cho nhịp phách hai tai.
- Câu hỏi khủng hoảng trả lời ngay với số 115; câu hỏi điều trị được chuyển sang khuyến nghị gặp bác sĩ.
- Dữ liệu ở trên thiết bị; chỉ chức năng "Hỏi Claude" (tùy chọn, có hỏi đồng ý) gửi câu hỏi đi.
- Sản phẩm định vị là công cụ thư giãn, giáo dục, nghiên cứu; nếu thêm mục đích y tế phải tuân theo
  Nghị định 98/2021/NĐ-CP và văn bản sửa đổi [47].

## 5.6. Kết quả kiểm thử bản mẫu

Kết quả nghiệm thu chi tiết ở [Phụ lục C](09-phu-luc.md#pl-c). Tóm tắt:

| Tiêu chí (spec) | Mục tiêu | Kết quả đo |
|---|---|---|
| SC-001 nhận đúng chủ đề | ≥ 90 % của bộ câu hỏi chuẩn | 44/44 (100 %) |
| SC-002 phản hồi khủng hoảng | 100 % | 3/3 (100 %) |
| SC-003 lệch pha hai thiết bị (đồng hồ lệch 3 ms) | < 10° ở ≥ 95 % lần đo | 20/20 lần < 10°; trung bình ≈ 8,5° (lý thuyết 8,46°) |
| SC-004 pha trùng tuyệt đối | 100 % vector | 4/4 (100 %) |
| SC-005 sai số DDS 48 kHz / Timer1 | < 1 ppm / < 20 ppm | +0,6563 ppm / +15,040 ppm |
| SC-006 kiểm chứng dữ liệu mẫu | ≤ 0,01 Hz | đo 7,8498 Hz so với 7,85 Hz thật (sai 0,0002 Hz), kết luận Đạt |
| SC-007 tiêm lỗi SECDED | 100 % sửa 1 bit, 100 % phát hiện 2 bit | trong ứng dụng: 144/144 vị trí sửa đúng, 400/400 lỗi 2 bit phát hiện |
| SC-008 nhấp nháy | ≤ 3 lần/giây | 0 lần/giây; ghi hình ≈ 60 khung/s (> 15,66 khung/s Nyquist) |
| SC-010 ngoại tuyến | Toàn bộ chức năng lõi | Đạt (tệp độc lập, không tải tài nguyên ngoài bắt buộc) |
| SC-011 bề rộng 360 px | Không cuộn ngang | bề rộng cuộn 360 px = khung nhìn |
| SC-012 kiểm thử tự động | 100 % | pytest 48/48; mô phỏng người dùng 67/67; `sha256sum -c` đạt |

## 5.7. Lộ trình

1. Thử nghiệm người dùng có đối chứng (thư giãn, khả năng sử dụng) theo quy trình đạo đức.
2. Chế tạo thiết bị trung gian, đặt trạm ELF thử nghiệm tại địa điểm nhiễu thấp ở Việt Nam, đối chiếu
   với trạm quốc tế.
3. Thử nghiệm QCVN về an toàn điện và tương thích điện từ cho phần cứng trước khi lưu hành.
4. Mở dữ liệu trạm kèm SHA256SUMS và gốc băm có mã sửa lỗi.
