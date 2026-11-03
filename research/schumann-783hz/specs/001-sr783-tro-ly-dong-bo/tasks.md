---

description: "Task list for SR783"
---

# Tasks: SR783 – Trợ lý hội thoại và đồng bộ tần số 7,83 Hz

**Input**: Design documents from `specs/001-sr783-tro-ly-dong-bo/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Có (yêu cầu nghiệm thu từng bước của người đặt hàng).

**Organization**: Theo câu chuyện người dùng; `[X]` = đã làm trong bản mẫu này, `[ ]` = việc tương lai.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Tạo cấu trúc gói `research/schumann-783hz/` (app, kb, sr783, tools, tests, acceptance, specs)
- [X] T002 [P] Đặt `.gitattributes` (LF) để băm SHA-256 ổn định trên mọi hệ điều hành
- [X] T003 [P] Viết hiến chương sản phẩm `.specify/memory/constitution.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

- [X] T004 Lõi bit Python: `sr783/bits.py`, `sr783/synth.py`, `sr783/physics.py`
- [X] T005 [P] Mã SECDED tổng quát `sr783/secded.py`; SplitMix64 `sr783/prng.py`
- [X] T006 [P] Toàn vẹn gói `sr783/integrity.py` (SHA256SUMS, gốc băm, gốc SECDED, chuỗi băm)
- [X] T007 Tính mọi số liệu `tools/compute_results.py` → `results/results.json`
- [X] T008 Cơ sở tri thức tiếng Việt có mức bằng chứng `kb/kb_vi.json`
- [X] T009 Lõi JavaScript bit-exact trong `app/src/sr783.template.html` (SHA-256, SECDED, phân số, pha, DDS, Timer1)

**Checkpoint**: Lõi Python và JavaScript cho cùng kết quả trên mọi vector kiểm thử.

---

## Phase 3: User Story 1 - Trò chuyện có kiểm chứng (Priority: P1) 🎯 MVP

- [X] T010 [P] [US1] Bộ câu hỏi chuẩn `acceptance/benchmark_vi.json`
- [X] T011 [US1] Lớp an toàn, lệnh, khớp chủ đề trong `app/src/sr783.template.html`
- [X] T012 [US1] Trợ lý trực tuyến tùy chọn (Claude `sample` + công cụ trang) và lối lui ngoại tuyến
- [X] T013 [US1] Đọc to câu trả lời; nhận giọng nói khi chạy độc lập

---

## Phase 4: User Story 2 - Phát và đồng bộ nhiều thiết bị (Priority: P1)

- [X] T014 [US2] Bộ phát âm đẳng thời / hai tai / đơn âm, khởi động tại pha 0 kế tiếp
- [X] T015 [US2] Đo và bù trôi đồng hồ âm thanh bằng co giãn thời gian
- [X] T016 [US2] Mã phiên có kiểm tra SHA-256 (`contracts/sync-code.md`)
- [X] T017 [US2] Phòng nhiều thiết bị: hiện diện + ping/pong ước lượng lệch đồng hồ
- [X] T018 [US2] Vòng pha 30 chu kỳ không nhấp nháy; xuất WAV 60 s đóng gói ZIP
- [X] T019 [P] [US2] CLI `python -m sr783 tone|phase|code` cho máy tính và loa/TV

---

## Phase 5: User Story 3 - Đồng bộ theo Schumann thực đo (Priority: P2)

- [X] T020 [US3] Nhập giá trị/CSV, kiểm tra dải 7,0–9,0 Hz và chất lượng, đổi sang p/q

---

## Phase 6: User Story 4 - Kiểm chứng thiết bị (Priority: P2)

- [X] T021 [US4] DFT không đều + nội suy + SNR; kết luận Đạt/Không đạt/Không xác định
- [X] T022 [US4] Dữ liệu mẫu 7,85 Hz và xuất báo cáo CSV

---

## Phase 7: User Story 5 - Toàn vẹn và tự sửa lỗi (Priority: P3)

- [X] T023 [US5] Bản ghi cài đặt SECDED(72,64) + thẻ SHA-256 (`contracts/settings-secded.md`)
- [X] T024 [US5] Tiêm lỗi 1/2 bit, chuỗi băm nhật ký, xuất nhật ký

---

## Phase 8: User Story 6 - Soi bit (Priority: P3)

- [X] T025 [US6] Bảng phân số, IEEE 754 32/64 bit, DDS, Timer1

---

## Phase 9: User Story 7 - Thiết bị trung gian (Priority: P3, tương lai)

- [ ] T026 [US7] Thiết kế mạch cuộn cảm ứng + ADC 24 bit + TCXO/GPS 1 PPS
- [ ] T027 [US7] Firmware xuất CSV theo `contracts/data-csv.md` qua USB-C/BLE
- [ ] T028 [US7] Thử nghiệm đo ở điểm nhiễu thấp; đối chiếu trạm tham chiếu
- [ ] T029 [US7] Thử nghiệm QCVN an toàn điện và tương thích điện từ trước khi lưu hành

---

## Phase 10: Polish & Cross-Cutting Concerns

- [X] T030 [P] Bộ kiểm thử `tests/` (pytest)
- [X] T031 Mô phỏng 7 kiểu người dùng `acceptance/simulate_users.cjs` + ảnh chụp
- [X] T032 Niêm phong `SHA256SUMS`, `ROOT_HASH.txt`, `ROOT_HASH.secded.txt`

## Dependencies & Execution Order

Phase 1 → Phase 2 → (US1 ∥ US2) → (US3 ∥ US4) → (US5 ∥ US6) → Polish; US7 độc lập, chỉ cần
hợp đồng dữ liệu.
