import matplotlib.pyplot as plt
from tqdm import tqdm

import matplotlib.cm as cm
import numpy as np
from state import DeliveryState

class Visualizer:
    def __init__(self, env):
        """
        Khởi tạo hệ thống ánh xạ không gian.
        :param env: Thể hiện của DeliveryEnvironment chứa trường vector tọa độ.
        """
        self.env = env
        self.locations = env.locations
        self.depot = self.locations.iloc[0]
        self.customers = self.locations.iloc[1:]

    def plot_routes(self, state: DeliveryState, title: str = "Đồ thị Quỹ đạo Phân bổ Không gian"):
        """
        Biểu diễn vector không gian của các chu trình giao hàng phân rã theo đa chu kỳ.
        :param state: Không gian trạng thái cần trực quan hóa.
        :param title: Tiêu đề hệ quy chiếu.
        """
        plt.figure(figsize=(12, 8))
        
        # Thiết lập các điểm kì dị trong không gian metric 2D
        plt.scatter(self.customers['x_km'], self.customers['y_km'], 
                    c='gray', marker='o', s=30, alpha=0.6, label='Tập Khách hàng (V)')
        plt.scatter(self.depot['x_km'], self.depot['y_km'], 
                    c='red', marker='s', s=120, edgecolors='black', label='Kho trung tâm (Gốc tọa độ)')
        
        # Khởi tạo hàm phân phối dải màu sắc quang phổ cho 7 chu kỳ không gian - thời gian
        colors = cm.rainbow(np.linspace(0, 1, 7))

        for day, route in state.routes.items():
            day_idx = int(day)
            if not route:
                tqdm.write(f"Thông báo: Chu kỳ k={day_idx} trống (Không có đơn hàng phân bổ).")
                continue

            color = colors[day_idx - 1]

            # Khởi tạo ma trận tọa độ hạt nhân từ Kho trung tâm
            x_coords = [self.depot['x_km']]
            y_coords = [self.depot['y_km']]
            
            # Tích hợp vector di chuyển tuần tự
            for node in route:
                node = f"C{node:03d}"
                tqdm.write(f"Đang xử lý node ID: {node} | Kiểu dữ liệu: {type(node)}") # <-- Dòng này cực quan trọng
                                
                subset = self.locations[self.locations['location_id'] == node]
                
                # Kiểm tra xem nó có tìm thấy gì không
                if subset.empty:
                    tqdm.write(f"LỖI: Node {node} không tồn tại trong danh sách location_id")
                    continue
                
                
                node_data = self.locations[self.locations['location_id'] == node].iloc[0]
                x_coords.append(node_data['x_km'])
                y_coords.append(node_data['y_km'])
                
            # Đóng quỹ đạo bằng phép phản hồi về gốc tọa độ
            x_coords.append(self.depot['x_km'])
            y_coords.append(self.depot['y_km'])
            
            # Thiết lập phương trình đường thẳng nối các điểm nút
            plt.plot(x_coords, y_coords, color=color, linewidth=1, 
                     marker='.', markersize=8, alpha=0.8, label=f'Chu kỳ $k={day_idx}$')
            
            # Tính toán đạo hàm định hướng để vẽ vector hướng (arrow)
            for i in range(len(x_coords) - 1):
                plt.annotate('', 
                             xy=(x_coords[i+1], y_coords[i+1]), 
                             xytext=(x_coords[i], y_coords[i]),
                             arrowprops=dict(arrowstyle="-|>", color=color, lw=1.2, alpha=0.8, 
                                             mutation_scale=15))

        # Biểu diễn các nút ngoại lai (chưa được phân bổ) vào không gian nghiệm
        if state.unassigned:
            unassigned_x = []
            unassigned_y = []
            for node in state.unassigned:
                node_data = self.locations[self.locations['location_id'] == node].iloc[0]
                unassigned_x.append(node_data['x_km'])
                unassigned_y.append(node_data['y_km'])
            plt.scatter(unassigned_x, unassigned_y, c='black', marker='x', s=60, 
                        label=r'Tập chưa phân bổ ($\mathbf{U}$)')

        # Thiết lập các ràng buộc hiển thị của hệ tọa độ Descartes
        plt.title(title, fontsize=14, fontweight='bold')
        plt.xlabel(r"Trục hoành $X$ (km)", fontsize=12)
        plt.ylabel(r"Trục tung $Y$ (km)", fontsize=12)
        
        # Định vị bảng chú giải bên ngoài miền không gian chính để tối ưu tầm nhìn
        plt.legend(loc='upper right', bbox_to_anchor=(1.25, 1), borderaxespad=0.)
        plt.grid(True, linestyle='--', alpha=0.5)
        
        # Khử răng cưa và điều chỉnh lề
        plt.tight_layout()
        plt.show()