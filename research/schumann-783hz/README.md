# Nghiên cứu chuyên sâu tần số 7,83 Hz và phần mềm đồng bộ SR783

Gói nghiên cứu tự chứa, chỉ bổ sung vào kho mã (không sửa cấu trúc cũ của Spec Kit).

| Bạn cần | Mở tệp |
|---|---|
| Đọc báo cáo (chuẩn trình bày báo cáo tổng hợp KH&CN) | [`report/BAO-CAO-7.83Hz.md`](report/BAO-CAO-7.83Hz.md) · `report/BAO-CAO-7.83Hz.pdf` · `report/BAO-CAO-7.83Hz.docx` (thể thức Nghị định 30/2020) · `report/BAO-CAO-7.83Hz.html` |
| Dùng phần mềm trên điện thoại / máy tính | `app/sr783-standalone.html` (mở bằng trình duyệt, chạy ngoại tuyến) |
| Đặc tả phần mềm (Spec Kit) | [`specs/001-sr783-tro-ly-dong-bo/spec.md`](specs/001-sr783-tro-ly-dong-bo/spec.md), `plan.md`, `tasks.md`, `contracts/` |
| Hiến chương sản phẩm | [`.specify/memory/constitution.md`](.specify/memory/constitution.md) |
| Số liệu gốc của mọi bảng, hình | `results/results.json` (sinh bởi `tools/compute_results.py`) |
| Kết quả nghiệm thu mô phỏng người dùng | `acceptance/report.json`, ảnh `acceptance/screenshots/` |

## Nội dung chính

- **Chương 1** – Cơ sở vật lý: cộng hưởng Schumann, mode lý tưởng 10,59 Hz so với quan sát 7,83 Hz, biên độ cỡ 1 pT.
- **Chương 2** – AI và máy tính: xử lý tín hiệu, học máy (phương pháp lai đạt MAE 0,0299 Hz), BCI, DDS, vi điều khiển, truyền thông ELF, kênh ẩn.
- **Chương 3** – Thiết bị đầu cuối: máy phát, điện thoại (không đo được Schumann, kiểm chứng được máy phát ≤ 3,33 cm), âm thanh, ánh sáng, bằng chứng sức khỏe, pháp lý Việt Nam, phiếu kiểm định.
- **Chương 4** – Liên kết tầng bit: IEEE 754 (`0x40FA8F5C`), pha hữu tỉ, mã Hamming SECDED, SHA-256, đối chiếu Python ↔ JavaScript.
- **Chương 5** – Đặc tả SR783: trợ lý hội thoại + đồng bộ tần số trên thiết bị đa năng; bản mẫu chạy được.

## Kiểm chứng (Python ≥ 3.9; pytest; Node.js + Playwright cho nghiệm thu)

```bash
cd research/schumann-783hz
python tools/compute_results.py --check
python tools/build_figures.py --check
python tools/build_app.py --check
python tools/build_report.py --check
python -m pytest tests -q
node acceptance/simulate_users.cjs
python -m sr783 verify
sha256sum -c SHA256SUMS
```

`SHA256SUMS` liệt kê băm của mọi tệp; `ROOT_HASH.txt` niêm phong cả gói; `ROOT_HASH.secded.txt` là gốc băm
được bảo vệ bằng mã Hamming SECDED(72,64).

## Lưu ý

Báo cáo và phần mềm do trợ lý AI (Claude Code) soạn theo yêu cầu, đã kiểm thử tự động và mô phỏng người
dùng; cần chuyên gia thẩm định trước khi dùng cho mục đích chính thức. SR783 phục vụ thư giãn, giáo dục,
nghiên cứu; không chẩn đoán, không điều trị bệnh.
