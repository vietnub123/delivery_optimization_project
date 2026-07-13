import json
import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Thiết lập thông số thẩm mỹ cho biểu đồ khoa học
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12

class RoutingAnalyzer:
    def __init__(self, locations_path, time_windows_path):
        """Khởi tạo môi trường mô phỏng tĩnh để giải mã các vector quỹ đạo."""
        self.locations = pd.read_csv(locations_path)
        self.time_windows = pd.read_csv(time_windows_path)
        
        # Tiền xử lý tọa độ
        self.loc_dict = self.locations.set_index('location_id').to_dict('index')
        
        def _parse_time(t_str):
            """Hàm vô hướng hóa chuỗi thời gian (HH:MM -> Phút)."""
            h, m = map(int, str(t_str).strip().split(':'))
            return h * 60 + m

        # Tiền xử lý Time Windows
        self.tw_dict = {}
        for _, row in self.time_windows.iterrows():
            loc_id = str(row['location_id'])
            day = int(row['day_of_week'])
            
            if loc_id not in self.tw_dict:
                self.tw_dict[loc_id] = {}
            if day not in self.tw_dict[loc_id]:
                self.tw_dict[loc_id][day] = []
                
            start_min = _parse_time(row['start_time'])
            end_min = _parse_time(row['end_time'])
            self.tw_dict[loc_id][day].append((start_min, end_min))
            
        # Tổng số lượng đỉnh nhu cầu (Ngoại trừ Depot thông qua ràng buộc demand_kg > 0)
        self.total_demand_nodes = len(self.locations[self.locations['demand_kg'] > 0])
        
        # Tự động nội suy mã định danh của Depot (Đỉnh có vector tải trọng bằng 0)
        depot_row = self.locations[self.locations['demand_kg'] == 0]
        self.depot_id = str(depot_row.iloc[0]['location_id']) if not depot_row.empty else 'DEPOT'

    def _resolve_node_id(self, node):
        """
        Hàm phân giải định danh (Identity Resolution).
        Ánh xạ các chỉ số nguyên tuyến tính (integer index) hoặc chuỗi bị mất tiền tố về định danh tuyệt đối.
        """
        node_str = str(node)
        
        # Trường hợp 1: Định danh đã khớp tuyệt đối
        if node_str in self.loc_dict:
            return node_str
            
        # Trường hợp 2: Định danh là chỉ số dòng (Row Index) trong không gian ma trận
        try:
            idx = int(node)
            if 0 <= idx < len(self.locations):
                loc_id = str(self.locations.iloc[idx]['location_id'])
                if loc_id in self.loc_dict:
                    return loc_id
        except ValueError:
            pass
            
        # Trường hợp 3: Định danh bị lược bỏ tiền tố (e.g., '56' -> 'C056' hoặc 'C56')
        if node_str.isdigit():
            padded_id = f"C{int(node_str):03d}"
            if padded_id in self.loc_dict:
                return padded_id
            prefixed_id = f"C{node_str}"
            if prefixed_id in self.loc_dict:
                return prefixed_id
                
        raise KeyError(f"Lỗi ánh xạ: Không thể phân giải đỉnh không gian '{node}' vào hệ tọa độ.")

    def _euclidean_distance(self, loc1, loc2):
        """Khoảng cách L2 (Euclidean Norm) sử dụng tọa độ mét metric (km)."""
        x1, y1 = self.loc_dict[loc1]['x_km'], self.loc_dict[loc1]['y_km']
        x2, y2 = self.loc_dict[loc2]['x_km'], self.loc_dict[loc2]['y_km']
        return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

    def _calculate_dynamic_travel_time(self, distance_km: float, departure_time_min: float) -> float:
        """Tích phân phi tuyến thời gian di chuyển (Mô hình TD-VRP)."""
        speed_profile = [
            (0, 360, 50.0 / 60),
            (360, 960, 40.0 / 60),
            (960, 1140, 30.0 / 60),
            (1140, 1440, 50.0 / 60)
        ]
        
        remaining_distance = distance_km
        current_time = departure_time_min
        travel_time = 0.0
        
        while remaining_distance > 0:
            day_time = current_time % 1440 
            current_speed, end_of_interval = None, None
            
            for (start, end, speed) in speed_profile:
                if start <= day_time < end:
                    current_speed, end_of_interval = speed, end
                    break
                    
            if current_speed is None:
                current_speed, end_of_interval = speed_profile[0][2], 1440 + speed_profile[0][1]
                
            time_left_in_interval = end_of_interval - day_time
            max_distance_in_interval = time_left_in_interval * current_speed
            
            if remaining_distance <= max_distance_in_interval:
                travel_time += remaining_distance / current_speed
                remaining_distance = 0
            else:
                travel_time += time_left_in_interval
                remaining_distance -= max_distance_in_interval
                current_time += time_left_in_interval
                
        return travel_time

    def evaluate_solution(self, solution_data: dict, algo_name: str) -> dict:
        """Giải mã Không gian Trạng thái, lượng hóa các thông số vận hành động học."""
        routes = solution_data.get('routes', {})
        unassigned = solution_data.get('unassigned', [])
        
        metrics = {
            'Algorithm': algo_name,
            'Total_Cost': solution_data.get('objective_cost', 0.0),
            'Total_Distance_km': 0.0,
            'Total_Wait_Time_min': 0.0,
            'TW_Violations': 0,
            'Delayed_Orders': 0,
            'Sum_Delay_Days': 0,
            'Unassigned_Orders': len(unassigned),
            'Overtime_Violations': 0
        }
        
        # Theo dõi sự phân bổ quỹ đạo theo từng chu kỳ (Workload Balance)
        daily_workload = {day: {'nodes_served': 0, 'distance': 0.0} for day in range(1, 8)}

        for day_str, route in routes.items():
            day = int(day_str)
            if not route: continue
            
            current_node = self.depot_id
            current_time = 0.0
            
            for next_node in route:
                # Phân giải định danh tuyệt đối
                next_node_resolved = self._resolve_node_id(next_node)
                
                # Tích phân không gian & thời gian
                dist = self._euclidean_distance(current_node, next_node_resolved)
                metrics['Total_Distance_km'] += dist
                daily_workload[day]['distance'] += dist
                current_time += self._calculate_dynamic_travel_time(dist, current_time)
                
                # Xử lý thời gian và vi phạm
                allowed_tws = self.tw_dict.get(next_node_resolved, {}).get(day, [])
                if allowed_tws:
                    valid_tw_found = False
                    for (start_min, end_min) in sorted(allowed_tws):
                        if current_time <= end_min:
                            if current_time < start_min:
                                metrics['Total_Wait_Time_min'] += (start_min - current_time)
                                current_time = start_min
                            valid_tw_found = True
                            break
                    if not valid_tw_found:
                        metrics['TW_Violations'] += 1
                
                # Xử lý dời lịch (Delay Vector)
                all_allowed_days = list(self.tw_dict.get(next_node_resolved, {}).keys())
                if all_allowed_days:
                    earliest_day = min(all_allowed_days)
                    if day > earliest_day:
                        metrics['Delayed_Orders'] += 1
                        metrics['Sum_Delay_Days'] += (day - earliest_day)
                
                # Cập nhật trạng thái
                service_time = self.loc_dict[next_node_resolved].get('service_time', 10)
                current_time += service_time
                current_node = next_node_resolved
                daily_workload[day]['nodes_served'] += 1
            
            # Hồi quy về Depot
            return_dist = self._euclidean_distance(current_node, self.depot_id)
            metrics['Total_Distance_km'] += return_dist
            daily_workload[day]['distance'] += return_dist
            current_time += self._calculate_dynamic_travel_time(return_dist, current_time)
            
            if current_time > 1440.0:
                metrics['Overtime_Violations'] += 1

        # Xử lý các phép chia thống kê
        served_nodes = self.total_demand_nodes - metrics['Unassigned_Orders']
        metrics['Success_Rate_%'] = (served_nodes / self.total_demand_nodes * 100) if self.total_demand_nodes else 0
        metrics['Avg_Delay_Days'] = (metrics['Sum_Delay_Days'] / served_nodes) if served_nodes > 0 else 0
        
        # Loại bỏ các biến trung gian
        del metrics['Sum_Delay_Days']

        return metrics, daily_workload

def load_json_safe(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Cảnh báo: Không tìm thấy phân phối dữ liệu tại {filepath}")
        return None

def main():
    print("[*] Khởi tạo Hệ thống Phân tích Đối chứng (Benchmarking Engine)...")
    
    # --- ĐƯỜNG DẪN DỮ LIỆU TÙY CHỈNH (Điều chỉnh nếu cần) ---
    DATA_DIR = Path('./tests/test4')
    LOCATIONS_FILE = DATA_DIR / 'locations.csv'
    TIME_WINDOWS_FILE = DATA_DIR / 'time_windows.csv'
    
    analyzer = RoutingAnalyzer(LOCATIONS_FILE, TIME_WINDOWS_FILE)
    
    solutions = {
        'ALNS': load_json_safe(DATA_DIR / 'solution_alns.json'),
        'NN': load_json_safe(DATA_DIR / 'solution_nn.json'),
        'EDD': load_json_safe(DATA_DIR / 'solution_edd.json')
    }
    
    results = []
    workloads = {}
    history_alns = []

    # Tiến hành giải mã và đánh giá vi phân
    for algo, data in solutions.items():
        if data:
            metrics, workload = analyzer.evaluate_solution(data, algo)
            results.append(metrics)
            workloads[algo] = workload
            if algo == 'ALNS' and 'history' in data:
                history_alns = data['history']

    df_results = pd.DataFrame(results)
    
    print("\n--- MA TRẬN KẾT QUẢ ĐỐI CHỨNG VẬN HÀNH ---")
    columns_to_print = ['Algorithm', 'Total_Cost', 'Success_Rate_%', 'Total_Distance_km', 
                        'TW_Violations', 'Delayed_Orders', 'Unassigned_Orders']
    print(df_results[columns_to_print].to_string(index=False))

    # ==========================================
    # PHÂN HỆ TRỰC QUAN HÓA (VISUALIZATION)
    # ==========================================
    
    # 1. Đồ thị Hội tụ Động lực học của ALNS
    if history_alns:
        plt.figure(figsize=(10, 5))
        plt.plot(history_alns, color='blue', linewidth=1.5, alpha=0.8)
        plt.title('Động lực học Hội tụ (Convergence Dynamics) - Thuật toán ALNS', fontweight='bold')
        plt.xlabel('Vòng lặp (Iterations)')
        plt.ylabel('Giá trị Hàm Mục Tiêu F(x)')
        plt.yscale('log') # Áp dụng thang logarit do F(x) biến thiên phi tuyến mạnh
        plt.tight_layout()
        plt.savefig('convergence_alns.png', dpi=300)
        plt.close()
        print("[+] Đã kết xuất đồ thị: convergence_alns.png")

    # 2. Phân bố Vi phân Chu kỳ (Workload Balancing - Nodes Served per Day)
    if workloads:
        df_workload = pd.DataFrame({
            algo: {day: data['nodes_served'] for day, data in w_data.items()}
            for algo, w_data in workloads.items()
        }).fillna(0)
        
        plt.figure(figsize=(12, 6))
        df_workload.plot(kind='bar', colormap='viridis', width=0.7, ax=plt.gca())
        plt.title('Phương sai Phân bổ Khối lượng Công việc theo Chu kỳ (Workload Balancing)', fontweight='bold')
        plt.xlabel('Chu kỳ Vận hành (Day)')
        plt.ylabel('Tần suất Nhu cầu (Nodes Served)')
        plt.xticks(rotation=0)
        plt.legend(title='Cơ sở Thuật toán')
        plt.tight_layout()
        plt.savefig('workload_balancing.png', dpi=300)
        plt.close()
        print("[+] Đã kết xuất đồ thị: workload_balancing.png")

    # 3. Phân tích Vĩ mô Đối sánh (Macro Metrics Comparison)
    if not df_results.empty:
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Ma trận Đối sánh Đa chiều (Multi-dimensional Benchmarking)', fontweight='bold', fontsize=16)
        
        # Cấu hình biểu đồ
        metrics_to_plot = [
            ('Total_Distance_km', 'Tổng Quãng đường (km)', axes[0, 0]),
            ('Total_Wait_Time_min', 'Tổng Thời gian Chờ (phút)', axes[0, 1]),
            ('TW_Violations', 'Tần suất Vi phạm Khung giờ (Lần)', axes[1, 0]),
            ('Unassigned_Orders', 'Tập hợp Khách hàng bị Bỏ rơi (Đơn)', axes[1, 1])
        ]
        
        for col, title, ax in metrics_to_plot:
            sns.barplot(data=df_results, x='Algorithm', y=col, ax=ax, hue='Algorithm', palette='muted', legend=False)
            ax.set_title(title, fontweight='bold')
            ax.set_ylabel('')
            ax.set_xlabel('')
            
        plt.tight_layout()
        plt.savefig('macro_benchmarking.png', dpi=300)
        plt.close()
        print("[+] Đã kết xuất đồ thị: macro_benchmarking.png")

    # ==========================================
    # 4. Trực quan hóa Quỹ đạo Không gian (Spatial Routing Topologies)
    # Tái cấu trúc thành 3 tệp tin đồ họa độc lập
    # ==========================================
    print("[*] Đang nội suy ma trận tọa độ và kết xuất đồ thị hình học riêng biệt...")

    # Trích xuất tọa độ chuẩn của Điểm gốc (Depot)
    depot_x = analyzer.loc_dict[analyzer.depot_id]['x_km']
    depot_y = analyzer.loc_dict[analyzer.depot_id]['y_km']

    algorithms = ['NN', 'EDD', 'ALNS']

    
    gamma = 1
    colors = [(r * gamma, g * gamma, b * gamma, a) for r, g, b, a in plt.cm.rainbow(np.linspace(0, 1, 7))]


    for algo in algorithms:
        data = solutions.get(algo)
        if not data or 'routes' not in data:
            continue
            
        fig_spatial, ax = plt.subplots(figsize=(10, 8))
        ax.set_title(f'Ánh xạ Cấu trúc Hình học Quỹ đạo - Mô hình: {algo}', fontweight='bold', fontsize=15)
        
        # Khởi tạo vector đồ thị cho Kho trung tâm
        ax.scatter(depot_x, depot_y, c='red', marker='s', s=150, edgecolor='black', label='DEPOT', zorder=5)
        
        routes = data['routes']
        for day_str, route in routes.items():
            day = int(day_str)
            if not route: continue
            
            # Khởi tạo vector không gian với điểm đầu mút là Depot
            x_coords = [depot_x]
            y_coords = [depot_y]
            
            for node in route:
                resolved_node = analyzer._resolve_node_id(node)
                x_coords.append(analyzer.loc_dict[resolved_node]['x_km'])
                y_coords.append(analyzer.loc_dict[resolved_node]['y_km'])
                
            # Hồi quy vector về Depot
            x_coords.append(depot_x)
            y_coords.append(depot_y)
            
            color = colors[(day - 1) % len(colors)]
            
            # Ánh xạ đường đi (Edges) và đỉnh (Vertices)
            ax.plot(x_coords, y_coords, color=color, linewidth=1.5, alpha=0.7, label=f'Chu kỳ {day}')
            ax.scatter(x_coords[1:-1], y_coords[1:-1], color=color, s=30, zorder=3)
        
        ax.set_xlabel('Hệ tọa độ X (km)')
        ax.set_ylabel('Hệ tọa độ Y (km)')
        ax.grid(True, linestyle='--', alpha=0.5)

        # Thuật toán chuẩn hóa khung chú giải (Legend Deduplication)
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        # Đặt legend ở không gian ngoại vi bên phải nhằm bảo toàn tầm nhìn không gian
        ax.legend(by_label.values(), by_label.keys(), loc='upper left', bbox_to_anchor=(1.02, 1), borderaxespad=0.)

        # Tối ưu hóa viền lề bảo toàn tỷ lệ co (Aspect Ratio)
        plt.tight_layout()
        filename = f'spatial_trajectory_{algo}.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"[+] Đã kết xuất đồ thị vi phân không gian: {filename}")

if __name__ == '__main__':
    main()