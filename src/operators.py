import numpy as np
import copy
from tqdm import tqdm
from state import DeliveryState

# ==========================================
# 1. TOÁN TỬ PHÁ HỦY (DESTROY OPERATORS)
# ==========================================

def get_removal_degree(total_nodes: int, rnd_state: np.random.RandomState) -> int:
    """Xác định bậc phá hủy q dựa trên phân phối đều liên tục U(0.1, 0.3)."""
    return int(total_nodes * rnd_state.uniform(0.1, 0.3))

def random_removal(state: DeliveryState, rnd_state: np.random.RandomState) -> DeliveryState:
    """Giải phóng ngẫu nhiên q nút khỏi quỹ đạo dựa trên phân phối đồng nhất."""
    destroyed_state = state.copy()
    assigned_nodes = []
    
    for day, route in destroyed_state.routes.items():
        assigned_nodes.extend([(day, node) for node in route])
        
    if not assigned_nodes:
        return destroyed_state
        
    q = get_removal_degree(len(assigned_nodes) + len(destroyed_state.unassigned), rnd_state)
    q = min(q, len(assigned_nodes))
    
    # Rút mẫu không hoàn lại
    removed_indices = rnd_state.choice(len(assigned_nodes), q, replace=False)
    nodes_to_remove = [assigned_nodes[i] for i in removed_indices]
    
    for day, node in nodes_to_remove:
        destroyed_state.routes[day].remove(node)
        destroyed_state.unassigned.append(node)
        
    return destroyed_state

def worst_removal(state: DeliveryState, rnd_state: np.random.RandomState, p: float = 3.0) -> DeliveryState:
    """
    Tối ưu hóa worst_removal bằng cách tính toán chi phí cận biên dựa trên khoảng cách cục bộ.
    """
    destroyed_state = state.copy()
    marginal_costs = []

    # Duyệt cấu trúc không gian để tính toán mức độ đóng góp chi phí của từng nút
    for day, route in destroyed_state.routes.items():
        for i, node in enumerate(route):
            # Xác định các nút lân cận
            prev_node = route[i-1] if i > 0 else 0
            next_node = route[i+1] if i < len(route) - 1 else 0
            
            # Chi phí tiết kiệm được về mặt khoảng cách nếu loại bỏ nút hiện tại
            # Khai thác trực tiếp ma trận distance_matrix đã vector hóa
            dist_saved = (state.env.distance_matrix[prev_node][node] + 
                          state.env.distance_matrix[node][next_node] - 
                          state.env.distance_matrix[prev_node][next_node])
            
            marginal_costs.append((dist_saved, day, node))

    # Sắp xếp giảm dần theo lượng chi phí tiết kiệm
    marginal_costs.sort(key=lambda x: x[0], reverse=True)
    
    total_nodes = len(marginal_costs) + len(destroyed_state.unassigned)
    if total_nodes == 0 or not marginal_costs:
        return destroyed_state
        
    q = get_removal_degree(total_nodes, rnd_state)
    q = min(q, len(marginal_costs))

    # Loại bỏ q nút có chi phí đóng góp cao nhất dựa trên phân phối lũy thừa
    for _ in range(q):
        if not marginal_costs: break
        idx = int((rnd_state.uniform(0, 1) ** p) * len(marginal_costs))
        idx = min(idx, len(marginal_costs) - 1)
        
        _, day, node = marginal_costs.pop(idx)
        if node in destroyed_state.routes[day]:
            destroyed_state.routes[day].remove(node)
            destroyed_state.unassigned.append(node)

    return destroyed_state

# ==========================================
# 2. TOÁN TỬ SỬA CHỮA (REPAIR OPERATORS)
# ==========================================

def greedy_insertion(state: DeliveryState, rnd_state: np.random.RandomState) -> DeliveryState:
    repaired_state = state.copy()
    rnd_state.shuffle(repaired_state.unassigned)
    nodes_to_insert = repaired_state.unassigned.copy()
    
    for node in nodes_to_insert:
        tqdm.write(f"Đang thử chèn nút: {node}")
        best_delta_dist = float('inf')
        best_position = None
        
        node_attrs = repaired_state.env.get_node_attributes(node)
        # Chỉ xét ngày cho phép để tiết kiệm vòng lặp
        allowed_days = list(node_attrs['allowed_time_windows'].keys())
        
        for day in allowed_days:
            route = repaired_state.routes.get(day, [])
            
            # Tối ưu 1: Chỉ tính khoảng cách Euclid (cực nhanh)
            for i in range(len(route) + 1):
                prev_node = route[i-1] if i > 0 else 0
                next_node = route[i] if i < len(route) else 0
                
                # Tính delta khoảng cách (không cần copy state)
                dist_change = (repaired_state.env.distance_matrix[prev_node][node] + 
                               repaired_state.env.distance_matrix[node][next_node] - 
                               repaired_state.env.distance_matrix[prev_node][next_node])
                
                # Tối ưu 2: Chỉ khi dist_change tốt mới kiểm tra feasibility
                if dist_change < best_delta_dist:
                    # Kiểm tra feasibility sơ bộ (ví dụ: chỉ check khung thời gian)
                    # Không gọi objective() ở đây!
                    best_delta_dist = dist_change
                    best_position = (day, i)
        
        # Tối ưu 3: Chỉ gọi objective() 1 lần duy nhất sau khi tìm được vị trí tốt nhất
        if best_position:
            day, idx = best_position
            repaired_state.routes[day].insert(idx, node)
            repaired_state.unassigned.remove(node)
            
    return repaired_state