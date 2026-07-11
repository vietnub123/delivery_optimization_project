import pandas as pd
import numpy as np
from scipy.spatial import distance_matrix

class DeliveryEnvironment:
    def __init__(self, loc_filepath: str, tw_filepath: str):
        self.loc_filepath = loc_filepath
        self.tw_filepath = tw_filepath
        self.max_speed_kmh = 50.0
        
        # Biến trạng thái nội tại
        self.locations = pd.DataFrame()
        self.time_windows = pd.DataFrame()
        self.distance_matrix = np.array([])
        self.travel_time_matrix = np.array([])
        
    def execute_pipeline(self):
        """Kích hoạt chuỗi quy trình tiền xử lý dữ liệu."""
        self._load_data()
        self._build_spatial_matrices()
        self._normalize_time_windows()
        return self

    def _load_data(self):
        """Trích xuất dữ liệu từ cấu trúc tệp hệ thống."""
        self.locations = pd.read_csv(self.loc_filepath)
        self.time_windows = pd.read_csv(self.tw_filepath)
        
        # Xử lý các giá trị rỗng trong trường service_time, giả định tiệm cận 0
        if 'service_time' in self.locations.columns:
            self.locations['service_time'] = self.locations['service_time'].fillna(0)
            
    def _build_spatial_matrices(self):
        """Kiến tạo ma trận khoảng cách và ma trận thời gian di chuyển."""
        # Trích xuất vector không gian [x_km, y_km]
        coordinates = self.locations[['x_km', 'y_km']].values
        
        # Tính toán ma trận Euclid
        self.distance_matrix = distance_matrix(coordinates, coordinates)
        
        # Ánh xạ ma trận thời gian (phút) dựa trên vận tốc trần 50 km/h
        self_time_conversion_factor = 60 / self.max_speed_kmh
        self.travel_time_matrix = self.distance_matrix * self_time_conversion_factor
        
    def _normalize_time_windows(self):
        """Chuẩn hóa hệ trục thời gian đa chu kỳ."""
        def time_string_to_minutes(time_str):
            if pd.isna(time_str):
                return np.nan
            time_parts = str(time_str).split(':')
            if len(time_parts) != 2:
                return np.nan
            h, m = map(int, time_parts)
            return h * 60 + m

        # Cấu trúc hóa các điểm kỳ dị biên (cận dưới và cận trên)
        self.time_windows['start_min'] = self.time_windows['start_time'].apply(time_string_to_minutes)
        self.time_windows['end_min'] = self.time_windows['end_time'].apply(time_string_to_minutes)
        
        # Loại bỏ các bản ghi nhiễu hoặc sai định dạng thời gian
        self.time_windows.dropna(subset=['start_min', 'end_min'], inplace=True)
        
    def get_node_attributes(self, location_id: int):
            """Truy xuất vector đặc trưng của một nút trạng thái trong không gian mạng lưới."""
            
            # 1. Pha nội suy kiểu dữ liệu (Polymorphic Mapping)
            if isinstance(location_id, int):
                if location_id == 0:
                    location_id = 'DEPOT'
                else:
                    # Định dạng số nguyên thành chuỗi định danh (VD: 1 -> 'C001')
                    location_id = f"C{location_id:03d}"
                    
            # 2. Trích xuất không gian con (Subset) từ ma trận vị trí
            subset = self.locations[self.locations['location_id'] == location_id]
            
            # 3. Kiểm định tính toàn vẹn của tập hợp
            if subset.empty:
                raise ValueError(f"Không gian metric từ chối định danh: '{location_id}' không tồn tại.")
                
            # 4. Trích xuất các tham số vô hướng (Scalar parameters)
            node_data = subset.iloc[0]
            demand = node_data['demand_kg']
            service_time = node_data.get('service_time', 0.0)
            
            # 5. Xây dựng ma trận giới hạn thời gian (Time-Window Matrix)
            node_tw = self.time_windows[self.time_windows['location_id'] == location_id]
            time_windows_dict = {}
            
            for _, row in node_tw.iterrows():
                day = int(row['day_of_week'])
                if day not in time_windows_dict:
                    time_windows_dict[day] = []
                time_windows_dict[day].append((row['start_min'], row['end_min']))
                
            # 6. Kết xuất vector trạng thái tổng hợp (Dictionary Payload)
            return {
                'demand_kg': demand,
                'service_time': service_time,
                'allowed_time_windows': time_windows_dict
            }

# Khởi tạo thể hiện của môi trường và kích hoạt biên dịch
# ... (Phần định nghĩa class DeliveryEnvironment giữ nguyên) ...

# Đoạn mã dưới đây thay thế cho dòng 85 bị lỗi trong src/environment.py
if __name__ == "__main__":
    from pathlib import Path
    
    # 1. Nội suy tọa độ thư mục gốc (lùi 2 cấp từ src/environment.py -> src -> project_root)
    BASE_DIR = Path(__file__).resolve().parent.parent
    
    # 2. Xây dựng vector đường dẫn tĩnh đến phân vùng dữ liệu
    loc_file = BASE_DIR / 'data' / 'locations.csv'
    tw_file = BASE_DIR / 'data' / 'time_windows.csv'
    
    print("Khởi chạy kiểm thử độc lập phân hệ Tiền xử lý...")
    
    # 3. Ép kiểu String để truyền vào hàm khởi tạo
    env = DeliveryEnvironment(str(loc_file), str(tw_file)).execute_pipeline()
    print("Đã tải môi trường dữ liệu thành công.")