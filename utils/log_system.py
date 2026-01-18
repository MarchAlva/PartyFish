import sys
import io
import datetime
import queue
import threading

# 日志系统配置
LOG_HISTORY_MAX = 500  # 最大保存500条日志

# 运行日志队列，用于存储所有控制台输出信息
log_queue = queue.Queue(maxsize=1000)
log_history = []  # 日志历史记录
log_history_lock = threading.Lock()  # 保护日志历史记录的线程锁


class LogRedirector:
    """重定向标准输出到日志系统"""

    def __init__(self, original_stream):
        self.original_stream = original_stream
        self.buffer = io.StringIO()

    def write(self, text):
        # 写入到原始流，只有当original_stream不为None时才写入
        if self.original_stream is not None:
            self.original_stream.write(text)
        # 如果文本不为空，添加到日志队列
        if text.strip():
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {text.rstrip()}"

            # 添加到队列
            try:
                log_queue.put_nowait(log_entry)
            except queue.Full:
                # 队列满时移除最旧的条目
                try:
                    log_queue.get_nowait()
                    log_queue.put_nowait(log_entry)
                except:
                    pass

            # 添加到历史记录
            with log_history_lock:
                log_history.append(log_entry)
                # 保持历史记录不超过最大限制
                if len(log_history) > LOG_HISTORY_MAX:
                    log_history.pop(0)

        # 写入到缓冲区（如果需要）
        self.buffer.write(text)

    def flush(self):
        if self.original_stream is not None:
            self.original_stream.flush()
        self.buffer.flush()


# 初始化日志系统
def init_log_system():
    """初始化日志系统，重定向标准输出和标准错误"""
    sys.stdout = LogRedirector(sys.stdout)
    sys.stderr = LogRedirector(sys.stderr)
    print("📝 [日志] 日志系统初始化成功")


# 获取日志历史
def get_log_history():
    """获取日志历史记录
    
    Returns:
        日志历史记录列表
    """
    with log_history_lock:
        return log_history.copy()


# 清除日志历史
def clear_log_history():
    """清除日志历史记录"""
    with log_history_lock:
        log_history.clear()
    print("🗑️  [日志] 日志历史已清除")


# 获取当前日志队列
def get_log_queue():
    """获取当前日志队列
    
    Returns:
        日志队列
    """
    return log_queue
