# Phase 0 Research: SR783

Cơ sở khoa học đầy đủ nằm trong báo cáo `report/BAO-CAO-7.83Hz.md`. Tệp này ghi các quyết định kỹ
thuật theo dạng Quyết định / Lý do / Phương án bị loại.

## R1. Biểu diễn tần số và pha

- **Quyết định**: f = p/q (phân số tối giản, 7,83 Hz = 783/100); pha = (p·Δt mod 1000q)/(1000q) với
  Δt là mili giây UTC tính từ mốc phiên t0; số học BigInt.
- **Lý do**: không tích lũy sai số dấu phẩy động; mọi thiết bị cho cùng tử số/mẫu số; kiểm thử được bit-exact.
- **Loại bỏ**: bộ tích lũy pha dấu phẩy động (trôi theo thời gian); đếm khung hình (phụ thuộc tốc độ làm tươi).
- **Bổ sung sau nghiệm thu**: thời điểm hiện tại tính theo micro giây (đồng hồ hệ điều hành hiệu chuẩn
  bằng `performance.now()`), vì lượng tử 1 ms gây thêm tới 2,82° lệch pha.

## R2. Đồng bộ nhiều thiết bị

- **Quyết định**: đồng bộ "không máy chủ" theo UTC của hệ điều hành + mã phiên; khi có phòng nhiều
  thiết bị, đo độ lệch đồng hồ bằng ping/pong (θ = ((t2 − t1) + (t3 − t4))/2, chọn mẫu trễ khứ hồi nhỏ nhất).
- **Lý do**: chạy được ngoại tuyến; độ lệch pha = 360°·f·δ nên 1 ms ứng với 2,82°.
- **Loại bỏ**: máy chủ thời gian riêng (thêm hạ tầng, mất ngoại tuyến).

## R3. Bộ phát âm thanh

- **Quyết định**: dao động hình sin của nền tảng âm thanh, khởi động tại thời điểm pha 0 kế tiếp đã đổi
  sang đồng hồ âm thanh; bao hình âm đẳng thời 0,5 − 0,5·cos; bù trôi bằng "co giãn thời gian" mọi bộ
  dao động trong 4 s khi lệch > 2 ms.
- **Lý do**: không gây tiếng lách cách; không ngắt âm khi bù.
- **Loại bỏ**: khởi động lại khi trôi (có khoảng lặng); bộ đệm lặp (cần 100 s để lặp liền mạch với âm mang 200 Hz).

## R4. Trợ lý hội thoại

- **Quyết định**: lớp an toàn → lệnh → khớp chủ đề theo từ khóa đã bỏ dấu (điểm = số từ của từ khóa
  khớp); tùy chọn hỏi Claude với quy tắc bằng chứng, công cụ trang và lối lui ngoại tuyến.
- **Lý do**: tất định, kiểm thử được, chạy ngoại tuyến; câu hỏi tự do vẫn có lời giải khi trực tuyến.
- **Loại bỏ**: chỉ dùng mô hình ngôn ngữ (không ngoại tuyến, khó kiểm thử).

## R5. Toàn vẹn và tự sửa lỗi

- **Quyết định**: cài đặt đóng gói thành 2 từ 64 bit, mỗi từ SECDED(72,64); thẻ = 16 ký tự đầu
  SHA-256 của hai từ mã; nhật ký chuỗi băm SHA-256 với entry chỉ chứa chuỗi và số nguyên (JSON chuẩn hóa).
- **Lý do**: sửa 1 bit, phát hiện 2 bit; thẻ bắt lỗi ≥ 3 bit giải mã sai; JSON chuẩn hóa cho cùng byte
  ở Python và JavaScript.

## R6. Kiểm chứng thiết bị

- **Quyết định**: DFT không đều (theo thời điểm mẫu thật) với cửa sổ Hann, quét thô 0,01 Hz rồi tinh
  0,0005 Hz, nội suy parabol trên log công suất; SNR = công suất đỉnh / trung vị ngoài ±0,15 Hz.
- **Lý do**: điện thoại lấy mẫu không đều; tránh nội suy lại.
- **Giới hạn**: từ kế điện thoại 0,15 µT/LSB chỉ thấy máy phát mẫu ở ≤ 7,42 cm (1 LSB), tốt nhất ≤ 3,33 cm (10 LSB).

## R7. Ứng dụng AI cho dữ liệu Schumann thật

- **Quyết định**: dùng phương pháp lai (hồi quy ridge khởi tạo + khớp Lorentz bền vững) khi có thiết bị
  trung gian; thí nghiệm tái lập cho MAE 0,0299 Hz so với 0,3283 Hz của lấy đỉnh cực đại.

## R8. Thiết bị trung gian (tương lai)

- **Quyết định**: cuộn cảm ứng + ADC 24 bit + TCXO hoặc GPS 1 PPS, giao tiếp USB-C/BLE, xuất đúng
  định dạng `contracts/data-csv.md`.
- **Lý do**: 1 pT cần cảm biến chuyên dụng; phần mềm dùng chung đường xử lý.
