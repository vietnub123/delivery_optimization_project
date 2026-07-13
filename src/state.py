import copy
from alns import State
import numpy as np
from tqdm import tqdm

class DeliveryState(State):
    def __init__(self, routes: dict, unassigned: list, env):
        """
        Khởi tạo Không gian Trạng thái.
        :param routes: Dictionary lưu trữ quỹ đạo theo ngày {day_id: [node_1, node_2, ...]}. 
                       Lưu ý: Không bao gồm nút kho (Depot) ở hai đầu mút để tiện thao tác chèn/xóa.
        :param unassigned: Danh sách các ID đơn hàng chưa được phân bổ.
        :param env: Thể hiện của lớp DeliveryEnvironment chứa ma trận không gian và thời gian.
        """
        self.routes = routes
        self.unassigned = unassigned
        self.env = env
        
        # Hệ số phạt (Hyperparameters)
        self.PENALTY_UNASSIGNED = 1e5      # Phạt cực nặng nếu không giao được hàng /đơn
        self.PENALTY_DELAY_PER_DAY = 100  # Phạt dời lịch giao (tuyến tính) /đơn
        self.PENALTY_TW_VIOLATION = 50   # Phạt nếu vi phạm nghiêm trọng giới hạn thời gian /phút
        self.WEIGHT_DISTANCE = 1.0         # Trọng số cho tổng quãng đường /km
        self.WEIGHT_WAIT_TIME = 0.3        # Trọng số cho tổng thời gian chờ đợi (phút)

    def copy(self):
        """
        Ghi đè phương thức copy. Bắt buộc đối với thuật toán ALNS để lưu trữ các nghiệm lân cận 
        mà không làm biến đổi không gian trạng thái gốc.
        
        # Sử dụng deepcopy cho routes để tránh tham chiếu bộ nhớ
        """
        return DeliveryState(copy.deepcopy(self.routes), 
                             self.unassigned.copy(), 
                             self.env)
        
        # Chỉ copy những gì cần thiết: routes và unassigned
        #shallowcopy 
        """
        # Không copy env vì env là tĩnh, không thay đổi
        new_state = DeliveryState(routes=self.routes.copy(), 
                                unassigned=self.unassigned.copy(), 
                                env=self.env)
        return new_state
        """
    def objective(self) -> float:
        """
        Hàm định lượng chi phí F(x) của toàn bộ hệ thống.
        F(x) = C_distance + C_wait + C_delay + C_unassigned + C_tw_violation
        """
        total_distance = 0.0
        total_wait_time = 0.0
        total_delay_penalty = 0.0
        
        # [SỬA ĐỔI] Đổi từ biến đếm số lượng sang biến lưu tổng tiền phạt
        total_tw_penalty_cost = 0.0 

        # Mô phỏng quỹ đạo không gian - thời gian cho từng chu kỳ ngày
        for day, route in self.routes.items():
            if not route:
                continue
            
            # Khởi tạo điểm xuất phát tại Kho trung tâm (Node 0) tại thời điểm 00:00
            current_node = 0
            current_time = 0.0
            
            for next_node in route:
                if next_node is None: continue
                # 1. Tích phân chi phí khoảng cách và thời gian di chuyển
                total_distance += self.env.distance_matrix[current_node][next_node]
                current_time += self.env.travel_time_matrix[current_node][next_node]
                
                # 2. Xử lý Ràng buộc Khung thời gian (Time Windows)
                node_attrs = self.env.get_node_attributes(next_node)
                allowed_tws = node_attrs['allowed_time_windows'].get(day, [])
                
                if not allowed_tws:
                    # [SỬA ĐỔI] Khách không nhận hàng ngày này -> Phạt ngang với rớt đơn (Big M)
                    total_tw_penalty_cost += self.PENALTY_UNASSIGNED
                    continue
                
                # Tìm khung thời gian phù hợp nhất (sắp xếp theo start_time)
                valid_tw_found = False
                for (start_min, end_min) in sorted(allowed_tws):
                    if current_time <= end_min:
                        if current_time < start_min:
                            # Hệ thống đến sớm, bắt buộc phải chờ
                            wait_time = start_min - current_time
                            total_wait_time += wait_time
                            current_time = start_min # Thời điểm bắt đầu phục vụ
                        valid_tw_found = True
                        break # Đã chốt được khung thời gian hợp lệ
                
                if not valid_tw_found:
                    # [SỬA ĐỔI] Xử lý Phạt Lũy tiến (Exponential Penalty) khi đến trễ
                    # Lấy khung thời gian muộn nhất trong ngày làm mốc
                    last_end_min = sorted(allowed_tws)[-1][1]
                    minutes_late = current_time - last_end_min
                    
                    # Trễ 10 phút -> Hệ số x1
                    # Trễ 60 phút -> Hệ số x36
                    # Trễ 120 phút -> Hệ số x144
                    penalty_multiplier = (minutes_late / 10.0) ** 2
                    
                    # Cộng dồn tiền phạt vào tổng
                    total_tw_penalty_cost += self.PENALTY_TW_VIOLATION * penalty_multiplier
                
                # 3. Tính toán thời gian phục vụ (Service Time)
                current_time += node_attrs['service_time']
                
                # 4. Tính toán hệ số phạt Delay (dời lịch)
                earliest_possible_day = min(node_attrs['allowed_time_windows'].keys())
                if day > earliest_possible_day:
                    total_delay_penalty += (day - earliest_possible_day) * self.PENALTY_DELAY_PER_DAY
                
                # Dịch chuyển nút trạng thái
                current_node = next_node
                
            # 5. Phản hồi về Kho trung tâm (Return to Depot)
            total_distance += self.env.distance_matrix[current_node][0]

        # 6. Tích hợp Chi phí Phạt đối với Khách hàng chưa được phục vụ
        unassigned_penalty = len(self.unassigned) * self.PENALTY_UNASSIGNED

        # [SỬA ĐỔI] Phương trình Hội tụ Cost sử dụng tổng tiền phạt đa thức
        F_x = (total_distance * self.WEIGHT_DISTANCE) + \
              (total_wait_time * self.WEIGHT_WAIT_TIME) + \
              total_delay_penalty + \
              total_tw_penalty_cost + \
              unassigned_penalty

        return F_x

    def __hash__(self):
        """Khóa băm xác định trạng thái duy nhất, tối ưu cho bộ nhớ đệm."""
        route_tuple = tuple(tuple(self.routes[day]) for day in sorted(self.routes.keys()))
        return hash((route_tuple, tuple(self.unassigned)))

    def __eq__(self, other):
        """Toán tử so sánh không gian."""
        return isinstance(other, DeliveryState) and \
               self.routes == other.routes and \
               self.unassigned == other.unassigned