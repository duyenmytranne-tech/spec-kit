# Feature Specification: SR783 – Trợ lý hội thoại và đồng bộ tần số 7,83 Hz trên thiết bị đa năng

**Feature Branch**: `001-sr783-tro-ly-dong-bo`

**Created**: 2026-11-03

**Status**: Draft

**Input**: User description: "Bạn hãy đặc tả một thiết bị phần mềm dựa trên 7.83 hz người dùng có thể nói chuyện và đồng bộ tần số và tận dụng tối đa tính ứng dụng của 7.83 hz mang lại. Tiếp tục phần mềm máy tính hoặc thiết bị trung gian trực tiếp trên các thiết bị công nghệ đa năng"

> Phạm vi: một "thiết bị phần mềm" chạy trực tiếp trên thiết bị đa năng sẵn có (điện thoại, máy tính
> bảng, máy tính, TV có trình duyệt), kèm một thiết bị trung gian ngoại vi tùy chọn. Cơ sở khoa học,
> số liệu và mức bằng chứng lấy từ báo cáo `report/BAO-CAO-7.83Hz.md` cùng gói nghiên cứu.

## User Scenarios & Testing *(mandatory)*

*Kịch bản người dùng và kiểm thử. Mỗi câu chuyện kiểm thử độc lập được và tự nó đã có giá trị.*

### User Story 1 - Trò chuyện có kiểm chứng về 7,83 Hz (Priority: P1)

Người dùng phổ thông gõ (hoặc nói, nếu thiết bị hỗ trợ) bằng tiếng Việt có dấu hay không dấu các câu
như "7,83 Hz là gì?", "có hại không?", "máy phát có tác dụng không?". Trợ lý trả lời ngắn gọn, ghi mức
bằng chứng A–D và số tài liệu tham khảo, và có thể đọc to câu trả lời. Người dùng cũng ra lệnh bằng
lời: "bắt đầu đẳng thời 10 phút", "tần số 7,79", "âm lượng 20", "dừng", "mã phiên", "trạng thái".

**Why this priority**: Đây là cửa ngõ của sản phẩm và là nơi chặn thông tin sai lệch (tần số "đang
tăng", "chữa bệnh"). Không có nó, người dùng không có cách hiểu đúng và dùng an toàn các chức năng khác.

**Independent Test**: Gửi bộ 40 câu hỏi chuẩn (có và không dấu) cùng 10 lệnh; kiểm tra chủ đề nhận
diện, mức bằng chứng, số tài liệu và tác động của lệnh lên trạng thái phiên.

**Acceptance Scenarios**:

1. **Given** trợ lý ở chế độ ngoại tuyến, **When** người dùng hỏi "7,83 Hz là gì?", **Then** câu trả
   lời nêu cộng hưởng Schumann, mức bằng chứng A và các tài liệu [1], [2], [3], [6].
2. **Given** bất kỳ chế độ nào, **When** câu hỏi chứa ý định tự hại, **Then** trợ lý trả lời ngay thông
   điệp hỗ trợ có số 115, xử lý trên thiết bị, không gửi câu hỏi tới dịch vụ ngoài.
3. **Given** câu hỏi về điều trị bệnh, **When** người dùng hỏi "có chữa ung thư không", **Then** trợ lý
   từ chối tư vấn điều trị, nêu bằng chứng hiện có và khuyên gặp bác sĩ.
4. **Given** phiên đang dừng, **When** người dùng gõ "bắt đầu đẳng thời 10 phút", **Then** phiên bắt
   đầu ở chế độ âm đẳng thời, thời lượng 10 phút, và trợ lý xác nhận bằng lời.
5. **Given** trợ lý trực tuyến được bật và người dùng đồng ý, **When** người dùng hỏi một câu ngoài
   cơ sở tri thức, **Then** câu trả lời vẫn tuân thủ quy tắc bằng chứng và an toàn; nếu dịch vụ trực
   tuyến không dùng được, trợ lý tự lui về chế độ ngoại tuyến.

---

### User Story 2 - Phát và đồng bộ nhịp 7,83 Hz trên nhiều thiết bị (Priority: P1)

Người dùng bắt đầu một phiên nhịp 7,83 Hz ở một trong ba chế độ âm thanh (âm đẳng thời, nhịp phách
hai tai, nhịp phách đơn âm). Một nhóm người (ví dụ một lớp thiền) mở ứng dụng trên nhiều điện thoại và
máy tính; tất cả nghe cùng pha mà không cần máy chủ, nhờ mốc pha chung và đồng hồ chuẩn của thiết bị.
Người dùng tạo một mã phiên ngắn có mã kiểm tra để thiết bị khác tham gia đúng tham số.

**Why this priority**: "Đồng bộ tần số" là yêu cầu cốt lõi của người dùng và là giá trị khác biệt so
với các ứng dụng phát âm thông thường.

**Independent Test**: Mở hai phiên trên hai thiết bị (hoặc hai cửa sổ) với cùng mã phiên, so sánh pha
hiển thị tại cùng thời điểm; thay đổi một ký tự của mã và xác nhận mã bị từ chối.

**Acceptance Scenarios**:

1. **Given** hai thiết bị có đồng hồ lệch nhau dưới 3,5 ms, **When** cả hai tham gia cùng mã phiên,
   **Then** độ lệch pha hiển thị giữa chúng dưới 10°.
2. **Given** một mã phiên bị gõ sai một ký tự, **When** người dùng bấm Tham gia, **Then** ứng dụng từ
   chối và giải thích mã kiểm tra không khớp.
3. **Given** phiên đang phát, **When** người dùng đổi tần số, **Then** nhịp mới bắt đầu tại thời điểm
   pha 0 kế tiếp, không có tiếng lách cách do nhảy pha.
4. **Given** phiên kéo dài, **When** đồng hồ âm thanh của thiết bị trôi so với đồng hồ chuẩn, **Then**
   ứng dụng bù trôi dần mà không ngắt âm và hiển thị lượng đã bù.
5. **Given** người dùng muốn phát trên loa hoặc TV không chạy được ứng dụng, **When** bấm xuất tệp,
   **Then** nhận tệp âm thanh 60 giây cùng tham số, có mã băm để kiểm chứng.

---

### User Story 3 - Đồng bộ theo tần số Schumann thực đo (Priority: P2)

Người dùng có số đo tần số mode 1 thực tế (từ một trạm quan trắc hoặc thiết bị trung gian) và muốn
bộ phát đi theo giá trị thực đo (ví dụ 7,792 Hz) thay vì con số danh nghĩa 7,83 Hz.

**Why this priority**: Tận dụng giá trị khoa học thật của 7,83 Hz: tần số tự nhiên thay đổi theo giờ,
mùa và Mặt Trời.

**Independent Test**: Nhập một giá trị và một tệp dữ liệu có cả dòng hợp lệ, dòng ngoài dải và dòng
chất lượng kém; kiểm tra giá trị được chọn và giá trị bị loại.

**Acceptance Scenarios**:

1. **Given** giá trị 7,792 Hz chất lượng tốt, **When** người dùng bấm đồng bộ, **Then** tần số phiên
   trở thành 7,792 Hz biểu diễn chính xác bằng phân số 974/125.
2. **Given** giá trị 9,6 Hz, **When** người dùng bấm đồng bộ, **Then** ứng dụng từ chối vì ngoài dải
   7,0–9,0 Hz của mode 1.
3. **Given** tệp dữ liệu nhiều dòng, **When** nạp tệp, **Then** ứng dụng chọn dòng hợp lệ mới nhất và
   bỏ qua dòng chất lượng kém.

---

### User Story 4 - Kiểm chứng một thiết bị "7,83 Hz" (Priority: P2)

Người tiêu dùng hoặc kỹ sư kiểm định muốn biết một máy phát "7,83 Hz" có thật sự phát đúng tần số công
bố hay không. Họ đặt điện thoại sát máy phát, ghi dữ liệu cảm biến từ trường thành tệp, nạp vào ứng
dụng và nhận kết luận Đạt / Không đạt / Không xác định kèm tần số đo, sai số và tỉ số tín hiệu trên nhiễu.

**Why this priority**: Bảo vệ người tiêu dùng là ứng dụng thực tế, có đo lường được của chủ đề 7,83 Hz.

**Independent Test**: Dùng bộ dữ liệu mẫu có tần số thật đã biết (7,85 Hz) và xác nhận tần số đo nằm
trong ±0,01 Hz; dùng dữ liệu chỉ có nhiễu và xác nhận kết luận "Không xác định".

**Acceptance Scenarios**:

1. **Given** dữ liệu mẫu 30 s của máy phát 7,85 Hz có nhiễu, **When** phân tích, **Then** tần số đo
   nằm trong 7,84–7,86 Hz và kết luận "Đạt" với dung sai 1 %.
2. **Given** dữ liệu không có tín hiệu tuần hoàn, **When** phân tích, **Then** kết luận "Không xác
   định" vì tỉ số tín hiệu trên nhiễu dưới 10 dB.
3. **Given** một kết quả kiểm chứng, **When** người dùng xuất báo cáo, **Then** nhận tệp bảng chứa
   nguồn dữ liệu, số mẫu, tần số đo, tần số công bố, sai số, tỉ số tín hiệu trên nhiễu và kết luận.

---

### User Story 5 - Toàn vẹn dữ liệu và tự sửa lỗi (Priority: P3)

Cài đặt của người dùng phải còn đúng sau lỗi bộ nhớ hoặc sửa đổi ngoài ý muốn. Người dùng có thể tự
thử lật bit để thấy ứng dụng sửa lỗi; nhật ký phiên lộ ra mọi sửa đổi về sau.

**Why this priority**: Đáp ứng yêu cầu "cơ chế tự sửa lỗi", "an toàn bảo mật" và "đồng nhất đến bit".

**Independent Test**: Tiêm lỗi 1 bit và 2 bit vào cài đặt đã lưu, nạp lại, kiểm tra kết quả; sửa một
dòng nhật ký và chạy kiểm tra chuỗi.

**Acceptance Scenarios**:

1. **Given** cài đặt đã lưu, **When** một bit bất kỳ trong 144 bit mã bị lật, **Then** khi nạp lại
   ứng dụng sửa đúng bit đó, thẻ băm khớp và cài đặt không đổi.
2. **Given** cài đặt đã lưu, **When** hai bit trong cùng một từ mã bị lật, **Then** ứng dụng phát hiện,
   khôi phục mặc định và ghi nhật ký.
3. **Given** nhật ký có nhiều sự kiện, **When** một sự kiện bị sửa, **Then** kiểm tra chuỗi báo không
   hợp lệ.

---

### User Story 6 - Soi bit và giáo dục (Priority: P3)

Sinh viên, kỹ sư nhúng và giáo viên nhập một tần số và xem nó được biểu diễn thế nào trong máy tính:
dạng phân số, dấu phẩy động 32/64 bit, từ điều chỉnh của bộ tổng hợp số, giá trị thanh ghi bộ định thời
vi điều khiển và sai số tương ứng.

**Why this priority**: Làm rõ "liên kết tầng bit" giữa con số 7,83 và phần cứng thật.

**Independent Test**: Nhập 7,83 và so sánh với bảng tham chiếu của báo cáo (0x40FA8F5C, 700617,
OCR1A 15963).

**Acceptance Scenarios**:

1. **Given** giá trị 7,83, **When** người dùng bấm Soi bit, **Then** hiển thị 0x40FA8F5C,
   0x401F51EB851EB852, từ điều chỉnh 700617 ở 48 kHz và OCR1A = 15963 với sai số +15,040 ppm.

---

### User Story 7 - Thiết bị trung gian ngoại vi (Priority: P3)

Người dùng nâng cao gắn một thiết bị trung gian nhỏ (cảm biến cuộn cảm ứng, bộ chuyển đổi tương tự–số
độ phân giải cao, đồng hồ chuẩn) vào điện thoại hoặc máy tính để đo cộng hưởng Schumann thật và làm
chuẩn thời gian cho đồng bộ.

**Why this priority**: Mở rộng tương lai; phần mềm đã có giao diện nhập dữ liệu nên thiết bị này
không chặn các câu chuyện P1–P2.

**Independent Test**: Thiết bị xuất dữ liệu đúng định dạng tệp cảm biến và tệp Schumann của hợp đồng;
ứng dụng nhận và xử lý như dữ liệu nhập tay.

**Acceptance Scenarios**:

1. **Given** thiết bị trung gian xuất số đo mode 1 theo định dạng hợp đồng, **When** người dùng nạp,
   **Then** ứng dụng đồng bộ theo giá trị đó như ở câu chuyện 3.

---

### Edge Cases

- Thiết bị không phát được âm thanh hoặc chặn âm thanh khi chưa có thao tác của người dùng: ứng dụng
  báo rõ và chỉ bắt đầu âm thanh sau một thao tác.
- Đồng hồ thiết bị lệch lớn (hàng trăm ms): độ lệch pha hiển thị lớn; ứng dụng gợi ý bật đồng bộ thời
  gian của hệ điều hành và hiển thị độ lệch đo được giữa các thiết bị khi có phòng nhiều thiết bị.
- Trình duyệt chạy nền làm giãn bộ hẹn giờ: âm thanh vẫn theo đồng hồ âm thanh; phép bù trôi tiếp tục
  khi ứng dụng trở lại.
- Nhập tần số sai định dạng hoặc ngoài 1–40 Hz: từ chối, giữ giá trị cũ.
- Bộ nhớ trình duyệt bị chặn hoặc bị xóa: ứng dụng vẫn chạy với cài đặt mặc định trong bộ nhớ tạm.
- Lỗi 3 bit trở lên trong một từ mã: có thể giải mã sai; thẻ băm phát hiện và ứng dụng khôi phục mặc định.
- Nhịp phách hai tai khi không đeo tai nghe: ứng dụng nhắc đeo tai nghe.
- Người dùng nhạy cảm ánh sáng: không có thành phần nào thay đổi độ sáng ở 7,83 Hz.
- Tệp dữ liệu có khoảng trống, đơn vị mili giây, dấu phân cách khác nhau, lấy mẫu không đều: được
  nhận diện; dưới 32 mẫu hoặc dưới 1 giây thì báo không đủ dữ liệu.
- Ảnh phổ đồ có vạch bất thường (giống các ảnh lan truyền): trợ lý giải thích nguyên nhân thường gặp.
- Nhiều thẻ trình duyệt cùng mở: mỗi thẻ là một thiết bị trong phòng; pha vẫn khớp.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống MUST trả lời câu hỏi tiếng Việt có dấu và không dấu về 7,83 Hz bằng cơ sở tri
  thức ngoại tuyến, mỗi câu trả lời có mức bằng chứng A–D và số tài liệu tham khảo.
- **FR-002**: Hệ thống MUST nhận diện lệnh bằng lời: bắt đầu (kèm chế độ, thời lượng), dừng, đặt tần
  số, đặt âm lượng, tạo/tham gia mã phiên, trạng thái, mở mục soi bit.
- **FR-003**: Hệ thống MUST xử lý ý định khủng hoảng trước mọi xử lý khác, trên thiết bị, với thông
  điệp có số cấp cứu 115.
- **FR-004**: Hệ thống MUST từ chối tư vấn chẩn đoán/điều trị và nêu bằng chứng hiện có.
- **FR-005**: Hệ thống MUST cho phép bật trợ lý trực tuyến tùy chọn chỉ khi người dùng đồng ý; trợ lý
  trực tuyến MUST tuân thủ cùng quy tắc bằng chứng và an toàn, và MAY điều khiển phiên qua các thao
  tác được liệt kê trong hợp đồng.
- **FR-006**: Hệ thống MUST có thể đọc to câu trả lời khi người dùng bật.
- **FR-007**: Hệ thống MUST phát nhịp ở ba chế độ: âm đẳng thời, nhịp phách hai tai, nhịp phách đơn âm,
  với âm mang 50–1000 Hz (mặc định 200 Hz).
- **FR-008**: Hệ thống MUST biểu diễn tần số nhịp bằng phân số chính xác và tính pha bằng số học số
  nguyên theo mốc pha chung, sao cho mọi thiết bị cho cùng pha tại cùng thời điểm chuẩn.
- **FR-009**: Hệ thống MUST bắt đầu và đổi tham số tại thời điểm pha 0 kế tiếp.
- **FR-010**: Hệ thống MUST đo và bù trôi giữa đồng hồ âm thanh và đồng hồ chuẩn mà không ngắt âm.
- **FR-011**: Hệ thống MUST tạo mã phiên chứa tần số, mốc pha, chế độ và mã kiểm tra băm 8 ký tự; MUST
  từ chối mã có mã kiểm tra sai.
- **FR-012**: Khi có kênh phòng nhiều thiết bị, hệ thống SHOULD hiển thị các thiết bị cùng phiên, độ
  lệch đồng hồ ước lượng và độ lệch pha tương ứng.
- **FR-013**: Hệ thống MUST hiển thị vòng pha chuyển động chậm (một vòng bằng 30 chu kỳ) và các số đo
  pha, chu kỳ, độ trôi; MUST NOT có vùng nhấp nháy quá 3 lần mỗi giây.
- **FR-014**: Hệ thống MUST chặn âm lượng ở 50 %, tăng/giảm dần 3 s và giới hạn phiên 1–120 phút.
- **FR-015**: Hệ thống MUST xuất tệp âm thanh 60 s, 16 bit, 48 kHz đúng tham số phiên, kèm mã băm.
- **FR-016**: Hệ thống MUST nhận tần số mode 1 thực đo (nhập tay hoặc tệp), chỉ chấp nhận 7,0–9,0 Hz
  và chất lượng khác "kém", rồi đồng bộ bộ phát theo giá trị đó.
- **FR-017**: Hệ thống MUST phân tích tệp dữ liệu cảm biến lấy mẫu không đều, ước lượng tần số trong
  6–10 Hz với độ phân giải tốt hơn 0,01 Hz, tính sai số so với tần số công bố và tỉ số tín hiệu trên nhiễu.
- **FR-018**: Hệ thống MUST đưa kết luận Đạt khi |sai số| ≤ dung sai (mặc định 1 %) và tỉ số tín hiệu
  trên nhiễu ≥ 10 dB; Không xác định khi tỉ số dưới 10 dB; Không đạt trong các trường hợp còn lại.
- **FR-019**: Hệ thống MUST cung cấp dữ liệu mẫu có tần số thật đã biết để người dùng thử kiểm chứng.
- **FR-020**: Hệ thống MUST xuất báo cáo kiểm chứng dạng bảng.
- **FR-021**: Hệ thống MUST hiển thị cho một tần số bất kỳ: phân số, biểu diễn dấu phẩy động 32/64 bit
  và giá trị thập phân chính xác, từ điều chỉnh tổng hợp số trực tiếp cho các cấu hình chuẩn, và giá
  trị thanh ghi bộ định thời 16 bit của vi điều khiển tham chiếu kèm sai số.
- **FR-022**: Hệ thống MUST lưu cài đặt dưới dạng từ mã sửa 1 bit / phát hiện 2 bit kèm thẻ băm; khi
  nạp MUST tự sửa lỗi 1 bit, phát hiện lỗi 2 bit và khôi phục mặc định.
- **FR-023**: Hệ thống MUST ghi nhật ký sự kiện thành chuỗi băm và cho phép kiểm tra, xuất nhật ký.
- **FR-024**: Hệ thống MUST cho phép người dùng tự tiêm lỗi 1 bit và 2 bit để quan sát cơ chế tự sửa.
- **FR-025**: Hệ thống MUST chạy toàn bộ chức năng lõi không cần mạng và không gửi dữ liệu ra ngoài khi
  chức năng trực tuyến tắt.
- **FR-026**: Hệ thống MUST chạy trên điện thoại, máy tính bảng và máy tính, từ màn hình rộng khoảng
  360 px trở lên, không cuộn ngang.
- **FR-027**: Hệ thống MUST hiển thị cảnh báo sử dụng: không chẩn đoán/điều trị; nhóm cần hỏi bác sĩ;
  yêu cầu tai nghe cho nhịp phách hai tai.
- **FR-028**: Hệ thống MUST có giao diện tiếng Việt, dùng dấu phẩy thập phân trong văn bản hiển thị.
- **FR-029**: Thiết bị trung gian tùy chọn MUST xuất dữ liệu theo đúng định dạng tệp cảm biến và tệp
  Schumann của hợp đồng để phần mềm dùng chung đường xử lý.
- **FR-030**: Bản phát hành MUST kèm tệp kê khai băm của mọi tệp và gốc băm được bảo vệ sửa lỗi.

### Key Entities *(include if feature involves data)*

- **Phiên (Session)**: tần số p/q, chế độ, âm mang, âm lượng, thời lượng, mốc pha, trạng thái phát.
- **Mã phiên (Sync code)**: chuỗi mang p, q, mốc pha, chế độ và mã kiểm tra; dùng để tham gia phiên.
- **Bản ghi cài đặt (Settings record)**: hai từ 64 bit được mã hóa sửa lỗi cùng thẻ băm.
- **Sự kiện nhật ký (Log entry)**: loại sự kiện, p, q, thời điểm, chế độ, băm nối chuỗi.
- **Số đo Schumann (SR reading)**: thời điểm, tần số mode 1, chất lượng.
- **Tệp cảm biến (Sensor capture)**: chuỗi thời gian và giá trị; nguồn; số mẫu.
- **Kết quả kiểm chứng (Verification report)**: tần số đo, tần số công bố, sai số, tỉ số tín hiệu trên
  nhiễu, kết luận.
- **Mục tri thức (Knowledge item)**: chủ đề, từ khóa, câu trả lời, mức bằng chứng, tài liệu.
- **Thiết bị ngang hàng (Peer)**: thiết bị cùng phiên, tham số phiên của nó, độ lệch đồng hồ ước lượng.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Ít nhất 90 % trong bộ 40 câu hỏi chuẩn được nhận đúng chủ đề ở chế độ ngoại tuyến; 100 %
  câu trả lời có mức bằng chứng hoặc là thông điệp an toàn.
- **SC-002**: 100 % câu hỏi khủng hoảng trong bộ kiểm thử nhận thông điệp có số 115 trong cùng lượt.
- **SC-003**: Hai thiết bị có đồng hồ khớp trong 3,5 ms hiển thị pha lệch dưới 10° ở 95 % lần đo.
- **SC-004**: Pha tính trên mọi thiết bị trùng nhau tuyệt đối (cùng tử số và mẫu số) cho cùng thời
  điểm chuẩn và cùng mã phiên, ở 100 % vector kiểm thử.
- **SC-005**: Sai số biểu diễn tần số của bộ tổng hợp số ở 48 kHz dưới 1 ppm; sai số tần số định thời
  vi điều khiển tham chiếu dưới 20 ppm (không kể sai số nguồn dao động).
- **SC-006**: Với dữ liệu mẫu, tần số đo sai lệch so với giá trị thật không quá 0,01 Hz.
- **SC-007**: 100 % lỗi 1 bit được sửa và 100 % lỗi 2 bit trong cùng từ mã được phát hiện trong phép
  thử vét cạn.
- **SC-008**: Không có vùng nào trên giao diện thay đổi độ sáng quá 3 lần/giây trong phép đo khung hình.
- **SC-009**: Người dùng mới bắt đầu được phiên đầu tiên trong dưới 60 giây kể từ khi mở ứng dụng.
- **SC-010**: Toàn bộ chức năng lõi hoạt động khi không có mạng.
- **SC-011**: Giao diện dùng được ở bề rộng 360 px không cuộn ngang.
- **SC-012**: Bộ kiểm thử tự động và mô phỏng người dùng đạt 100 % trước mỗi lần phát hành.

## Assumptions

- Người dùng là người Việt Nam, giao diện và cơ sở tri thức bằng tiếng Việt.
- Thiết bị chạy hệ điều hành có đồng bộ thời gian tự động; độ chính xác đồng hồ quyết định độ khớp pha.
- SR783 là sản phẩm thư giãn, giáo dục, nghiên cứu và bảo vệ người tiêu dùng; không phải trang thiết
  bị y tế. Nếu sau này có mục đích y tế, sản phẩm phải phân loại và đăng ký theo quy định hiện hành.
- Yêu cầu dùng mã Hamming và SHA-256 là yêu cầu bắt buộc của người đặt hàng, nên được nêu trong đặc
  tả dù mang tính kỹ thuật.
- Trợ lý trực tuyến và phòng nhiều thiết bị chỉ có khi ứng dụng mở trong môi trường cung cấp các dịch
  vụ đó; ngoài môi trường đó ứng dụng vẫn đầy đủ chức năng lõi.
- Điện thoại không đo được cộng hưởng Schumann tự nhiên (1 pT nhỏ hơn 1 bước số của từ kế hàng
  chục nghìn lần); việc đo Schumann thật cần thiết bị trung gian (câu chuyện 7).
- Thiết bị trung gian là hạng mục tương lai; bản mẫu hiện tại chỉ định nghĩa định dạng dữ liệu nó xuất.
