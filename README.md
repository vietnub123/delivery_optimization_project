# Hệ thống Tối ưu hóa Định tuyến Xe Đa chu kỳ (MP-TD-VRPTW)
**Multi-Period Time-Dependent Vehicle Routing Problem with Time Windows**

Dự án này triển khai một hệ thống Meta-heuristic dựa trên thuật toán Tìm kiếm Lân cận Lớn Thích ứng (ALNS - Adaptive Large Neighborhood Search) nhằm giải quyết bài toán định tuyến logistics phức tạp. Hệ thống tích hợp các yếu tố thực tiễn như Khung giờ giao hàng, Dịch chuyển thời hạn, và Động học vận tốc giao thông.

---

## 1. Giới thiệu Bài toán (Problem Statement)
Hệ thống được thiết kế để giải quyết bài toán **MP-TD-VRPTW**.
* **Mục tiêu:** Điều phối một đội xe phục vụ tập hợp các đơn hàng trải dài qua nhiều chu kỳ (nhiều ngày) nhằm cực tiểu hóa tổng chi phí vận hành (khoảng cách, thời gian) và chi phí phạt (trễ giờ, dời lịch).
* **Thử thách:** Quyết định dời một đơn hàng từ Thứ 2 sang Thứ 3 sẽ thay đổi toàn bộ quỹ đạo của cả hai ngày. Hơn nữa, vận tốc di chuyển không cố định mà thay đổi theo tình trạng giao thông thực tế.

## 2. Kiến trúc Hàm Mục tiêu (Objective Function)
Hệ thống không tối ưu hóa các con số vô hướng mà tối ưu hóa **Chi phí Tài chính thực tế**. Chúng tôi thiết lập mỏ neo: **1 km di chuyển = 4.000 VNĐ = 1 Đơn vị Chi phí**.

Hàm hội tụ Cost tổng quát được định nghĩa như sau:
$$F(S) = \sum (C_{dist} + C_{wait} + C_{delay} + C_{tw} + C_{overtime}) + M \cdot U$$

* **Chi phí Khoảng cách ($C_{dist}$ - Trọng số 1.0):** Tổn hao nhiên liệu và khấu hao phương tiện /km .
* **Chi phí Chờ đợi ($C_{wait}$ - Trọng số 0.3):** Hao phí quỹ lương khi tài xế nhàn rỗi chờ điểm giao mở cửa /phút.
* **Phạt Dời lịch ($C_{delay}$ - 2000 đv/ngày):** Trừng phạt rủi ro lưu kho do dời lịch giao sang ngày sau.
* **Phạt Vượt mốc ($C_{overtime}$ - 500 đv/phút):** Trừng phạt khi xe không thể hồi quy về Kho trước mốc giới hạn 24h.
* **Phạt Rớt đơn ($M \cdot U$ - Trọng số 1,000,000):** Ràng buộc cứng (Hard Constraint), dập tắt mọi phương án bỏ sót khách hàng.

### Cải tiến Đột phá: Hàm Phạt Thời gian Lũy tiến (Exponential Penalty)
Để mô phỏng tâm lý khách hàng (trễ 15 phút có thể chấp nhận, trễ 2 tiếng lúc nửa đêm là thảm họa), hệ thống áp dụng hàm phạt cấp số mũ thay vì hàm tuyến tính:
$$C_{tw} = C \cdot \left( e^{\alpha \cdot \Delta t} - 1 \right)$$
*(Với $\alpha = 0.05$ và $C = 10$).*

## 3. Mô hình Hóa Động học Giao thông (TD-VRP)
Hệ thống loại bỏ hoàn toàn ma trận thời gian tĩnh. Thời gian di chuyển được tính bằng cơ chế **Tích phân từng phần (Piecewise Integration)** để bảo toàn tiên đề dòng chảy FIFO.

Vận tốc biến thiên theo 4 pha trong ngày:
1. `00:00 - 06:00`: Vận tốc cơ sở (50 km/h)
2. `06:00 - 16:00`: Vận tốc chuẩn (40 km/h)
3. `16:00 - 19:00`: **Giờ cao điểm** (30 km/h)
4. `19:00 - 24:00`: Phục hồi trạng thái (50 km/h)

*Cơ chế này ép thuật toán Meta-heuristic chủ động lảng tránh các tuyến đường dài trong khung giờ kẹt xe 16h-19h.*

## 4. Kiến trúc Thuật toán (ALNS Engine)
Quy trình tối ưu hóa vận hành qua 2 pha:

### Pha 1: Baseline Heuristics (Khởi tạo cơ sở)
* **Tham lam Khoảng cách (NN - Nearest Neighbor):** Tối ưu cực đoan về không gian nhưng gây rớt đơn hàng loạt.
* **Tham lam Thời gian (EDD - Earliest Due Date):** Phục vụ 100% đơn nhưng quỹ đạo di chuyển hỗn loạn, chồng chéo. Hệ thống sử dụng nghiệm EDD làm điểm xuất phát.

### Pha 2: Meta-heuristic (Tối ưu hóa Toàn cục)
Động cơ ALNS liên tục phá hủy và tái tạo đồ thị:
1. **Phá hủy (Destroy):** `Random Removal` và `Worst Removal` (bóc tách các đỉnh gây ra chi phí cận biên lớn nhất).
2. **Tái tạo (Repair):** `Greedy Insertion`. Hệ thống sử dụng Vi phân Khoảng cách Euclid $\Delta D$ ($O(1)$) để tìm vị trí chèn tối ưu, giảm đáng kể thời gian tính toán so với việc sao chép toàn bộ không gian nghiệm.

## 5. Cấu trúc Thư mục Mã Nguồn

```text
delivery_optimization_project/
│
├── main.py                   # Điểm truy cập hệ thống (Entry point) 
├── compare.py                # Phân tích đối chứng (Benchmarking) và vẽ đường đi 
├── README.md                 # Tài liệu đặc tả kiến trúc kỹ thuật và mô hình toán học của dự án
│
├── data/                     # Lưu trữ không gian dữ liệu vận hành 
│   ├── locations.csv         # Ma trận tọa độ không gian (Euclidean) và tham số tải trọng của các đỉnh
│   ├── time_windows.csv      # Ma trận giới hạn biên thời gian (Time Windows) đa chu kỳ
│   ├── solution_alns.json    # Nghiệm tối ưu toàn cục sinh ra từ Meta-heuristic
│   ├── solution_edd.json     # Nghiệm cơ sở của hàm tham lam thời gian (Earliest Due Date)
│   └── solution_nn.json      # Nghiệm cơ sở của hàm tham lam không gian (Nearest Neighbor)
│
├── src/                      # Phân hệ mã nguồn cốt lõi (Core Business Logic)
│   ├── __init__.py           # Khởi tạo định danh package module Python
│   ├── baselines.py          # Thuật toán khởi tạo nghiệm cơ sở (Constructive Heuristics: NN, EDD)
│   ├── environment.py        # Tiền xử lý môi trường: Thiết lập ma trận khoảng cách và giới hạn không gian
│   ├── evaluator.py          # Thuật toán định lượng thống kê và đánh giá vi phân nghiệm đầu ra
│   ├── io_manager.py         # Giao thức tuần tự hóa (Serialization) và quản lý luồng dữ liệu JSON/CSV
│   ├── operators.py          # Toán tử Heuristic can thiệp đồ thị: Phá hủy (Destroy) và Tái tạo (Repair)
│   ├── solver.py             # Động cơ vòng lặp Adaptive Large Neighborhood Search (ALNS)
│   ├── state.py              # Định nghĩa Không gian Trạng thái, phương trình hội tụ F(S) và mô hình TD-VRP
│   └── visualizer.py         # Phân hệ nội suy hệ tọa độ và ánh xạ trực quan hóa đồ thị hình học
│
└── tests/                    # Phân hệ lưu trữ kịch bản kiểm thử (Test Cases & Experiments)
    ├── test3/                # Dữ liệu đường chạy 100 iters
    │
    └── test4/                # Dữ liệu đường chạy 1000 iters
        ├── locations.csv
        ├── time_windows.csv
        ├── report.md         # Báo cáo kết xuất kết quả kiểm chuẩn định kỳ
        ├── solution_alns.json
        ├── solution_edd.json
        └── solution_nn.json

```
## 6. Hướng dẫn chạy chương trình

1. **Khởi tạo môi trường:**
   Chạy `src/environment.py` để thực hiện tiền xử lý dữ liệu đầu vào và khởi tạo ma trận khoảng cách Euclid làm cơ sở dữ liệu.

2. **Tối ưu hóa định tuyến:**
   Chạy `main.py` để kích hoạt lõi thuật toán tối ưu ALNS và các baselines (NN, EDD). Chương trình nạp dữ liệu từ thư mục sản xuất `data/` và tự động xuất kết quả nghiệm dạng JSON ngược lại vào `data/`. Sau đó, tiến hành copy toàn bộ các file dữ liệu này vào thư mục test tương ứng (ví dụ: `tests/test4/`).

3. **Kiểm chuẩn và vẽ đồ thị đối chứng:**
   Chạy `compare.py` để giải mã các tệp nghiệm từ `tests/test4/`, chạy mô phỏng đo lường hiệu năng thực tế (Cost, Distance, Violations,...) và xuất ra các biểu đồ so sánh và 3 tệp quỹ đạo không gian.
