# Tệp: src/io_manager.py
import json
import numpy as np
from src.state import DeliveryState

def export_solution(state: DeliveryState, filepath: str = "best_solution.json"):
    """
    Xuất không gian nghiệm ra tệp tin vật lý JSON.
    """
    # Ép kiểu dữ liệu về chuẩn Python (int, str) để tránh lỗi numpy.int64 với JSON
    safe_routes = {}
    for day, route in state.routes.items():
        safe_routes[int(day)] = [int(node) if isinstance(node, (int, np.integer)) else str(node) for node in route]
        
    safe_unassigned = [int(node) if isinstance(node, (int, np.integer)) else str(node) for node in state.unassigned]
    
    payload = {
        "objective_cost": state.objective(),
        "routes": safe_routes,
        "unassigned": safe_unassigned
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)
    print(f"[*] Đã xuất vector nghiệm an toàn tại: {filepath}")

def import_solution(env, filepath: str = "best_solution.json") -> DeliveryState:
    """
    Tái tạo không gian nghiệm từ tệp tin vật lý JSON.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        payload = json.load(f)
        
    # JSON tự động biến key của dict thành string, ta cần ép lại về int cho 'day'
    routes = {int(day): route for day, route in payload['routes'].items()}
    unassigned = payload['unassigned']
    
    print(f"[*] Đã nạp thành công vector nghiệm (Cost cũ: {payload['objective_cost']})")
    
    # Khôi phục trạng thái đối tượng
    return DeliveryState(routes=routes, unassigned=unassigned, env=env)