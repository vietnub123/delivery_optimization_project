iter = 100 
        # Hệ số phạt (Hyperparameters) thiết lập cho các cấu trúc rào cản
        self.PENALTY_UNASSIGNED = 1e5
        self.PENALTY_DELAY_PER_DAY = 100
        self.PENALTY_TW_VIOLATION = 50       # Hệ số C cho hàm mũ
        self.ALPHA_TW = 0.05                 # Trọng số gia tốc phi tuyến (alpha)
        self.PENALTY_OVERTIME = 500.0        # Hệ số phạt vượt mốc giới hạn 24h
        
        # Trọng số tối ưu hóa cơ sở
        self.WEIGHT_DISTANCE = 1.0
        self.WEIGHT_WAIT_TIME = 0.3
