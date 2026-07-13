        self.PENALTY_UNASSIGNED = 1e5      # Phạt cực nặng nếu không giao được hàng /đơn
        self.PENALTY_DELAY_PER_DAY = 100  # Phạt dời lịch giao (tuyến tính) /đơn
        self.PENALTY_TW_VIOLATION = 50   # Phạt nếu vi phạm nghiêm trọng giới hạn thời gian /phút
        self.WEIGHT_DISTANCE = 1.0         # Trọng số cho tổng quãng đường /km
        self.WEIGHT_WAIT_TIME = 0.3        # Trọng số cho tổng thời gian chờ đợi (phút)


Cơ chế phạt tuyến tính, 
Phạt cực nặng nếu ko giao
Phạt dời lịch giao nhưng chưa bao quát theo phút 1 phút phạt = 3 phút --> chỉnh lên hàm mũ
vi phạm nghiên trọng : 1 phút = 1 tiếng --> chỉnh
tổng quảng đường ok
tổng thời gian chờ ok

