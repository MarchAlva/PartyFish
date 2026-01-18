import threading

# 鱼桶满检测设置
FISH_BUCKET_FULL_TEXT = "鱼桶满了，无法钓鱼"
fish_bucket_full_detected = False
fish_bucket_sound_enabled = True  # 是否启用鱼桶满/没鱼饵警告!音效

# 鱼桶满/没鱼饵！检测模式
# mode1: 自动暂停
# mode2: 按下一次F键然后一直鼠标左键，但检测到键盘活动时自动停止
# mode3: 不会自动暂停，只会按下一次F键
bucket_detection_mode = "mode1"  # 默认模式

# 抛竿间隔检测相关设置
casting_timestamps = []  # 存储最近的抛竿时间戳
casting_interval_lock = threading.Lock()  # 保护抛竿时间戳的线程锁
CASTING_INTERVAL_THRESHOLD = 1.0  # 抛竿间隔阈值（秒）
REQUIRED_CONSECUTIVE_MATCHES = 4  # 需要连续匹配的次数
bucket_full_by_interval = False  # 标记是否通过间隔检测到鱼桶满/没鱼饵！

# 操作状态标志，用于协调抛杆和放生操作
is_casting = False  # 当前是否正在抛杆
is_releasing = False  # 当前是否正在放生
operation_lock = threading.Lock()  # 保护操作状态的线程锁


def reset_fish_bucket_state():
    """重置鱼桶检测状态"""
    global fish_bucket_full_detected, bucket_full_by_interval
    fish_bucket_full_detected = False
    bucket_full_by_interval = False
    
    with casting_interval_lock:
        casting_timestamps.clear()


def add_casting_timestamp(timestamp):
    """添加抛竿时间戳
    
    Args:
        timestamp: 抛竿时间戳
    """
    with casting_interval_lock:
        casting_timestamps.append(timestamp)
        # 只保留最近的REQUIRED_CONSECUTIVE_MATCHES个时间戳
        if len(casting_timestamps) > REQUIRED_CONSECUTIVE_MATCHES:
            casting_timestamps.pop(0)


def check_bucket_full_by_interval():
    """通过抛竿间隔检测鱼桶是否满
    
    Returns:
        bool: 鱼桶是否满
    """
    global bucket_full_by_interval
    
    with casting_interval_lock:
        if len(casting_timestamps) < REQUIRED_CONSECUTIVE_MATCHES:
            return False
        
        # 计算最近几次抛竿的间隔
        intervals = []
        for i in range(1, len(casting_timestamps)):
            interval = casting_timestamps[i] - casting_timestamps[i-1]
            intervals.append(interval)
        
        # 检查是否所有间隔都小于阈值
        all_short_intervals = all(interval < CASTING_INTERVAL_THRESHOLD for interval in intervals)
        
        if all_short_intervals:
            bucket_full_by_interval = True
            return True
        
        return False


def set_fish_bucket_full(detected: bool):
    """设置鱼桶满状态
    
    Args:
        detected: 鱼桶是否满
    """
    global fish_bucket_full_detected
    fish_bucket_full_detected = detected


def is_fish_bucket_full() -> bool:
    """检查鱼桶是否满
    
    Returns:
        bool: 鱼桶是否满
    """
    return fish_bucket_full_detected or bucket_full_by_interval


def set_bucket_detection_mode(mode: str):
    """设置鱼桶检测模式
    
    Args:
        mode: 检测模式，可选值：mode1, mode2, mode3
    """
    global bucket_detection_mode
    if mode in ["mode1", "mode2", "mode3"]:
        bucket_detection_mode = mode


def get_bucket_detection_mode() -> str:
    """获取当前鱼桶检测模式
    
    Returns:
        当前检测模式
    """
    return bucket_detection_mode


def set_fish_bucket_sound_enabled(enabled: bool):
    """设置鱼桶满音效是否启用
    
    Args:
        enabled: 是否启用音效
    """
    global fish_bucket_sound_enabled
    fish_bucket_sound_enabled = enabled


def is_fish_bucket_sound_enabled() -> bool:
    """检查鱼桶满音效是否启用
    
    Returns:
        bool: 是否启用音效
    """
    return fish_bucket_sound_enabled


def set_casting_state(casting: bool):
    """设置抛杆状态
    
    Args:
        casting: 是否正在抛杆
    """
    global is_casting
    with operation_lock:
        is_casting = casting


def is_casting_active() -> bool:
    """检查是否正在抛杆
    
    Returns:
        bool: 是否正在抛杆
    """
    with operation_lock:
        return is_casting


def set_releasing_state(releasing: bool):
    """设置放生状态
    
    Args:
        releasing: 是否正在放生
    """
    global is_releasing
    with operation_lock:
        is_releasing = releasing


def is_releasing_active() -> bool:
    """检查是否正在放生
    
    Returns:
        bool: 是否正在放生
    """
    with operation_lock:
        return is_releasing
