import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
import sys

def plot_routes_from_files(locations_file: str, 
                           solution_file: str, 
                           title: str = "Đồ thị Quỹ đạo Tối ưu - Đọc từ Tệp tĩnh"):
    """
    Biểu diễn vector không gian dựa trên dữ liệu tĩnh tĩnh (CSV và JSON).
    """
    # 1. Khởi tạo không gian dữ liệu
    try:
        locations = pd.read_csv(locations_file)
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy tệp không gian tọa độ '{locations_file}'")
        sys.exit(1)

    # Trích xuất vector tọa độ
    depot = locations.iloc[0]
    customers = locations.iloc[1:]

    # 2. Giải mã ma trận cấu trúc dữ liệu JSON
    try:
        with open(solution_file, 'r', encoding='utf-8') as f:
            solution_data = json.load(f)
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy tệp ma trận định tuyến '{solution_file}'")
        sys.exit(1)

    # Giả định JSON có cấu trúc dict: {"routes": {"1": ["C001", "C002"], ...}}
    # Hoặc trực tiếp là {"1": ["C001", "C002"], ...}
    routes = solution_data.get("routes", solution_data)

    # 3. Tính toán tập hợp đỉnh không được phân bổ bằng toán tử tập hợp
    all_customers = set(customers['location_id'].astype(str).tolist())
    assigned_customers = set()
    for route in routes.values():
        # Xử lý định dạng ID (Thêm tiền tố C và đệm 0 nếu đầu vào là số nguyên)
        for node in route:
            node_str = f"C{int(node):03d}" if str(node).isdigit() else str(node)
            assigned_customers.add(node_str)
            
    unassigned = list(all_customers - assigned_customers)

    # 4. Trực quan hóa Không gian Hình học
    plt.figure(figsize=(12, 8))
    
    # Thiết lập các điểm kì dị trong không gian metric 2D
    plt.scatter(customers['x_km'], customers['y_km'], 
                c='gray', marker='o', s=30, alpha=0.6, label='Tập Khách hàng (V)')
    plt.scatter(depot['x_km'], depot['y_km'], 
                c='red', marker='s', s=120, edgecolors='black', label='Kho trung tâm (Gốc tọa độ)')
    
    # Khởi tạo hàm phân phối dải màu sắc quang phổ
    colors = cm.rainbow(np.linspace(0, 1, max(7, len(routes))))

    for day, route_nodes in routes.items():
        day_idx = int(day)
        if not route_nodes:
            print(f"Thông báo: Chu kỳ k={day_idx} trống (Không có đơn hàng phân bổ).")
            continue

        color = colors[day_idx - 1]

        # Khởi tạo ma trận tọa độ hạt nhân từ Kho trung tâm
        x_coords = [depot['x_km']]
        y_coords = [depot['y_km']]
        
        # Tích hợp vector di chuyển tuần tự
        for node in route_nodes:
            node_id = f"C{int(node):03d}" if str(node).isdigit() else str(node)
            subset = locations[locations['location_id'] == node_id]
            
            if subset.empty:
                print(f"LỖI CỤC BỘ: Node {node_id} không tồn tại trong vector không gian.")
                continue
                
            node_data = subset.iloc[0]
            x_coords.append(node_data['x_km'])
            y_coords.append(node_data['y_km'])
            
        # Đóng quỹ đạo bằng phép phản hồi về gốc tọa độ
        x_coords.append(depot['x_km'])
        y_coords.append(depot['y_km'])
        
        # Thiết lập phương trình đường thẳng nối các điểm nút
        plt.plot(x_coords, y_coords, color=color, linewidth=1.5, 
                 marker='.', markersize=8, alpha=0.8, label=f'Chu kỳ $k={day_idx}$')
        
        # Tính toán đạo hàm định hướng để vẽ vector hướng
        for i in range(len(x_coords) - 1):
            plt.annotate('', 
                         xy=(x_coords[i+1], y_coords[i+1]), 
                         xytext=(x_coords[i], y_coords[i]),
                         arrowprops=dict(arrowstyle="-|>", color=color, lw=1.2, alpha=0.8, 
                                         mutation_scale=15))

    # Biểu diễn các nút ngoại lai (chưa được phân bổ) vào không gian nghiệm
    if unassigned:
        unassigned_x = []
        unassigned_y = []
        for node_id in unassigned:
            subset = locations[locations['location_id'] == node_id]
            if not subset.empty:
                node_data = subset.iloc[0]
                unassigned_x.append(node_data['x_km'])
                unassigned_y.append(node_data['y_km'])
                
        if unassigned_x:
            plt.scatter(unassigned_x, unassigned_y, c='black', marker='x', s=60, 
                        label=r'Tập chưa phân bổ ($\mathbf{U}$)')

    # Thiết lập các ràng buộc hiển thị của hệ tọa độ Descartes
    plt.title(title, fontsize=14, fontweight='bold')
    plt.xlabel(r"Trục hoành $X$ (km)", fontsize=12)
    plt.ylabel(r"Trục tung $Y$ (km)", fontsize=12)
    
    plt.legend(loc='upper right', bbox_to_anchor=(1.25, 1), borderaxespad=0.)
    plt.grid(True, linestyle='--', alpha=0.5)
    
    # Khử răng cưa và xuất đồ thị
    plt.tight_layout()
    plt.show()

# --- KHỐI THỰC THI CHÍNH ---
if __name__ == "__main__":
    # Cấu hình đường dẫn tuyệt đối hoặc tương đối tới các tệp dữ liệu
    LOCATIONS_PATH = "locations.csv"
    SOLUTION_PATH = "solution_edd.json"
    
    plot_routes_from_files(
        locations_file=LOCATIONS_PATH,
        solution_file=SOLUTION_PATH,
        title="Đồ thị Quỹ đạo Tối ưu - Mạng lưới Đa chu kỳ (Offline)"
    )