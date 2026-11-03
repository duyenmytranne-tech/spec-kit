# Quickstart: SR783

## Dùng ngay trên thiết bị đa năng

1. Mở `app/sr783-standalone.html` bằng trình duyệt của điện thoại, máy tính bảng hoặc máy tính
   (không cần mạng, không cài đặt). Khi mở trong Claude (Artifact), trợ lý có thêm chế độ "Hỏi Claude"
   và phòng nhiều thiết bị.
2. Gõ `7,83 Hz là gì?` → nhận câu trả lời có mức bằng chứng A và tài liệu.
3. Gõ `bắt đầu đẳng thời 10 phút` (hoặc bấm **Bắt đầu**) → âm bắt đầu tại pha 0 kế tiếp.
4. Bấm **Tạo mã phiên**, gửi mã cho thiết bị thứ hai, dán mã và bấm **Tham gia** → hai vòng pha quay
   trùng nhau.
5. Mục **Kiểm chứng thiết bị** → **Dùng dữ liệu mẫu** → kết quả khoảng 7,85 Hz, kết luận Đạt.
6. Mục **Toàn vẹn** → **Lật 1 bit rồi nạp lại** → ứng dụng báo đã tự sửa; **Lật 2 bit** → phát hiện và
   khôi phục mặc định.

## Tái lập và kiểm thử (máy tính có Python ≥ 3.9)

```bash
cd research/schumann-783hz
python tools/compute_results.py --check     # mọi số liệu báo cáo trùng từng byte
python tools/build_figures.py --check       # 9 hình SVG trùng từng byte
python tools/build_app.py --check           # ứng dụng = mẫu + cơ sở tri thức
python -m pytest tests -q                   # bộ kiểm thử (cần pytest)
node acceptance/simulate_users.cjs          # mô phỏng 7 kiểu người dùng (cần Playwright + Chromium)
python -m sr783 verify                      # kiểm tra SHA256SUMS + gốc băm SECDED
```

## Phần mềm máy tính dòng lệnh (thiết bị trung gian phần mềm)

```bash
python -m sr783 bits 7.83                   # bản đồ bit, DDS, Timer1
python -m sr783 phase --p 783 --q 100       # pha hiện tại theo UTC
python -m sr783 tone --mode isochronic --seconds 60 --out phien.wav   # WAV bit-exact cho loa/TV
python -m sr783 code --p 783 --q 100 --t0 1793664000000 --mode I      # mã phiên
```
