import time
import random

# 时间抖动配置
JITTER_RANGE = 0  # 时间抖动范围 ±0%

# 保存上次操作的时间戳
last_operation_time = None
last_operation_type = None


def add_jitter(base_time):
    """为给定的基础时间添加随机抖动

    Args:
        base_time: 基础时间（秒）

    Returns:
        float: 添加抖动后的时间（秒）
    """
    if base_time <= 0:
        return base_time

    # 计算抖动范围（±JITTER_RANGE%）
    jitter_factor = random.uniform(1 - JITTER_RANGE / 100, 1 + JITTER_RANGE / 100)
    jittered_time = base_time * jitter_factor

    # 确保时间不为负数且保持精度
    return max(0.01, round(jittered_time, 3))


def print_timing_info(operation_type, base_time, actual_time, previous_interval=None):
    """打印时间抖动信息

    Args:
        operation_type: 操作类型字符串
        base_time: 基础时间（秒）
        actual_time: 实际执行时间（秒）
        previous_interval: 与上次操作的时间间隔（秒）
    """
    global last_operation_time, last_operation_type

    current_time = time.time()

    # 计算与基础时间的偏差百分比
    deviation = ((actual_time - base_time) / base_time) * 100 if base_time > 0 else 0
    deviation_str = f"{deviation:+.1f}%"

    # 直接使用偏差字符串，不添加颜色
    deviation_display = deviation_str

    # 计算与上次操作的时间间隔
    interval_info = ""
    if last_operation_time is not None:
        interval = current_time - last_operation_time
        expected_interval = base_time if last_operation_type == operation_type else None

        if expected_interval is not None and expected_interval > 0:
            interval_deviation = (
                (interval - expected_interval) / expected_interval
            ) * 100
            interval_str = f"{interval:.3f}s ({interval_deviation:+.1f}%)"

            # 直接使用间隔字符串，不添加颜色
            interval_info = f" | 间隔: {interval_str}"

    # 更新最后操作信息
    last_operation_time = current_time
    last_operation_type = operation_type

    # 打印信息
    print(
        f"⏱️  [时间] {operation_type}: 基础={base_time:.3f}s, 实际={actual_time:.3f}s ({deviation_display}){interval_info}"
    )


def set_jitter_range(range_percent):
    """设置时间抖动范围
    
    Args:
        range_percent: 时间抖动范围百分比（0-100）
    """
    global JITTER_RANGE
    JITTER_RANGE = max(0, min(100, range_percent))


def get_jitter_range():
    """获取当前时间抖动范围
    
    Returns:
        当前时间抖动范围百分比
    """
    return JITTER_RANGE


def reset_operation_timing():
    """重置操作时间记录"""
    global last_operation_time, last_operation_type
    last_operation_time = None
    last_operation_type = None
