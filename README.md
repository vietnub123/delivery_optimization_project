# MP-VRPTW: Tối ưu hóa Lập lịch Giao hàng Đa chu kỳ bằng ALNS

Dự án này triển khai hệ thống giải quyết **Bài toán Định tuyến Phương tiện Đa chu kỳ có Khung thời gian** (Multi-Period Vehicle Routing Problem with Time Windows - MP-VRPTW). Hệ thống sử dụng thuật toán Meta-heuristic **Tìm kiếm Lân cận Thích ứng Cỡ lớn** (Adaptive Large Neighborhood Search - ALNS) để tối ưu hóa không gian phân bổ đơn hàng trong chu kỳ một tuần làm việc.

## 1. Cơ sở Lý thuyết và Mô hình Toán học

Bài toán được mô hình hóa dưới dạng bài toán tối ưu hóa tổ hợp đa mục tiêu. Hàm mục tiêu $F(x)$ được thiết lập để cực tiểu hóa sự kết hợp tuyến tính của các biến trạng thái:

$$F(x) = W_d \cdot C_{distance} + W_w \cdot C_{wait} + P_{delay} + P_{unassigned} + P_{tw}$$

Trong đó:
* **$C_{distance}$**: Tổng khoảng cách không gian (Euclid).
* **$C_{wait}$**: Tổng thời gian chờ đợi (tĩnh) khi phương tiện tiếp cận nút khách hàng sớm hơn điểm cận dưới của khung thời gian.
* **$P_{delay}$**: Hàm phạt tuyến tính đối với các cấu trúc bị dời chu kỳ giao hàng (trễ hẹn sang ngày hôm sau).
* **$P_{unassigned}$**: Hệ số phạt tuyệt đối đối với các đơn hàng không được phân bổ vào mạng lưới.
* **$P_{tw}$**: Hệ số phạt vi phạm ràng buộc khung thời gian cứng.

## 2. Kiến trúc Hệ thống (Project Structure)

Dự án được phân rã thành các phân hệ (modules) độc lập tuân thủ nguyên lý Đơn trách nhiệm (Single Responsibility Principle):

```text
delivery_optimization_project/
├── data/
│   ├── locations.csv          # Ma trận tọa độ không gian và nhu cầu
│   └── time_windows.csv       # Ràng buộc thời gian đa chu kỳ
├── src/
│   ├── __init__.py
│   ├── environment.py         # Tiền xử lý, chuẩn hóa không gian metric và thời gian
│   ├── state.py               # Đặc tả không gian trạng thái DeliveryState
│   ├── operators.py           # Toán tử Heuristic: Destroy (ngẫu nhiên/tồi nhất) và Repair (tham lam)
│   ├── solver.py              # Động cơ ALNS tích hợp Simulated Annealing & Roulette Wheel
│   ├── baselines.py           # Thuật toán sinh nghiệm cơ sở (Nearest Neighbor, Earliest Due Date)
│   ├── evaluator.py           # Nội suy và định lượng các tham số thống kê (Benchmarking)
│   └── visualizer.py          # Ánh xạ đồ thị topo đa chu kỳ lên mặt phẳng 2D
├── main.py                    # Trình điều phối trung tâm (Entry Point)
└── README.md                  # Tài liệu đặc tả kỹ thuật


## 3. Tiền xử lý dữ liệu với `src/environment.py`
Thực thi tập lệnh `src/environment.py` để khởi tạo quy trình đọc dữ liệu đầu vào và chuyển đổi chúng sang các cấu trúc dữ liệu cần thiết cho thuật toán.

## 4. Thực thi hệ thống với `main.py`
Khởi chạy `main.py` để bắt đầu quá trình mô phỏng hoặc tính toán. 

* **Điều chỉnh tham số:** Để thay đổi số lần duyệt node (node traversal iterations), truy cập vào file `main.py` và cập nhật giá trị tại biến cấu hình tương ứng trong pha 4. Việc tăng hoặc giảm giá trị này sẽ ảnh hưởng trực tiếp đến độ hội tụ và độ chính xác của kết quả đầu ra.