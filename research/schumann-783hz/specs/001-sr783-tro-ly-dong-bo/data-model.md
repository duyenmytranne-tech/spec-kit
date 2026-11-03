# Data Model: SR783

| Thực thể | Trường | Kiểu / miền giá trị | Ràng buộc |
|---|---|---|---|
| Session | p, q | số nguyên dương < 2³² | 1 ≤ p/q ≤ 40 Hz; phân số tối giản |
| | mode | `I` (đẳng thời), `B` (hai tai), `M` (đơn âm) | mặc định `I` |
| | carrier_centi_hz | số nguyên 5000–100000 | âm mang 50–1000 Hz, mặc định 20000 |
| | volume_pct | 0–50 | chặn trên 50 |
| | session_min | 1–120 | mặc định 20 |
| | t0_ms | số nguyên ≥ 0 (ms UTC) | mốc pha 0; 0 = kỷ nguyên Unix |
| | playing | bool | |
| SyncCode | body | `SR783-1-<p>-<q>-<t0_ms>-<mode>` | xem `contracts/sync-code.md` |
| | check | 8 ký tự hex in hoa | 8 ký tự đầu của SHA-256 phần thân |
| SettingsRecord | v, cw[2], tag | 1; 2 chuỗi hex 18 ký tự; 16 ký tự hex | xem `contracts/settings-secded.md` |
| LogEntry | event, p, q, t_ms, mode | chuỗi/số nguyên | băm = SHA-256(prev + "\n" + JSON chuẩn hóa) |
| SRReading | time_utc, f1_hz, quality | ISO 8601; 7,0–9,0; `good`/`fair`/`poor` | `poor` bị loại |
| SensorCapture | time, value | giây (hoặc ms), số thực | ≥ 32 mẫu, ≥ 1 s |
| VerificationReport | f_measured, f_nominal, error_pct, snr_db, verdict | số thực; `dat`/`khong_dat`/`khong_xac_dinh` | Đạt: giá trị tuyệt đối sai số ≤ dung sai và SNR ≥ 10 dB |
| KnowledgeItem | id, keywords[], grade, answer, refs[] | grade ∈ {A,B,C,D} | refs trỏ tới danh mục tài liệu báo cáo |
| Peer | peer, presence{p,q,t0,mode,playing}, offset_ms, delay_ms | dữ liệu không tin cậy | chọn mẫu delay nhỏ nhất |

Trạng thái phiên: `stopped → playing` (Bắt đầu, lệnh, công cụ Claude) → `stopped` (Dừng, hết thời
lượng). Đổi tần số khi đang phát: khởi động lại tại pha 0 kế tiếp.
