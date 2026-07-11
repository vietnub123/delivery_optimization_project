import copy
from alns import State
import numpy as np

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
        self.PENALTY_UNASSIGNED = 1e6      # Phạt cực nặng nếu không giao được hàng
        self.PENALTY_DELAY_PER_DAY = 5000  # Phạt dời lịch giao (tuyến tính)
        self.PENALTY_TW_VIOLATION = 1e5    # Phạt nếu vi phạm nghiêm trọng giới hạn thời gian
        self.WEIGHT_DISTANCE = 1.0         # Trọng số cho tổng quãng đường
        self.WEIGHT_WAIT_TIME = 0.5        # Trọng số cho tổng thời gian chờ đợi (phút)

    def copy(self):
        """
        Ghi đè phương thức copy. Bắt buộc đối với thuật toán ALNS để lưu trữ các nghiệm lân cận 
        mà không làm biến đổi không gian trạng thái gốc.
        """
        # Sử dụng deepcopy cho routes để tránh tham chiếu bộ nhớ
        return DeliveryState(copy.deepcopy(self.routes), 
                             self.unassigned.copy(), 
                             self.env)

    def objective(self) -> float:
        """
        Hàm định lượng chi phí F(x) của toàn bộ hệ thống.
        F(x) = C_distance + C_wait + C_delay + C_unassigned + C_tw_violation
        """
        total_distance = 0.0
        total_wait_time = 0.0
        total_delay_penalty = 0.0
        tw_violations = 0

        # Mô phỏng quỹ đạo không gian - thời gian cho từng chu kỳ ngày
        for day, route in self.routes.items():
            if not route:
                continue
            
            # Khởi tạo điểm xuất phát tại Kho trung tâm (Node 0) tại thời điểm 00:00
            current_node = 0
            current_time = 0.0
            
            for next_node in route:
                # 1. Tích phân chi phí khoảng cách và thời gian di chuyển
                total_distance += self.env.distance_matrix[current_node][next_node]
                current_time += self.env.travel_time_matrix[current_node][next_node]
                
                # 2. Xử lý Ràng buộc Khung thời gian (Time Windows)
                node_attrs = self.env.get_node_attributes(next_node)
                allowed_tws = node_attrs['allowed_time_windows'].get(day, [])
                
                if not allowed_tws:
                    # Lỗi nghiêm trọng: Khách hàng không nhận hàng vào ngày này
                    tw_violations += 1
                    continue
                
                # Tìm khung thời gian phù hợp nhất (sắp xếp theo start_time)
                # Xử lý trường hợp đa khung thời gian trong cùng 1 ngày
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
                    # Trễ toàn bộ các khung thời gian trong ngày
                    tw_violations += 1
                
                # 3. Tính toán thời gian phục vụ (Service Time)
                current_time += node_attrs['service_time']
                
                # 4. Tính toán hệ số phạt Delay (dời lịch)
                # Giả định: đơn hàng ưu tiên giao vào ngày có time window sớm nhất trong tuần
                earliest_possible_day = min(node_attrs['allowed_time_windows'].keys())
                if day > earliest_possible_day:
                    total_delay_penalty += (day - earliest_possible_day) * self.PENALTY_DELAY_PER_DAY
                
                # Dịch chuyển nút trạng thái
                current_node = next_node
                
            # 5. Phản hồi về Kho trung tâm (Return to Depot)
            total_distance += self.env.distance_matrix[current_node][0]

        # 6. Tích hợp Chi phí Phạt đối với Khách hàng chưa được phục vụ
        unassigned_penalty = len(self.unassigned) * self.PENALTY_UNASSIGNED

        # Phương trình Hội tụ Cost
        F_x = (total_distance * self.WEIGHT_DISTANCE) + \
              (total_wait_time * self.WEIGHT_WAIT_TIME) + \
              total_delay_penalty + \
              (tw_violations * self.PENALTY_TW_VIOLATION) + \
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