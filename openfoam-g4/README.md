# OpenFOAM trên Colab G4: Mac Mini M4 đẩy code, G4 chạy hết công suất, không lưu gì

Bộ công cụ này nối ba nơi thành một dây chuyền tự động:

- **Mac Mini M4**: bạn sửa case OpenFOAM, `foamctl` ký case bằng SHA-256 rồi đẩy lên GitHub.
- **GitHub**: chỉ chứa code, case và tệp job (cấu hình). Không chứa kết quả.
- **Colab G4** (NVIDIA RTX PRO 6000 Blackwell, 96 GB VRAM): notebook theo dõi hàng đợi, kiểm tra từng bit của case, tự đo phần cứng, tự chia việc cho toàn bộ lõi CPU và GPU, tự chữa lỗi, in kết quả ra ô notebook.

OpenFOAM mặc định chạy **một tiến trình trên một lõi** và **không dùng GPU**. Bộ chạy `g4runner` sửa điều đó tự động, không cần bạn chỉnh tay (xem mục [Tự động khai thác G4](#tự-động-khai-thác-g4)).

## Kiến trúc

```text
Mac Mini M4                      GitHub (private)               Colab G4 (RAM, /dev/shm)
──────────────                   ───────────────                ─────────────────────────────────────────
cases/myCase/  ──foamctl submit─▶ cases/myCase/   ──git fetch──▶ TT0 kiểm SHA-256 từng bit, quét bảo mật
  SHA-256 manifest               jobs/<id>.json     (30 s/lần)    TT1 lưới   (snappyHexMesh song song)
  jobs/<id>.json                 jobs/active.json                 TT2 khởi tạo
  jobs/active.json                                                TT4 chia miền, OGL dựng nền (TT5)
                                                                  TT3 giải   (CPU ngay, chuyển GPU khi lợi)
                                                                  TT8 theo dõi, tự chữa phân kỳ, dừng đúng hạn
                                                                  TT6 đọc KPI  →  TT7 in ra ô notebook
```

Mỗi khâu **TTk** thực thi nhóm chức năng **CNk** của báo cáo *OpenFOAM chi tiết* (TT1 ↔ CN1 lưới, …, TT8 ↔ CN8 kiểm chứng; TT0 là nền: môi trường và toàn vẹn). Bảng 21 ứng dụng nằm trong `g4runner/apps.py`; báo cáo HTML được kiểm tra khớp với tệp này từng ô.

## Chế độ không lưu

Đây là chế độ duy nhất của bộ chạy, không phải tuỳ chọn.

| Nơi | Bộ chạy ghi gì | Ghi chú |
| --- | --- | --- |
| Colab: tệp log | Không gì | Log của solver được đọc trực tiếp từ luồng ra, chỉ giữ 400 dòng cuối trong RAM để báo lỗi |
| Colab: dữ liệu tính | Chỉ trong RAM (`/dev/shm` hoặc tmpfs riêng) | Mất khi runtime kết thúc; `purgeWrite` giữ tối đa `keep_times` mốc thời gian |
| Colab: Google Drive | Không mount | |
| Colab: đầu ra notebook | Hiện trên màn hình | Bật *Omit code cell output when saving this notebook* để Colab không lưu |
| GitHub | Không đẩy gì từ Colab | Token chỉ cần quyền đọc |
| Mac | Tệp job và `jobs/active.json` | Do bạn commit, là cấu hình chứ không phải kết quả |

Nằm ngoài tầm của bộ chạy: nhật ký vận hành của chính Google Colab và GitHub, lịch sử git bạn đã đẩy, và Colab Secrets (lưu trong tài khoản Google của bạn; nếu không muốn, bỏ trống để notebook hỏi token bằng `getpass` mỗi phiên). Nếu RAM-disk quá nhỏ và không gắn được tmpfs, bộ chạy báo rõ là đang dùng ổ đĩa tạm của VM (bị huỷ cùng runtime).

## Cài đặt một lần

### 1. Trên Mac Mini M4

Cài công cụ dòng lệnh của Apple (có `git` và `python3` ≥ 3.9):

```bash
xcode-select --install
```

Lấy bộ công cụ về và kiểm tra:

```bash
git clone https://github.com/<owner>/<repo>.git && cd <repo>/openfoam-g4
```

```bash
./foamctl doctor
```

Tuỳ chọn, để thử nhanh trên chính Mac M4 trước khi đẩy: OpenFOAM 14 có gói ARM64 cho Ubuntu 22.04, 24.04 và 26.04, nên một máy ảo Ubuntu ARM64 (ví dụ OrbStack hoặc UTM) cài được `openfoam14` bằng apt và chạy `blockMesh`, `checkMesh` với tốc độ gốc của chip.

### 2. Trên GitHub

1. Tạo repo **private**, chép thư mục `openfoam-g4/` vào (ở gốc repo hoặc giữ nguyên tên thư mục).
2. Tạo *fine-grained personal access token* chỉ cho repo đó, quyền **Contents: Read-only**. Colab chỉ đọc nên không cần quyền ghi.

### 3. Trên Colab

1. *File → Open notebook → GitHub*, chọn repo, mở `openfoam-g4/colab/OpenFOAM_G4.ipynb`.
2. *Runtime → Change runtime type* → **G4**.
3. *Edit → Notebook settings* → tick **Omit code cell output when saving this notebook**.
4. *Secrets*: `GH_REPO` = `owner/repo`, `GH_TOKEN` = token ở bước 2. Nếu bộ công cụ nằm ở gốc repo, thêm `G4_SUBDIR` để trống.
5. *Runtime → Run all*. Ô cuối đo phần cứng, cài OpenFOAM 14 (khoảng vài phút mỗi phiên vì không lưu bộ đệm), rồi theo dõi hàng đợi mỗi 30 giây.

Colab bản thường không tự khởi động notebook khi có push; khi phiên còn sống, bộ theo dõi tự nhận job mới. Với Colab Pro+, bật chạy nền để phiên kéo dài tới 24 giờ sau khi đóng trình duyệt.

## Vòng làm việc hằng ngày

Sửa case trên Mac, rồi gửi:

```bash
./foamctl submit cases/myCase --app ud01 --gpu auto --kpi Cd:postProcessing/forceCoeffs/0/forceCoeffs.dat:Cd:mean_last:100
```

Lệnh trên kiểm tra bảo mật, tính manifest SHA-256, ghi `jobs/<id>.json`, thêm id vào `jobs/active.json`, commit và `git push` (thử lại sau 2, 4, 8, 16 giây nếu mạng lỗi). Trong vòng 30 giây, ô notebook trên Colab bắt đầu in tiến độ và cuối cùng in bảng kết quả.

Chạy một ứng dụng mẫu của báo cáo (tutorial OpenFOAM 14 đã kiểm chứng), ví dụ bồn trộn với 6 tốc độ khuấy chạy cùng lúc:

```bash
./foamctl submit --template ud07
```

Xem 21 ứng dụng, hồ sơ G4 và khâu thực thi của từng ứng dụng:

```bash
./foamctl apps
```

Muốn bỏ một job khỏi hàng đợi: sửa `jobs/active.json`, commit, push. Bộ chạy không tự xoá job nào.

## Tự động khai thác G4

| Tài nguyên | OpenFOAM mặc định | Bộ chạy làm tự động | Kiểm chứng ngay trong phiên |
| --- | --- | --- | --- |
| Lõi CPU | 1 tiến trình | `decomposePar` (scotch, tự lùi về hierarchical nếu bản build thiếu scotch) với số tiến trình = số lõi vật lý, `mpirun --bind-to core --map-by core` | % CPU bận đo từ `/proc/stat`, in cuối job |
| Nhiều biến thể | Chạy lần lượt | Chạy đồng thời, mỗi biến thể một bộ lõi riêng (`--cpu-set`), mỗi bộ ≥ 4 lõi, giới hạn theo RAM | Mỗi biến thể có % CPU riêng |
| GPU | Không dùng | Áp suất (`p`, `p_rgh`) lên GPU qua OGL (Ginkgo CG, `executor cuda`) khi đủ điều kiện; chuyển giữa chừng khi OGL dựng xong và đo thấy nhanh hơn ≥ 10 % | Giây mỗi bước của CPU và GPU, đo ngay trên lần chạy |
| GPU lúc OpenFOAM không cần | Đứng không | Làn mô hình: chạy script Python của bạn (đã ký SHA-256) trên GPU cùng lúc | % GPU của mô hình |
| Luồng siêu phân luồng | Bị MPI chiếm lẫn lộn | Tiến trình MPI ghim vào luồng chính của mỗi lõi; luồng anh em dành cho việc dựng OGL hoặc mô hình | Ảnh hưởng đo được lên tốc độ CPU |
| RAM | Ghi kết quả ra đĩa | Thư mục làm việc là tmpfs; `writeFormat binary`; `purgeWrite` | Đỉnh RAM in cuối job |
| Bộ nhớ ECC | Không xem | Đọc bộ đếm Hamming SECDED (`nvidia-smi -q -d ECC`); có lỗi không sửa được thì tắt GPU | In số lỗi đã sửa / không sửa được |
| Thời gian phiên | Bị cắt ngang | Dừng sạch bằng `stopAt noWriteNow` trước hạn, vẫn in KPI | Trạng thái `stopped_at_deadline` |

Điều kiện để chuyển sang GPU: GPU khoẻ, case không có lưới trượt (cyclicAMI hoặc ghép không trùng lưới), không phải phương pháp hạt (DSMC/MD), lưới ≥ 0,5 triệu ô, và phần việc còn lại đủ dài để bù chi phí khởi động lại. OGL ghi nhận đã thử với OpenFOAM 10 và v2212; với v14 bộ chạy coi đây là thử nghiệm: dựng lỗi hoặc chạy lỗi thì tự quay về CPU và ghi chú trong kết quả.

## CPU và GPU song song

Không lưu gì nghĩa là OGL phải dựng lại mỗi phiên. Nếu chờ dựng xong mới chạy, thời gian dựng cộng thẳng vào job. Bộ chạy làm song song:

1. Ngay khi phiên mở, `OglBuilder` dựng OGL ở nền qua sáu khâu: kiểm tra (GPU khoẻ, `nvcc` nhắm được đúng `sm_` đọc từ `nvidia-smi`, cmake ≥ 3.18), tải mã (nhánh `dev`, lỗi thì thử thẻ phát hành mới nhất), cấu hình, biên dịch, cài đặt vào RAM, chạy thử 3 bước trên GPU. Việc dựng chạy trên luồng anh em của siêu phân luồng (máy không có siêu phân luồng thì trên vài lõi dành riêng) với độ ưu tiên thấp nhất.
2. Solver bắt đầu ngay trên CPU, không chờ.
3. OGL xong: solver chạy thêm 20 bước để đo tốc độ CPU khi máy đã rảnh, rồi ghi mốc hiện tại và dừng (`stopAt writeNow`), đổi bộ giải áp suất sang OGL, chạy tiếp từ mốc đó.
4. Sau 20 bước trên GPU: nhanh hơn ≥ 10 % thì giữ, không thì quay về CPU. Mọi con số đo được in ra.

Mô hình năng lực (`./foamctl estimate`) tính cả ba cách: chỉ CPU, dựng trước rồi GPU, và song song. Ví dụ 10 triệu ô RANS × 2 000 vòng: 0,463 h, 0,681 h và 0,495 h cho job đầu phiên; từ job thứ hai (OGL đã sẵn) cách song song còn 0,301 h. Với 20 triệu ô × 20 000 vòng: 9,26 h, 6,03 h và 5,84 h.

## Làn mô hình

Khi OpenFOAM không giữ GPU, GPU chạy được mô hình của bạn cùng lúc (huấn luyện mô hình thay thế từ kết quả mô phỏng, suy luận…):

```bash
./foamctl submit-model models/surrogate --script train.py -- --epochs 20
```

- Chỉ chạy khi trong notebook bật Secret `G4_ALLOW_MODELS` = `1`: đây là mã Python của bạn, tệp job không tự bật được.
- Thư mục script phải khớp manifest SHA-256 ký trên Mac.
- Trọng tài GPU bảo đảm mô hình và OpenFOAM không dùng GPU cùng lúc; mô hình chạy trên vài luồng CPU solver không dùng, ưu tiên thấp, môi trường không có token GitHub.
- Bộ đệm Hugging Face, torch, pip, matplotlib và thư mục làm việc nằm trong RAM; đầu ra chỉ in ra ô notebook.

## Tự sửa lỗi

| Sự cố | Phát hiện | Hành động |
| --- | --- | --- |
| Case bị sửa dù 1 bit | Manifest SHA-256 khác | Từ chối job, liệt kê tệp khác |
| Case chứa mã chạy được | `systemCall`, `#codeStream`, `coded…`, `libs` theo đường dẫn | Từ chối (chỉ người vận hành Colab mở bằng `G4_ALLOW_CODED=1`) |
| Thiếu thư viện scotch | Lỗi `decomposePar` | Chia lại bằng hierarchical |
| Lỗi gắn lõi MPI | Thông báo của Open MPI | Chạy lại với cách gắn an toàn hơn |
| Phân kỳ (NaN, ngắt dấu phẩy động) | Đọc luồng ra từng dòng | Quay về mốc tốt gần nhất, giảm bước thời gian hoặc hệ số nới lỏng, rồi upwind; tối đa 3 lần (đặt được 0–5); kết quả được đánh dấu cần kiểm chứng lại |
| GPU lỗi khi chạy | Mã thoát khác 0 khi bật GPU | Khôi phục `fvSolution` CPU và chạy tiếp từ mốc mới nhất |
| GPU chậm hơn mong đợi | Đo 20 bước sau khi chuyển | Quay về CPU, chạy tiếp từ mốc mới nhất |
| Dựng OGL lỗi | Khâu dựng báo lỗi | Thử thẻ phát hành mới nhất; vẫn lỗi thì cả phiên chạy CPU, lý do in ra |
| Sắp hết phiên | Đồng hồ hạn | `stopAt noWriteNow`, in KPI đã có |
| Mạng lỗi khi push/fetch | Lệnh git thất bại | Thử lại sau 2, 4, 8, 16 giây |

Mốc thời gian hỏng được dời sang `.g4/quarantine/` trong RAM, không bị xoá.

## An toàn và bảo mật

- Job là cấu hình JSON, không phải script. Mọi trường được kiểm theo danh sách cho phép; giá trị không được chứa `# $ ; { } \` hoặc xuống dòng.
- `Allrun` không bao giờ được chạy như shell. Bộ chạy chỉ đọc các dòng `runApplication` / `runParallel` có công cụ OpenFOAM trong danh sách cho phép; nếu trước bước giải có dòng không tự động hoá được, job bị từ chối thay vì bỏ qua âm thầm.
- Token GitHub chỉ nằm trong biến môi trường của phiên; git lấy nó qua một script askpass không chứa bí mật; `credential.helper` bị tắt.
- Notebook không mount Drive, bộ chạy không cần quyền ghi GitHub.

## Ước tính năng lực

```bash
./foamctl estimate --cells-m 20 --physics incompressible_transient --iterations 20000
```

Cùng công thức với máy tính trong báo cáo HTML; hai bản cho kết quả giống nhau tới từng bit (có kiểm thử). Các hằng số mặc định là giả định có ghi rõ; trên Colab bộ chạy thay bằng số đo được (băng thông triad, băng thông GPU, FP64, PCIe, chi phí mỗi ô mỗi bước).

## Kiểm thử

```bash
python3 -m pytest -p no:cacheprovider openfoam-g4/tests
```

Các kiểm thử đầu–cuối cần OpenFOAM và MPI; thiếu thì tự bỏ qua. Đã chạy được thật với gói OpenFOAM v1912 của Ubuntu 24.04: chạy song song, tự chữa phân kỳ, dừng đúng hạn, hai biến thể đồng thời trên bộ lõi riêng, từ chối case nguy hiểm, phát hiện lật 1 bit, kế hoạch Allrun, và cả chuỗi Mac → Git → bộ theo dõi.

Cơ chế chuyển trực tuyến được kiểm thử trên OpenFOAM thật bằng một bộ tăng tốc thay thế (đổi GAMG sang PCG), đi đúng đường đo → `writeNow` → đổi bộ giải → `latestTime` → đo → quyết định. Làn mô hình được kiểm thử với script mẫu: bị giam đúng CPU, không thấy token, bộ đệm trong RAM, chạy cùng lúc với một job OpenFOAM.

Chưa kiểm thử được trong môi trường phát triển (không có GPU, không có Colab): dựng và chạy OGL thật, cài `openfoam14` bằng apt, đo băng thông GPU. Các phần này có đường lùi tự động về CPU và in lý do.

## Giới hạn đã biết

- Thông số Colab G4 (số vCPU, RAM, ổ đĩa, giá theo compute unit) không được Google công bố đầy đủ; bộ chạy đo trong phiên thay vì giả định.
- Ghép preCICE (ud03, ud11, ud13) chưa được tự động hoá.
- Gói OpenFOAM v1912 của Ubuntu 24.04 có lỗi function object (`dictionary::digest` trong `OSHA1stream`); KPI từ function object được kiểm thử bằng tệp `.dat` mẫu đúng định dạng.
