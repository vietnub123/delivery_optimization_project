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

* **Chi phí Khoảng cách ($C_{dist}$ - Trọng số 1.0):** Tổn hao nhiên liệu và khấu hao phương tiện.
* **Chi phí Chờ đợi ($C_{wait}$ - Trọng số 0.3):** Hao phí quỹ lương khi tài xế nhàn rỗi chờ điểm giao mở cửa.
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
├── data/                       # Chứa dữ liệu đầu vào và nghiệm đầu ra
│   ├── locations.csv           # Tọa độ không gian
│   ├── time_windows.csv        # Ma trận khung giờ dịch vụ
│   ├── best_solution.json      # Nghiệm xuất ra từ ALNS (Vector quỹ đạo)
│   └── detailed_timeline.csv   # Lịch trình giải mã chi tiết (Output)
│
├── src/                        # Chứa logic nghiệp vụ cốt lõi
│   ├── state.py                # Không gian Trạng thái, TD-VRP, Exponential Penalty
│   ├── environment.py          # Xây dựng ma trận Không gian/Thời gian
│   ├── operators.py            # Toán tử Heuristic (Destroy/Repair)
│   ├── solver.py               # Vòng lặp ALNS & Simulated Annealing
│   ├── baselines.py            # Thuật toán khởi tạo NN & EDD
│   ├── evaluator.py            # Đánh giá Benchmarking thống kê
│   ├── visualizer.py           # Ánh xạ đồ thị
│   ├── timeline_decoder.py     # Giải mã JSON thành Lịch trình (Timetable)
│   └── io_manager.py           # Quản lý Serialization (JSON) an toàn cho NumPy
│
└── main.py                     # Entry point với cờ điều khiển (OPTIMIZE/LOAD)