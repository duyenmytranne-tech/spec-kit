# Contract: mã phiên và công thức pha

## Công thức pha (bắt buộc, số học số nguyên)

```text
f      = p / q  Hz                (phân số tối giản; 7,83 Hz = 783/100)
Δt     = t_ms − t0_ms             (mili giây UTC, số nguyên)
phase  = (p · Δt) mod (1000 · q)  / (1000 · q)      ∈ [0, 1)
degree = phase · 360
cycles = floor(p · Δt / (1000 · q))
```

Vector kiểm thử (phải khớp tuyệt đối; nguồn `results/results.json → synth.phase_vectors`):

| p | q | t_ms | t0_ms | tử số pha | mẫu số | độ |
|---|---|---|---|---|---|---|
| 783 | 100 | 1793664000000 | 0 | 0 | 100000 | 0.0000 |
| 783 | 100 | 1793664012345 | 0 | 66135 | 100000 | 238.0860 |
| 783 | 100 | 1793664000127 | 1793664000000 | 99441 | 100000 | 357.9876 |
| 7792 | 1000 | 1793664012345 | 0 | 192240 | 1000000 | 69.2064 |

Độ lệch đồng hồ δ (ms) gây lệch pha 360·f·δ/1000 độ: 1 ms → 2,82°; muốn < 10° cần δ < 3,548 ms.

**Thực thi trên thiết bị** (bắt buộc từ bản 1.0.0): thời điểm hiện tại lấy theo micro giây từ đồng hồ hệ
điều hành (`Date.now()`) hiệu chuẩn tại thời điểm đổi mili giây và nội suy bằng `performance.now()`;
pha hiện tại = (p·(t_us − 1000·t0_ms)) mod (10⁶·q) / (10⁶·q). Với t_us = 1000·t_ms công thức trùng tuyệt
đối với các vector mili giây ở trên. Lý do: dùng mili giây nguyên thì sai số lượng tử ±1 ms (±2,82°) cộng
dồn vào lệch đồng hồ (phát hiện trong vòng nghiệm thu, xem báo cáo Phụ lục C).

## Mã phiên

```text
body  = "SR783-1-" p "-" q "-" t0_ms "-" mode      mode ∈ {I, B, M}
check = upper(hex(SHA-256(UTF-8(body))))[0:8]
code  = body "-" check
```

Ví dụ: `SR783-1-783-100-1793664000000-I-9336D787`.

Quy tắc nhận mã: khớp biểu thức `^SR783-1-\d{1,9}-\d{1,9}-\d{1,15}-[IBM]-[0-9A-F]{8}$` (không phân biệt
hoa thường); tính lại `check`; sai thì từ chối với thông báo "Sai mã kiểm tra SHA-256". p = 0 hoặc
q = 0 bị từ chối.

## Phòng nhiều thiết bị (khi có)

- Tên phòng: `sr783-` + check viết thường (ví dụ `sr783-9336d787`).
- Hiện diện: `{p, q, t0, mode, playing}` (chuỗi/bool), là dữ liệu không tin cậy.
- Ước lượng lệch đồng hồ: chủ đề `ping {id, t1}` và `pong {id, to, t1, t2, t3}`;
  θ = ((t2 − t1) + (t3 − t4))/2, trễ = (t4 − t1) − (t3 − t2); giữ mẫu trễ nhỏ nhất mỗi thiết bị.
