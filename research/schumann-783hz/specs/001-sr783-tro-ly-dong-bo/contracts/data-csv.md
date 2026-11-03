# Contract: tệp dữ liệu nhập (CSV UTF-8)

## Tệp cảm biến (kiểm chứng thiết bị) – từ điện thoại hoặc thiết bị trung gian

```text
time_s,field_uT
0.0000,45.15
0.0101,47.10
...
```

- Cột 1: thời gian (giây; nếu tiêu đề chứa `ms` hoặc khoảng thời gian > 5000 thì hiểu là mili giây).
- Cột 2: giá trị cảm biến (đơn vị tùy ý, ví dụ µT của một trục từ kế hoặc độ lớn).
- Dấu phân cách `,` `;` hoặc tab; dòng không phải số bị bỏ qua; lấy mẫu không cần đều.
- Tối thiểu 32 mẫu và 1 giây; khuyến nghị ≥ 20 s, tốc độ ≥ 50 Hz.
- Kết quả: tần số đo trong 6–10 Hz, sai số so với tần số công bố, SNR (dB), kết luận.

## Tệp Schumann thực đo – từ trạm quan trắc hoặc thiết bị trung gian

```text
time_utc,f1_hz,quality
2026-11-03T08:00:00Z,7.801,good
2026-11-03T08:10:00Z,7.792,good
2026-11-03T08:20:00Z,9.600,poor
```

- `f1_hz` ngoài 7,0–9,0 Hz hoặc `quality = poor` bị loại; dòng hợp lệ cuối cùng được chọn.

## Báo cáo kiểm chứng xuất ra (minh họa định dạng; giá trị thật do ứng dụng tính)

```text
nguon,so_mau,tan_so_do_hz,tan_so_cong_bo_hz,sai_so_phan_tram,snr_db,ket_luan
"du lieu mau (7,85 Hz, nhieu 0,3 µT, buoc luong tu 0,15 µT)",3007,7.84980,7.83000,0.2529,43.90,dat
```
