import os
import pandas as pd
from environment import DeliveryEnvironment
from baselines import BaselineHeuristics
from solver import ALNSOptimizer
from evaluator import Evaluator
from visualizer import Visualizer

def main():
    """
    Hàm thực thi chính của hệ thống tối ưu hóa định tuyến đa chu kỳ (MP-VRPTW).
    Quy trình vận hành tuân thủ nguyên lý tuyến tính qua 5 pha tổ hợp.
    """
    # 1. Khởi tạo Không gian Môi trường và Tiền xử lý (Pha 1)
    loc_file = os.path.join('data', 'locations.csv')
    tw_file = os.path.join('data', 'time_windows.csv')
    
    print("[1/5] Biên dịch không gian hệ tọa độ và ma trận thời gian...")
    try:
        env = DeliveryEnvironment(loc_file, tw_file).execute_pipeline()
    except FileNotFoundError:
        print("Lỗi: Không tìm thấy tệp dữ liệu. Vui lòng kiểm tra lại đường dẫn thư mục 'data/'.")
        return

    # 2. Sinh Nghiệm Cơ sở - Constructive Heuristics (Pha 3)
    print("[2/5] Khởi tạo các trạng thái nghiệm cơ sở...")
    baselines = BaselineHeuristics(env)
    
    state_nn = baselines.nearest_neighbor()
    state_edd = baselines.earliest_due_date()

    # 3. Tối ưu hóa Toàn cục bằng ALNS (Pha 4)
    # Khởi tạo ALNS với nghiệm cơ sở từ EDD (giảm thiểu vi phạm khung thời gian)
    iterations = 1000
    print(f"[3/5] Kích hoạt động cơ Meta-heuristic (ALNS) với {iterations} chu kỳ lặp...")
    optimizer = ALNSOptimizer(seed=42)
    best_alns_state = optimizer.optimize(initial_state=state_edd, iterations=iterations)

    # 4. Định lượng và Đối chứng Hệ số Thống kê (Pha 5)
    print("[4/5] Kết xuất ma trận đối chứng hiệu năng (Benchmarking)...")
    evaluator = Evaluator(env)
    
    states_dict = {
        "Tham lam Khoảng cách (NN)": state_nn,
        "Tham lam Thời gian (EDD)": state_edd,
        "Tối ưu hóa ALNS": best_alns_state
    }
    
    benchmark_report = evaluator.generate_benchmark_report(states_dict)
    
    print("\n--- KẾT QUẢ KIỂM CHUẨN (BENCHMARK REPORT) ---")
    # Hiển thị cấu trúc DataFrame với định dạng tối ưu
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    print(benchmark_report.to_string(index=False))
    print("-" * 50)

    # 5. Trực quan hóa Cấu trúc Đồ thị (Pha 6)
    print("\n[5/5] Ánh xạ không gian hình học...")
    visualizer = Visualizer(env)
    visualizer.plot_routes(best_alns_state, title="Đồ thị Quỹ đạo Tối ưu - Mạng lưới Đa chu kỳ (ALNS)")

if __name__ == "__main__":
    main()