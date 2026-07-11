import numpy as np
from alns import ALNS
from alns.accept import SimulatedAnnealing
from alns.select import RouletteWheel
from alns.stop import MaxIterations
from operators import random_removal, worst_removal, greedy_insertion
from state import DeliveryState

class ALNSOptimizer:
    def __init__(self, seed: int = 42):
        """
        Khởi tạo hệ thống tối ưu ALNS.
        Tham số seed đảm bảo tính tất định (deterministic) trong quá trình tái lập thực nghiệm.
        """
        self.rnd_state = np.random.RandomState(seed)
        self.alns = ALNS(self.rnd_state)
        
        # Đăng ký không gian toán tử Heuristic
        self.alns.add_destroy_operator(random_removal)
        self.alns.add_destroy_operator(worst_removal)
        self.alns.add_repair_operator(greedy_insertion)

    def optimize(self, initial_state: DeliveryState, iterations: int = 1000) -> DeliveryState:
        """
        Thực thi chu trình tối ưu hóa.
        :param initial_state: Nghiệm cơ sở (Constructive heuristic)
        :param iterations: Số chu kỳ lặp tối đa
        :return: Không gian trạng thái tối ưu toàn cục (Best state)
        """
        # 1. Cơ chế Chọn lọc Bánh xe Roulette (Roulette Wheel Selection)
        # Vector trọng số [w1, w2, w3, w4] tương ứng với mức độ thưởng:
        # w1: Tìm ra cực tiểu toàn cục mới
        # w2: Tìm ra cực tiểu cục bộ mới (nghiệm chưa từng duyệt)
        # w3: Nghiệm tồi hơn nhưng được hệ thống chấp nhận
        # w4: Nghiệm bị hệ thống từ chối
        # Hệ số suy giảm (decay_rate = 0.8) kiểm soát tốc độ quên của trọng số lịch sử
        select = RouletteWheel(scores=[5, 2, 1, 0.1], 
                               decay=0.8, 
                               num_destroy=2, 
                               num_repair=1)

        # 2. Tiêu chuẩn Chấp nhận Nghiệm: Luyện kim Mô phỏng (Simulated Annealing)
        init_cost = initial_state.objective()
        
        # Thiết lập nhiệt độ khởi tạo: Chấp nhận nghiệm có độ lệch chi phí tồi hơn 5% 
        # với xác suất 50% ở những chu kỳ lặp đầu tiên.
        start_temperature = (init_cost * 0.05) / np.log(2)
        end_temperature = 1.0  # Trạng thái đóng băng (Hội tụ)
        
        # Hàm làm mát theo hàm mũ (Exponential cooling rate)
        step = (end_temperature / start_temperature) ** (1 / iterations)
        
        accept = SimulatedAnnealing(start_temperature=start_temperature, 
                                    end_temperature=end_temperature, 
                                    step=step, 
                                    method="multiplicative")

        # 3. Tiêu chuẩn Dừng (Stopping Criterion)
        stop = MaxIterations(iterations)

        # 4. Kích hoạt chu trình tìm kiếm
        result = self.alns.iterate(initial_state, select, accept, stop)
        
        return result.best_state