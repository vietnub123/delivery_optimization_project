import numpy as np
from tqdm import tqdm
from alns import ALNS
from alns.accept import SimulatedAnnealing
from alns.select import RouletteWheel
from operators import random_removal, worst_removal, greedy_insertion
from state import DeliveryState

class ProgressStopCriterion:
    """
    Bộ bọc (Wrapper) tích hợp bộ đếm chu kỳ lặp và giao diện giám sát tiến trình.
    Tuân thủ giao thức Callable của thư viện ALNS: __call__(rnd, best, current) -> bool.
    """
    def __init__(self, max_iterations: int, pbar: tqdm):
        self.max_iterations = max_iterations
        self.pbar = pbar
        self.current_iter = 0

    def __call__(self, rnd, best, current) -> bool:
        # Cập nhật vi phân tiến trình và trạng thái hàm mục tiêu F(x)
        self.pbar.update(1)
        self.pbar.set_postfix(Cost=f"{current.objective():.2f}")
        
        # Đánh giá giới hạn hội tụ (Hội tụ khi số vòng lặp chạm ngưỡng trần)
        self.current_iter += 1
        return self.current_iter >= self.max_iterations


class ALNSOptimizer:
    def __init__(self, seed: int = 42):
        """
        Khởi tạo hệ thống tối ưu ALNS.
        Tham số seed đảm bảo tính tất định (deterministic) của ma trận ngẫu nhiên.
        """
        self.rnd_state = np.random.RandomState(seed)
        self.alns = ALNS(self.rnd_state)
        
        # Không gian toán tử Heuristic
        self.alns.add_destroy_operator(random_removal)
        self.alns.add_destroy_operator(worst_removal)
        self.alns.add_repair_operator(greedy_insertion)

    def optimize(self, initial_state: DeliveryState, iterations: int = 1000) -> DeliveryState:
        """
        Thực thi không gian tìm kiếm lân cận.
        """
        for i in range(iterations):
            # --- ĐẶT PRINT: Theo dõi vòng lặp ---
            if i % 50 == 0: # Chỉ in mỗi 50 vòng để đỡ lag
                tqdm.write(f"Đang chạy iter thứ: {i}")
        # 1. Cơ chế Chọn lọc (Roulette Wheel Selection)
        select = RouletteWheel(scores=[5, 2, 1, 0.1], 
                               decay=0.8, 
                               num_destroy=2, 
                               num_repair=1)

        # 2. Tiêu chuẩn Chấp nhận (Simulated Annealing)
        init_cost = initial_state.objective()
        
        start_temperature = (init_cost * 0.05) / np.log(2)
        end_temperature = 1.0  
        step = (end_temperature / start_temperature) ** (1 / iterations)
        
        # SỬA Ở ĐÂY: Xóa tham số 'method="multiplicative"'
        accept = SimulatedAnnealing(start_temperature=start_temperature, 
                                    end_temperature=end_temperature, 
                                    step=step)

        # 3. Khởi tạo Giao diện Giám sát và Tiêu chuẩn Dừng kết hợp
        pbar = tqdm(total=iterations, desc="[Pha 4] Tối ưu ALNS", unit="iter")
        stop_criterion = ProgressStopCriterion(max_iterations=iterations, pbar=pbar)

        # 4. Kích hoạt chu trình tìm kiếm (Loại bỏ mảng callbacks ngoại vi)
        result = self.alns.iterate(initial_state, select, accept, stop_criterion)
        
        best_state = result.best_state

        # BỔ SUNG: Gắn lịch sử hội tụ vào state để xuất ra JSON
        # history là danh sách giá trị Cost tại mỗi iteration
        best_state.convergence_history = result.statistics.objectives
        
        # 5. Giải phóng tài nguyên bộ đệm
        pbar.close()
        
        return result.best_state