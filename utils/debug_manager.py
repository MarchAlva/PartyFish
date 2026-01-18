import queue
import threading
import datetime

# 调试功能设置
debug_mode = True  # 调试模式开关，默认开启
debug_info_queue = queue.Queue(maxsize=200)  # 调试信息队列，用于线程间通信
debug_info_history = []  # 调试信息历史记录，最多保存200条
debug_history_lock = threading.Lock()  # 保护调试历史记录的线程锁
debug_auto_refresh = True  # 是否自动刷新调试信息
debug_window = None  # 调试窗口引用


def add_debug_info(info):
    """添加调试信息到队列和历史记录
    
    Args:
        info: 调试信息字典
    """
    if not debug_mode:
        return

    # 添加到队列（用于实时通知）
    try:
        debug_info_queue.put_nowait(info)
    except queue.Full:
        try:
            debug_info_queue.get_nowait()
            debug_info_queue.put_nowait(info)
        except:
            pass

    # 添加到历史记录（用于保留历史信息）
    with debug_history_lock:
        debug_info_history.append(info)
        # 保持历史记录不超过200条
        if len(debug_info_history) > 200:
            debug_info_history.pop(0)  # 移除最旧的记录



def get_debug_info_history():
    """获取调试信息历史记录
    
    Returns:
        调试信息历史记录列表
    """
    with debug_history_lock:
        return debug_info_history.copy()



def clear_debug_info_history():
    """清除调试信息历史记录"""
    with debug_history_lock:
        debug_info_history.clear()



def set_debug_mode(enabled):
    """设置调试模式开关
    
    Args:
        enabled: 是否启用调试模式
    """
    global debug_mode
    debug_mode = enabled



def is_debug_mode_enabled():
    """检查调试模式是否启用
    
    Returns:
        bool: 调试模式是否启用
    """
    return debug_mode



def set_debug_auto_refresh(enabled):
    """设置调试信息自动刷新
    
    Args:
        enabled: 是否启用自动刷新
    """
    global debug_auto_refresh
    debug_auto_refresh = enabled



def is_debug_auto_refresh_enabled():
    """检查调试信息自动刷新是否启用
    
    Returns:
        bool: 自动刷新是否启用
    """
    return debug_auto_refresh



def get_debug_info_queue():
    """获取调试信息队列
    
    Returns:
        调试信息队列
    """
    return debug_info_queue



def set_debug_window(window):
    """设置调试窗口引用
    
    Args:
        window: 调试窗口对象
    """
    global debug_window
    debug_window = window



def get_debug_window():
    """获取调试窗口引用
    
    Returns:
        调试窗口对象
    """
    return debug_window
