import numpy as np
import copy
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
    Loại bỏ các nút có chi phí cận biên cực đại.
    Sử dụng hàm phân phối lũy thừa để duy trì tính ngẫu nhiên.
    """
    destroyed_state = state.copy()
    base_cost = destroyed_state.objective()
    marginal_costs = []

    # Nội suy chi phí cận biên \Delta F(x)_i cho từng nút
    for day, route in destroyed_state.routes.items():
        for i, node in enumerate(route):
            temp_state = destroyed_state.copy()
            temp_state.routes[day].remove(node)
            temp_state.unassigned.append(node)
            cost_without_node = temp_state.objective()
            
            delta_cost = base_cost - cost_without_node
            marginal_costs.append((delta_cost, day, node))

    # Sắp xếp giảm dần theo \Delta F(x)
    marginal_costs.sort(key=lambda x: x[0], reverse=True)
    
    total_nodes = len(marginal_costs) + len(destroyed_state.unassigned)
    if total_nodes == 0:
        return destroyed_state
        
    q = get_removal_degree(total_nodes, rnd_state)
    q = min(q, len(marginal_costs))

    # Xóa q phần tử dựa trên hàm lũy thừa y^p với y ~ U(0,1)
    for _ in range(q):
        idx = int((rnd_state.uniform(0, 1) ** p) * len(marginal_costs))
        _, day, node = marginal_costs.pop(idx)
        destroyed_state.routes[day].remove(node)
        destroyed_state.unassigned.append(node)

    return destroyed_state

# ==========================================
# 2. TOÁN TỬ SỬA CHỮA (REPAIR OPERATORS)
# ==========================================

def greedy_insertion(state: DeliveryState, rnd_state: np.random.RandomState) -> DeliveryState:
    """
    Toán tử chèn tham lam: Phân bổ tập U vào quỹ đạo sao cho 
    đạo hàm bậc nhất của hàm mục tiêu \Delta F(x) là cực tiểu.
    """
    repaired_state = state.copy()
    
    # Xáo trộn tập chưa phân bổ để tránh hội tụ cục bộ
    rnd_state.shuffle(repaired_state.unassigned)
    
    unassigned_copy = repaired_state.unassigned.copy()
    
    for node in unassigned_copy:
        best_delta_f = float('inf')
        best_position = None  # (day, insert_index)
        
        node_attrs = repaired_state.env.get_node_attributes(node)
        allowed_days = list(node_attrs['allowed_time_windows'].keys())
        
        for day in allowed_days:
            route = repaired_state.routes.get(day, [])
            
            # Quét không gian chèn khả thi cho ngày hiện tại
            for i in range(len(route) + 1):
                temp_state = repaired_state.copy()
                temp_state.routes[day].insert(i, node)
                temp_state.unassigned.remove(node)
                
                current_f = temp_state.objective()
                
                if current_f < best_delta_f:
                    best_delta_f = current_f
                    best_position = (day, i)
        
        # Thực thi phép gán toán học nếu tồn tại cực tiểu cục bộ
        if best_position:
            day, idx = best_position
            repaired_state.routes[day].insert(idx, node)
            repaired_state.unassigned.remove(node)

    return repaired_state