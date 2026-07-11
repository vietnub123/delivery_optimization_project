import pandas as pd
import numpy as np
from state import DeliveryState

class Evaluator:
    def __init__(self, env):
        """
        Khởi tạo bộ định lượng thống kê.
        :param env: Thể hiện của DeliveryEnvironment chứa dữ liệu không gian - thời gian.
        """
        self.env = env
        self.total_orders = len(env.locations) - 1  # Loại trừ Kho trung tâm (Depot)

    def evaluate_state(self, state: DeliveryState, method_name: str) -> dict:
        """
        Trích xuất và định lượng các tham số mục tiêu từ một không gian trạng thái.
        """
        total_distance = 0.0
        total_wait_time = 0.0
        delayed_orders = 0
        total_delay_days = 0
        tw_violations = 0

        for day, route in state.routes.items():
            if not route:
                continue
                
            current_node = 0
            current_time = 0.0
            
            for next_node in route:
                # 1. Tích phân vector khoảng cách và thời gian
                total_distance += self.env.distance_matrix[current_node][next_node]
                current_time += self.env.travel_time_matrix[current_node][next_node]
                
                # 2. Xử lý hàm trạng thái thời gian
                node_attrs = self.env.get_node_attributes(next_node)
                allowed_tws = node_attrs['allowed_time_windows'].get(day, [])
                
                valid_tw_found = False
                if allowed_tws:
                    for (start_min, end_min) in sorted(allowed_tws):
                        if current_time <= end_min:
                            if current_time < start_min:
                                wait_time = start_min - current_time
                                total_wait_time += wait_time
                                current_time = start_min
                            valid_tw_found = True
                            break
                            
                if not valid_tw_found:
                    tw_violations += 1
                
                # 3. Tính thời gian phục vụ
                current_time += node_attrs['service_time']
                
                # 4. Định lượng độ trễ chu kỳ
                earliest_possible_day = min(node_attrs['allowed_time_windows'].keys())
                if day > earliest_possible_day:
                    delayed_orders += 1
                    total_delay_days += (day - earliest_possible_day)
                    
                current_node = next_node
                
            # Phản hồi về depot
            total_distance += self.env.distance_matrix[current_node][0]

        # 5. Các chỉ số vĩ mô
        unassigned_count = len(state.unassigned)
        success_rate = ((self.total_orders - unassigned_count) / self.total_orders) * 100

        return {
            "Method": method_name,
            "Objective_Cost (F)": round(state.objective(), 2),
            "Success_Rate (%)": round(success_rate, 2),
            "Total_Distance (km)": round(total_distance, 2),
            "Total_Wait_Time (min)": round(total_wait_time, 2),
            "Delayed_Orders": delayed_orders,
            "Avg_Delay_Days": round(total_delay_days / max(1, delayed_orders), 2),
            "TW_Violations": tw_violations,
            "Unassigned_Orders": unassigned_count
        }

    def generate_benchmark_report(self, states_dict: dict) -> pd.DataFrame:
        """
        Tổng hợp ma trận kết quả từ nhiều phương pháp để tiến hành đối chứng.
        :param states_dict: Dictionary chứa các state đầu ra {tên_phương_pháp: đối_tượng_DeliveryState}
        """
        metrics_list = []
        for method_name, state in states_dict.items():
            metrics = self.evaluate_state(state, method_name)
            metrics_list.append(metrics)
            
        report_df = pd.DataFrame(metrics_list)
        return report_df