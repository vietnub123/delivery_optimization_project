import os
import pandas as pd
import sys
from pathlib import Path

# Xác lập tọa độ gốc của dự án (project root) một cách nội hàm
BASE_DIR = Path(__file__).resolve().parent

# Cập nhật không gian biến môi trường sys.path để nạp các phân hệ từ 'src'
src_path = BASE_DIR / "src"
sys.path.append(str(src_path))

# Cập nhật đường dẫn import chuẩn xác
from io_manager import export_solution, import_solution
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
    # =====================================================================
    # --- CỜ ĐIỀU KHIỂN LUỒNG (CONTROL FLAGS) ---
    # Chuyển thành "LOAD" nếu bạn chỉ muốn nạp dữ liệu từ JSON và vẽ đồ thị
    MODE = "LOAD" 
    # =====================================================================
    
    # Thiết lập đường dẫn vector lưu trữ nghiệm tĩnh
    nn_file = BASE_DIR / 'data' / 'solution_nn.json'
    edd_file = BASE_DIR / 'data' / 'solution_edd.json'
    alns_file = BASE_DIR / 'data' / 'solution_alns.json'

    # 1. Khởi tạo Không gian Môi trường và Tiền xử lý (Pha 1)
    loc_file = BASE_DIR / 'data' / 'locations.csv'
    tw_file = BASE_DIR / 'data' / 'time_windows.csv'
    
    print("[1/5] Biên dịch không gian hệ tọa độ và ma trận thời gian...")
    try:
        env = DeliveryEnvironment(str(loc_file), str(tw_file)).execute_pipeline()
    except FileNotFoundError:
        print("Lỗi: Không tìm thấy tệp dữ liệu. Vui lòng kiểm tra lại đường dẫn thư mục 'data/'.")
        return

    # Cấp phát bộ nhớ cho các biến không gian trạng thái
    state_nn, state_edd, best_alns_state = None, None, None

    # --- NHÁNH 1: THỰC THI TÍNH TOÁN VÀ LƯU TRỮ ---
    if MODE == "OPTIMIZE":
        # 2. Sinh Nghiệm Cơ sở - Constructive Heuristics (Pha 3)
        print("[2/5] Khởi tạo các trạng thái nghiệm cơ sở...")
        baselines = BaselineHeuristics(env)
        
        state_nn = baselines.nearest_neighbor()
        export_solution(state_nn, str(nn_file))
        
        state_edd = baselines.earliest_due_date()
        export_solution(state_edd, str(edd_file))

        # 3. Tối ưu hóa Toàn cục bằng ALNS (Pha 4)
        iterations = 50
        print(f"[3/5] Kích hoạt động cơ Meta-heuristic (ALNS) với {iterations} chu kỳ lặp...")
        optimizer = ALNSOptimizer(seed=42)
        best_alns_state = optimizer.optimize(initial_state=state_edd, iterations=iterations)
        export_solution(best_alns_state, str(alns_file))

    # --- NHÁNH 2: NẠP DỮ LIỆU TỪ Ổ CỨNG (BỎ QUA TÍNH TOÁN) ---
    elif MODE == "LOAD":
        print("\n[--- KÍCH HOẠT CHẾ ĐỘ PHÂN TÍCH NHANH ---]")
        if not (nn_file.exists() and edd_file.exists() and alns_file.exists()):
            print("Lỗi hạt nhân: Không tìm thấy các tệp JSON. Vui lòng đặt MODE = 'OPTIMIZE' để chạy khởi tạo lần đầu.")
            return
            
        print("[2-3/5] Nạp các vector nghiệm từ bộ lưu trữ vật lý (I/O)...")
        state_nn = import_solution(env, str(nn_file))
        state_edd = import_solution(env, str(edd_file))
        best_alns_state = import_solution(env, str(alns_file))

    # 4. Định lượng và Đối chứng Hệ số Thống kê (Pha 5)
    print("\n[4/5] Kết xuất ma trận đối chứng hiệu năng (Benchmarking)...")
    evaluator = Evaluator(env)
    
    # Đóng gói ma trận cấu trúc dữ liệu
    states_dict = {
        "Tham lam Khoảng cách (NN)": state_nn,
        "Tham lam Thời gian (EDD)": state_edd,
        "Tối ưu hóa ALNS": best_alns_state
    }
    
    benchmark_report = evaluator.generate_benchmark_report(states_dict)
    
    print("\n--- KẾT QUẢ KIỂM CHUẨN (BENCHMARK REPORT) ---")
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