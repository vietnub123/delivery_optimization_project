import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import distance_matrix

def initialize_and_process_data(loc_file, time_file):
    # 1. Đọc dữ liệu đầu vào thành DataFrames
    df_locations = pd.read_csv(loc_file)
    df_time_windows = pd.read_csv(time_file)
    print(df_locations.head())
    print(df_time_windows.head())
    # 2. Xây dựng Ma trận Khoảng cách Không gian (Euclid)
    # Giả định df_locations chứa cột tọa độ 'x_km' và 'y_km'
    coordinates = df_locations[['x_km', 'y_km']].values
    dist_matrix = distance_matrix(coordinates, coordinates)
    
    # 3. Chuẩn hóa Trường Dữ liệu Thời gian
    def convert_hhmm_to_minutes(time_str):
        if pd.isna(time_str):
            return np.nan
        # Phân rã chuỗi thời gian HH:MM
        h, m = map(int, str(time_str).split(':'))
        return h * 60 + m
    
    # Áp dụng phép biến đổi lên các cột giới hạn biên thời gian
    df_time_windows['start_min'] = df_time_windows['start_time'].apply(convert_hhmm_to_minutes)
    df_time_windows['end_min'] = df_time_windows['end_time'].apply(convert_hhmm_to_minutes)
    
    return df_locations, df_time_windows, dist_matrix

def visualize_spatial_network(df_locations):
    """
    Trực quan hóa cấu trúc topo học của mạng lưới phân phối.
    Nút đầu tiên (index 0) được quy ước mặc định là Kho trung tâm.
    """
    plt.figure(figsize=(10, 8))
    
    # Phân tách tập hợp điểm: Kho (Depot) và Tập khách hàng (Customers)
    depot = df_locations.iloc[0]
    customers = df_locations.iloc[1:]
    
    # Biểu diễn đồ thị phân bố
    plt.scatter(customers['x_km'], customers['y_km'], 
                c='#1f77b4', label='Nút Khách hàng', alpha=0.7, edgecolors='w', s=50)
    plt.scatter(depot['x_km'], depot['y_km'], 
                c='#d62728', marker='^', label='Kho Trung tâm (Depot)', s=200)
    
    # Thiết lập thuộc tính hệ quy chiếu
    plt.title('Sơ đồ Phân bố Không gian Mạng lưới Giao hàng', fontsize=14, fontweight='bold')
    plt.xlabel('Trục tọa độ X (km)', fontsize=12)
    plt.ylabel('Trục tọa độ Y (km)', fontsize=12)
    plt.legend(loc='best')
    plt.grid(True, linestyle='--', alpha=0.6)
    
    plt.tight_layout()
    plt.show()
    
# Thực thi hàm (Cần đảm bảo tệp locations.csv và time_windows.csv nằm cùng thư mục)
df_loc, df_tw, D_matrix = initialize_and_process_data('locations.csv', 'time_windows.csv')
visualize_spatial_network(df_loc)