import copy
import math
from alns import State

class DeliveryState(State):
    """
    Ma trận biểu diễn không gian trạng thái của bài toán Định tuyến phụ thuộc Thời gian (TD-VRP).
    Tích hợp hàm phạt giới hạn biên (Overtime) và hàm phạt thời gian cấp số mũ (Exponential Penalty).
    """
    def __init__(self, routes: dict, unassigned: list, env):
        self.routes = routes
        self.unassigned = unassigned
        self.env = env
        
        # Hệ số phạt (Hyperparameters) thiết lập cho các cấu trúc rào cản
        self.PENALTY_UNASSIGNED = 1e6
        self.PENALTY_DELAY_PER_DAY = 2000    #giao trễ trong ngày luôn tốt hơn chuyển sang ngày khác
        self.PENALTY_TW_VIOLATION = 10       # Hệ số C cho hàm mũ
        self.ALPHA_TW = 0.05                 # Trọng số gia tốc phi tuyến (alpha)
        self.PENALTY_OVERTIME = 500.0        # Hệ số phạt vượt mốc giới hạn 24h
        
        # Trọng số tối ưu hóa cơ sở
        self.WEIGHT_DISTANCE = 1.0
        self.WEIGHT_WAIT_TIME = 0.3

    def copy(self):
        """Khởi tạo trạng thái lân cận, bảo toàn định dạng tham chiếu không gian bộ nhớ."""
        return DeliveryState(copy.deepcopy(self.routes), 
                             self.unassigned.copy(), 
                             self.env)

    def calculate_dynamic_travel_time(self, distance_km: float, departure_time_min: float) -> float:
        """
        Nội suy thời gian di chuyển phi tuyến thông qua tích phân từng phần.
        Bảo toàn tiên đề FIFO trên các chu kỳ vận tốc giao thông.
        """
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
            current_speed = None
            end_of_interval = None
            
            for (start, end, speed) in speed_profile:
                if start <= day_time < end:
                    current_speed = speed
                    end_of_interval = end
                    break
                    
            if current_speed is None:
                current_speed = speed_profile[0][2]
                end_of_interval = 1440 + speed_profile[0][1]
                
            time_left_in_interval = end_of_interval - day_time
            max_distance_in_interval = time_left_in_interval * current_speed
            
            if remaining_distance <= max_distance_in_interval:
                time_spent = remaining_distance / current_speed
                travel_time += time_spent
                remaining_distance = 0
            else:
                travel_time += time_left_in_interval
                remaining_distance -= max_distance_in_interval
                current_time += time_left_in_interval
                
        return travel_time

    def objective(self) -> float:
        """
        Hàm định lượng chi phí toàn cục. Đã khắc phục điều kiện biên hồi quy (Return Boundary)
        và tích hợp mô hình đánh giá phạt cấp số mũ.
        """
        total_distance = 0.0
        total_wait_time = 0.0
        total_delay_penalty = 0.0
        total_tw_penalty_cost = 0.0 
        total_overtime_penalty = 0.0

        for day, route in self.routes.items():
            if not route:
                continue
            
            current_node = 0
            current_time = 0.0
            
            for next_node in route:
                if next_node is None: continue
                
                segment_distance = self.env.distance_matrix[current_node][next_node]
                total_distance += segment_distance
                
                current_time += self.calculate_dynamic_travel_time(segment_distance, current_time)
                
                node_attrs = self.env.get_node_attributes(next_node)
                allowed_tws = node_attrs['allowed_time_windows'].get(day, [])
                
                if not allowed_tws:
                    total_tw_penalty_cost += self.PENALTY_UNASSIGNED
                    continue
                
                valid_tw_found = False
                for (start_min, end_min) in sorted(allowed_tws):
                    if current_time <= end_min:
                        if current_time < start_min:
                            wait_time = start_min - current_time
                            total_wait_time += wait_time
                            current_time = start_min 
                        valid_tw_found = True
                        break 
                
                if not valid_tw_found:
                    # Phương trình phạt cấp số mũ (Exponential Penalty)
                    last_end_min = sorted(allowed_tws)[-1][1]
                    minutes_late = current_time - last_end_min
                    
                    try:
                        # P_late = C * (e^(alpha * delta_t) - 1)
                        penalty_multiplier = math.exp(self.ALPHA_TW * minutes_late) - 1.0
                    except OverflowError:
                        # Đảm bảo tính ổn định số học, chặn giá trị tại ngưỡng vô cực giả (Big M)
                        penalty_multiplier = 1e6 
                        
                    total_tw_penalty_cost += self.PENALTY_TW_VIOLATION * penalty_multiplier
                
                current_time += node_attrs['service_time']
                
                earliest_possible_day = min(node_attrs['allowed_time_windows'].keys())
                if day > earliest_possible_day:
                    total_delay_penalty += (day - earliest_possible_day) * self.PENALTY_DELAY_PER_DAY
                
                current_node = next_node
                
            # Xử lý điều kiện biên: Hồi quy về Kho trung tâm (Return to Depot)
            return_distance = self.env.distance_matrix[current_node][0]
            total_distance += return_distance
            
            # Tích phân thời gian hồi quy (Khắc phục lỗ hổng biến mất thời gian)
            current_time += self.calculate_dynamic_travel_time(return_distance, current_time)
            
            # Kiểm soát giới hạn chu kỳ 24h (1440 phút) bằng hàm kích hoạt ReLU
            if current_time > 1440.0:
                overtime = current_time - 1440.0
                total_overtime_penalty += overtime * self.PENALTY_OVERTIME

        unassigned_penalty = len(self.unassigned) * self.PENALTY_UNASSIGNED

        F_x = (total_distance * self.WEIGHT_DISTANCE) + \
              (total_wait_time * self.WEIGHT_WAIT_TIME) + \
              total_delay_penalty + \
              total_tw_penalty_cost + \
              total_overtime_penalty + \
              unassigned_penalty

        return F_x

    def __hash__(self):
        route_tuple = tuple(tuple(self.routes[day]) for day in sorted(self.routes.keys()))
        return hash((route_tuple, tuple(self.unassigned)))

    def __eq__(self, other):
        return isinstance(other, DeliveryState) and \
               self.routes == other.routes and \
               self.unassigned == other.unassigned