# Contract: bản ghi cài đặt SECDED(72,64) + thẻ SHA-256

## Bố cục bit

```text
word0 (64 bit) = p << 32 | q
word1 (64 bit) = carrier_centi_hz << 40 | volume_pct << 32 | mode << 28 | session_min << 20 | flags << 12
                 (24 bit)              (8 bit)              (4 bit)      (8 bit)              (8 bit) + 12 bit dự trữ = 0
mode: 1 = I (đẳng thời), 2 = B (hai tai), 3 = M (đơn âm)
```

## Mã SECDED(72,64)

- Vị trí 1..71 là mã Hamming: bit chẵn lẻ ở các lũy thừa của 2 (1, 2, 4, …, 64); 64 bit dữ liệu lấp các
  vị trí còn lại theo thứ tự tăng dần, bit dữ liệu 0 (LSB) trước.
- Vị trí 0 là bit chẵn lẻ tổng (chẵn trên vị trí 0..71).
- Từ mã là số nguyên 72 bit (bit i = vị trí i), ghi bằng 18 ký tự hex in hoa.
- Giải mã: s = XOR các vị trí có bit 1 (1..71), P = chẵn lẻ toàn từ.
  s = 0, P = 0 → nguyên vẹn; P = 1 → sửa bit tại vị trí s (s = 0: bit chẵn lẻ tổng);
  s ≠ 0, P = 0 → lỗi 2 bit, không sửa.

## Lưu trữ

```json
{"v": 1, "cw": ["<18 hex>", "<18 hex>"], "tag": "<16 hex>"}
```

`tag` = 16 ký tự đầu của SHA-256(cw[0] + cw[1]). Khi nạp: giải mã từng từ → nếu có lỗi 2 bit thì khôi
phục mặc định; nếu sửa được thì mã hóa lại và kiểm tra `tag`; `tag` sai → khôi phục mặc định.

## Vector kiểm thử (nguồn `results/results.json → settings_record`)

| Trường | Giá trị |
|---|---|
| p, q, carrier_centi_hz, volume_pct, mode, session_min, flags | 783, 100, 20000, 30, 1, 20, 0 |
| word0 / word1 | `0000030F00000064` / `004E201E11400000` |
| cw[0] / cw[1] | `000001878000010C51` / `0027100F0850010007` |
| tag | `c58816fc657fd7b8` |
