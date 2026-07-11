import numpy as np
from state import DeliveryState

class BaselineHeuristics:
    def __init__(self, env):
        """
        Khởi tạo hệ thống thuật toán cơ sở.
        :param env: Đối tượng DeliveryEnvironment chứa không gian metric.
        """
        self.env = env
        # Khách hàng bắt đầu từ chỉ số 1 (0 là Kho trung tâm)
        self.customers = list(range(1, len(env.locations)))

    def _generate_empty_state(self) -> DeliveryState:
        """Tạo không gian trạng thái rỗng ban đầu."""
        routes = {day: [] for day in range(1, 8)}
        return DeliveryState(routes=routes, unassigned=self.customers.copy(), env=self.env)

    def nearest_neighbor(self) -> DeliveryState:
        """
        Chiến lược Tham lam Khoảng cách (Nearest Neighbor).
        Phân bổ quỹ đạo dựa trên việc cực tiểu hóa khoảng cách Euclid D_{ij}.
        """
        state = self._generate_empty_state()
        unassigned = set(state.unassigned)
        
        for day in range(1, 8):
            current_node = 0
            current_time = 0.0
            
            while unassigned:
                best_node = None
                min_dist = float('inf')
                best_wait = 0.0
                
                # Quét không gian để tìm lân cận gần nhất thỏa mãn ràng buộc thời gian
                for node in unassigned:
                    dist = self.env.distance_matrix[current_node][node]
                    travel_time = self.env.travel_time_matrix[current_node][node]
                    arrival_time = current_time + travel_time
                    
                    node_attrs = self.env.get_node_attributes(node)
                    allowed_tws = node_attrs['allowed_time_windows'].get(day, [])
                    
                    if not allowed_tws:
                        continue
                        
                    # Xác thực tính khả thi của hàm trạng thái thời gian (đỉnh j)
                    valid = False
                    wait_time = 0.0
                    for (start_min, end_min) in sorted(allowed_tws):
                        if arrival_time <= end_min:
                            valid = True
                            wait_time = max(0.0, start_min - arrival_time)
                            break
                            
                    if valid and dist < min_dist:
                        min_dist = dist
                        best_node = node
                        best_wait = wait_time
                        
                if best_node is None:
                    break  # Không tồn tại nút khả thi, chuyển chu kỳ ngày
                    
                # Cập nhật không gian trạng thái
                state.routes[day].append(best_node)
                state.unassigned.remove(best_node)
                unassigned.remove(best_node)
                
                # Tiến vi phân thời gian: t = t + T_{ij} + Wait_{j} + S_{j}
                node_attrs = self.env.get_node_attributes(best_node)
                current_time += self.env.travel_time_matrix[current_node][best_node] + \
                                best_wait + node_attrs['service_time']
                current_node = best_node
                
        return state

    def earliest_due_date(self) -> DeliveryState:
        """
        Chiến lược Tham lam Thời gian (Earliest Due Date).
        Phân bổ dựa trên điểm kỳ dị cận trên (l_i) của khung thời gian.
        """
        state = self._generate_empty_state()
        
        # Thiết lập vector lưu trữ cận trên l_i cực tiểu của mỗi nút
        node_deadlines = []
        for node in state.unassigned:
            attrs = self.env.get_node_attributes(node)
            min_end_time = float('inf')
            
            for day, tws in attrs['allowed_time_windows'].items():
                for (start, end) in tws:
                    if end < min_end_time:
                        min_end_time = end
            node_deadlines.append((node, min_end_time))
            
        # Sắp xếp không gian nút ưu tiên theo l_i tăng dần
        node_deadlines.sort(key=lambda x: x[1])
        sorted_nodes = [x[0] for x in node_deadlines]
        
        # Chèn định tuyến tuần tự
        for node in sorted_nodes:
            attrs = self.env.get_node_attributes(node)
            
            for day in sorted(attrs['allowed_time_windows'].keys()):
                # Tiến hành gán chuỗi đồ thị tại tọa độ cuối của nhánh ngày tương ứng
                state.routes[day].append(node)
                state.unassigned.remove(node)
                break
                
        return state