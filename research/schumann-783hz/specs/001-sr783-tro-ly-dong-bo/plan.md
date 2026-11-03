# Implementation Plan: SR783 – Trợ lý hội thoại và đồng bộ tần số 7,83 Hz

**Branch**: `001-sr783-tro-ly-dong-bo` | **Date**: 2026-11-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-sr783-tro-ly-dong-bo/spec.md`

**Note**: Gói nghiên cứu là một dự án Spec Kit độc lập; đặt `SPECIFY_FEATURE_DIRECTORY` tới thư mục
này khi chạy các lệnh Spec Kit.

## Summary

Một ứng dụng một tệp HTML ("thiết bị phần mềm") chạy trực tiếp trên trình duyệt của điện thoại, máy
tính bảng, máy tính và TV. Lõi đồng bộ biểu diễn tần số bằng phân số p/q và tính pha bằng số nguyên
theo mili giây UTC, nên mọi thiết bị đồng hồ đúng cho cùng pha mà không cần máy chủ. Trợ lý hội thoại
ngoại tuyến dựa trên cơ sở tri thức có mức bằng chứng; khi chạy trong Claude, trợ lý có thể hỏi Claude
và gọi các thao tác của trang (đặt tần số, bắt đầu, dừng…), còn phòng nhiều thiết bị đo độ lệch đồng
hồ giữa các máy. Cài đặt lưu bằng SECDED(72,64) kèm thẻ SHA-256; nhật ký là chuỗi băm. Một lõi tham
chiếu Python (chỉ thư viện chuẩn) tính mọi số liệu của báo cáo và là chuẩn đối chiếu bit cho bản JavaScript.

## Technical Context

**Language/Version**: JavaScript ES2020 (trình duyệt), HTML5/CSS; Python ≥ 3.9 cho lõi tham chiếu

**Primary Dependencies**: Không có thư viện ngoài. API nền tảng: Web Audio (OscillatorNode,
PeriodicWave, ConstantSourceNode), BigInt, TextEncoder; tùy chọn: Web Speech (đọc/nhận giọng nói),
năng lực thời gian chạy của Claude (`sample`, `room`, `downloads`)

**Storage**: localStorage (bản ghi cài đặt SECDED + thẻ SHA-256), bộ nhớ tạm khi bị chặn; không có máy chủ

**Testing**: pytest (lõi Python, tính nhất quán báo cáo, đặc tả, tệp ứng dụng); Playwright/Chromium
(mô phỏng người dùng, đối chiếu bit Python ↔ JavaScript, đo nhấp nháy, ảnh chụp giao diện)

**Target Platform**: Trình duyệt hiện đại trên Android, iOS/iPadOS, Windows, macOS, Linux, ChromeOS;
nhúng làm Artifact trong Claude

**Project Type**: Ứng dụng web một tệp + thư viện/CLI tham chiếu

**Performance Goals**: Phản hồi ngoại tuyến < 50 ms; phân tích tệp cảm biến 30 s < 1 s; vòng pha 60 khung/s

**Constraints**: Ngoại tuyến trước; không nhấp nháy > 3 lần/s; âm lượng ≤ 50 %; tệp ứng dụng < 1 MB;
lệch pha < 10° khi đồng hồ lệch < 3,548 ms

**Scale/Scope**: 1 người dùng mỗi thiết bị; phòng nhóm cỡ vài chục thiết bị; 7 câu chuyện người dùng

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Đối chiếu hiến chương SR783 (`.specify/memory/constitution.md`):

| Nguyên tắc | Cách đáp ứng | Kết quả |
|---|---|---|
| I. Sự thật và an toàn | Mọi mục tri thức có mức A–D và số tài liệu; lớp an toàn khủng hoảng/y tế chạy trước | PASS |
| II. Đồng nhất đến bit | Tần số p/q, pha số nguyên; `compute_results.py --check`; kiểm thử song song Python ↔ JS | PASS |
| III. Ngoại tuyến trước | Không phụ thuộc mạng; Claude và phòng là tùy chọn có lối lui | PASS |
| IV. An toàn thị giác, thính giác | Không đổi độ sáng ở 7,83 Hz; đo nhấp nháy trong nghiệm thu; âm lượng ≤ 50 % | PASS |
| V. Tự sửa lỗi, chống giả mạo | SECDED(72,64) + thẻ SHA-256; chuỗi băm; SHA256SUMS + gốc SECDED | PASS |
| VI. Đa năng, trường tồn | Một tệp HTML; Python chỉ thư viện chuẩn; chỉ bổ sung, không xóa | PASS |
| VII. Nghiệm thu mô phỏng | `acceptance/simulate_users.cjs` với 7 kiểu người dùng | PASS |

Re-check sau Phase 1: PASS (không phát sinh vi phạm).

## Project Structure

### Documentation (this feature)

```text
specs/001-sr783-tro-ly-dong-bo/
├── spec.md              # đặc tả (WHAT/WHY)
├── checklists/
│   └── requirements.md  # danh mục kiểm tra chất lượng đặc tả
├── plan.md              # tệp này
├── research.md          # Phase 0: quyết định kỹ thuật
├── data-model.md        # Phase 1: thực thể, trường, ràng buộc
├── quickstart.md        # Phase 1: chạy và nghiệm thu
├── contracts/           # Phase 1: hợp đồng dữ liệu và thao tác
│   ├── sync-code.md
│   ├── settings-secded.md
│   ├── data-csv.md
│   └── assistant-tools.md
└── tasks.md             # Phase 2: danh sách nhiệm vụ
```

### Source Code (repository root)

```text
research/schumann-783hz/
├── app/
│   ├── src/sr783.template.html   # mã nguồn ứng dụng (giao diện + lõi JS)
│   ├── sr783.html                # bản dựng dạng Artifact (không có doctype/head/body)
│   └── sr783-standalone.html     # bản dựng ngoại tuyến hoàn chỉnh
├── kb/kb_vi.json                 # cơ sở tri thức tiếng Việt (nhúng vào ứng dụng)
├── sr783/                        # lõi tham chiếu Python, chỉ thư viện chuẩn
├── tools/                        # tính kết quả, dựng hình, dựng ứng dụng, dựng báo cáo, niêm phong
├── results/results.json          # mọi số liệu của báo cáo
├── tests/                        # pytest
└── acceptance/                   # mô phỏng người dùng (Playwright) + ảnh chụp
```

**Structure Decision**: Một ứng dụng web một tệp (đa nền tảng, không cài đặt) cộng một thư viện
tham chiếu Python. Không tách frontend/backend vì không có máy chủ.

## Complexity Tracking

Không có vi phạm hiến chương cần biện minh.
