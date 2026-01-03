import time
import os
import webbrowser
import warnings
import cv2
import numpy as np
from PIL import Image
import threading
import ctypes
from pynput import keyboard, mouse
import datetime
import re
import queue
import random
import traceback
import builtins

# 过滤libpng的iCCP警告
warnings.filterwarnings("ignore", message=".*iCCP.*")
os.environ["OPENCV_IO_ENABLE_JASPER"] = "0"

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
import json
import mss


# =========================
# OCR引擎初始化
# =========================
try:
    from rapidocr_onnxruntime import RapidOCR
    ocr_engine = RapidOCR()
    OCR_AVAILABLE = True
    print("✅ [OCR] RapidOCR 引擎加载成功")
except ImportError:
    OCR_AVAILABLE = False
    ocr_engine = None
    print("⚠️  [OCR] RapidOCR 未安装，钓鱼记录功能将不可用")

# =========================
# 安全执行装饰器
# =========================
def safe_execute(log_name=None, default_return=None):
    """安全执行装饰器，捕获所有异常并记录日志"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = f"{log_name or func.__name__} 错误: {str(e)}\n{traceback.format_exc()}"
                print(f"❌ [错误] {error_msg}")
                if debug_mode:
                    add_debug_info({
                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                        "action": f"{func.__name__}_error",
                        "error": str(e),
                        "traceback": traceback.format_exc()
                    })
                return default_return
        return wrapper
    return decorator

# =========================
# 资源管理上下文管理器
# =========================
class MSSContext:
    """MSS截图对象的上下文管理器，确保资源正确释放"""
    def __enter__(self):
        self.scr = mss.mss()
        return self.scr
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, 'scr') and self.scr is not None:
            try:
                self.scr.close()
            except:
                pass
        return False

# =========================
# 调试信息管理函数
# =========================
def add_debug_info(info):
    """添加调试信息到队列和历史记录"""
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
            debug_info_history.pop(0)

# =========================
# 日志管理器
# =========================
class LogManager:
    """线程安全的日志管理器"""
    def __init__(self):
        self._lock = threading.RLock()
        self.log_queue = queue.Queue(maxsize=500)
        self.log_history = []
        self.max_history = 200
        self.log_text_widget = None
        self.log_paused = False
        self.log_level = "all"
        
    def add_log(self, message, level="info", source=""):
        """添加日志"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "message": message,
            "level": level,
            "source": source
        }
        
        with self._lock:
            # 添加到队列
            try:
                self.log_queue.put_nowait(log_entry)
            except queue.Full:
                try:
                    self.log_queue.get_nowait()
                    self.log_queue.put_nowait(log_entry)
                except:
                    pass
            
            # 添加到历史记录
            self.log_history.append(log_entry)
            if len(self.log_history) > self.max_history:
                self.log_history.pop(0)
            
            # 实时更新GUI
            if self.log_text_widget and not self.log_paused:
                self._update_gui_log(log_entry)
    
    def _update_gui_log(self, log_entry):
        """更新GUI日志显示"""
        try:
            if self.log_level != "all" and self.log_level != log_entry["level"]:
                return
                
            tag = log_entry["level"]
            if tag not in ["info", "success", "warning", "error", "time", "action", "system", "debug"]:
                tag = "info"
            
            formatted_log = f"[{log_entry['timestamp']}] "
            if log_entry["source"]:
                formatted_log += f"[{log_entry['source']}] "
            formatted_log += f"{log_entry['message']}\n"
            
            # 在主线程中更新
            if self.log_text_widget:
                self.log_text_widget.after(0, lambda: self._safe_insert_log(formatted_log, tag))
        except:
            pass
    
    def _safe_insert_log(self, log_text, tag):
        """安全插入日志到文本组件"""
        try:
            self.log_text_widget.insert("end", log_text, tag)
            
            # 保持自动滚动
            if hasattr(self, '_auto_scroll_var') and self._auto_scroll_var.get():
                self.log_text_widget.see("end")
            
            # 限制行数
            line_count = int(self.log_text_widget.index('end-1c').split('.')[0])
            if line_count > 1000:
                self.log_text_widget.delete("1.0", f"{line_count-500}.0")
                
        except Exception as e:
            print(f"日志显示错误: {e}")
    
    def load_history_to_gui(self):
        """加载历史日志到GUI"""
        if not self.log_text_widget:
            return
            
        self.log_text_widget.delete("1.0", "end")
        for log_entry in self.log_history[-100:]:  # 只显示最近100条
            self._update_gui_log(log_entry)
    
    def clear_logs(self):
        """清空日志"""
        with self._lock:
            self.log_queue.queue.clear()
            self.log_history.clear()
        if self.log_text_widget:
            self.log_text_widget.delete("1.0", "end")
    
    def set_auto_scroll_var(self, var):
        """设置自动滚动变量"""
        self._auto_scroll_var = var

# 创建全局日志管理器
log_manager = LogManager()

# 保存原始print函数
original_print = print

def custom_print(*args, **kwargs):
    """自定义print函数，同时输出到控制台和GUI"""
    message = " ".join(str(arg) for arg in args)
    original_print(*args, **kwargs)
    
    # 根据消息内容确定日志级别
    level = "info"
    if "✅" in message or "成功" in message:
        level = "success"
    elif "⚠️" in message or "警告" in message:
        level = "warning"
    elif "❌" in message or "错误" in message:
        level = "error"
    elif "⏱️" in message or "时间" in message:
        level = "time"
    elif "🎣" in message or "钓鱼" in message or "🐟" in message:
        level = "action"
    elif "🐛" in message or "调试" in message:
        level = "debug"
    elif "初始化" in message or "启动" in message or "清理" in message:
        level = "system"
    elif "🎲" in message or "⚙️" in message or "📊" in message:
        level = "info"
    
    # 添加到日志管理器
    log_manager.add_log(message, level, "系统")

# 替换print函数
builtins.print = custom_print

# =========================
# 线程锁 - 保护共享变量
# =========================
param_lock = threading.RLock()

# =========================
# 时间抖动配置
# =========================
JITTER_RANGE = 15
last_operation_time = None
last_operation_type = None

def add_jitter(base_time):
    """为给定的基础时间添加随机抖动"""
    if base_time <= 0:
        return base_time
    
    jitter_factor = random.uniform(1 - JITTER_RANGE/100, 1 + JITTER_RANGE/100)
    jittered_time = base_time * jitter_factor
    
    return max(0.01, round(jittered_time, 3))

def print_timing_info(operation_type, base_time, actual_time, previous_interval=None):
    """打印时间抖动信息"""
    global last_operation_time, last_operation_type
    
    current_time = time.time()
    
    deviation = ((actual_time - base_time) / base_time) * 100 if base_time > 0 else 0
    deviation_str = f"{deviation:+.1f}%"
    
    # 简单判断，不使用颜色
    if abs(deviation) <= 5:
        deviation_display = deviation_str
    elif abs(deviation) <= 10:
        deviation_display = deviation_str
    else:
        deviation_display = deviation_str
    
    interval_info = ""
    if last_operation_time is not None:
        interval = current_time - last_operation_time
        expected_interval = base_time if last_operation_type == operation_type else None
        
        if expected_interval is not None and expected_interval > 0:
            interval_deviation = ((interval - expected_interval) / expected_interval) * 100
            interval_str = f"{interval:.3f}s ({interval_deviation:+.1f}%)"
            
            interval_info = f" | 间隔: {interval_str}"
    
    last_operation_time = current_time
    last_operation_type = operation_type
    
    print(f"⏱️  [时间] {operation_type}: 基础={base_time:.3f}s, 实际={actual_time:.3f}s ({deviation_display}){interval_info}")

# =========================
# 钓鱼记录开关
# =========================
record_fish_enabled = True
legendary_screenshot_enabled = True

# =========================
# 调试功能设置
# =========================
debug_mode = True
debug_info_queue = queue.Queue(maxsize=200)
debug_info_history = []
debug_history_lock = threading.Lock()
debug_window = None
debug_auto_refresh = True

# =========================
# 参数文件路径
# =========================
PARAMETER_FILE = "./parameters.json"
FISH_RECORD_FILE = "./fish_records.txt"

# =========================
# 常数定义
# =========================
t = 0.3
leftclickdown = 2.5
leftclickup = 2
times = 15
paogantime = 0.5
BASE_WIDTH = 2560
BASE_HEIGHT = 1440
TARGET_WIDTH = 2560
TARGET_HEIGHT = 1440
resolution_choice = "current"
SCALE_X = TARGET_WIDTH / BASE_WIDTH
SCALE_Y = TARGET_HEIGHT / BASE_HEIGHT
SCALE_UNIFORM = SCALE_Y

# =========================
# 模板文件夹路径
# =========================
template_folder_path = os.path.join('.', 'resources')

# =========================
# 钓鱼记录相关
# =========================
QUALITY_LEVELS = ["标准", "非凡", "稀有", "史诗", "传说", "传奇"]
GUI_QUALITY_LEVELS = ["标准", "非凡", "稀有", "史诗", "传说"]
QUALITY_COLORS = {
    "标准": "⚪",
    "非凡": "🟢",
    "稀有": "🔵",
    "史诗": "🟣",
    "传说": "🟡",
    "传奇": "🟡"
}

FISH_INFO_REGION_BASE = (915, 75, 1640, 225)
BAIT_REGION_BASE = (2318, 1296, 2348, 1318)
JIASHI_REGION_BASE = (1245, 675, 26, 27)
BTN_NO_JIASHI_BASE = (1182, 776)
BTN_YES_JIASHI_BASE = (1398, 776)

BAIT_CROP_HEIGHT_BASE = 22
BAIT_CROP_WIDTH1_BASE = 15

current_session_id = None
gui_fish_update_callback = None

# =========================
# 热键相关
# =========================
hotkey_name = "F2"
hotkey_modifiers = set()
hotkey_main_key = keyboard.Key.f2
current_modifiers = set()

MODIFIER_KEYS = {
    keyboard.Key.ctrl_l: 'ctrl',
    keyboard.Key.ctrl_r: 'ctrl',
    keyboard.Key.alt_l: 'alt',
    keyboard.Key.alt_r: 'alt',
    keyboard.Key.alt_gr: 'alt',
    keyboard.Key.shift_l: 'shift',
    keyboard.Key.shift_r: 'shift',
}

SPECIAL_KEY_NAMES = {
    keyboard.Key.f1: "F1", keyboard.Key.f2: "F2", keyboard.Key.f3: "F3",
    keyboard.Key.f4: "F4", keyboard.Key.f5: "F5", keyboard.Key.f6: "F6",
    keyboard.Key.f7: "F7", keyboard.Key.f8: "F8", keyboard.Key.f9: "F9",
    keyboard.Key.f10: "F10", keyboard.Key.f11: "F11", keyboard.Key.f12: "F12",
    keyboard.Key.space: "Space", keyboard.Key.enter: "Enter",
    keyboard.Key.tab: "Tab", keyboard.Key.backspace: "Backspace",
    keyboard.Key.delete: "Delete", keyboard.Key.insert: "Insert",
    keyboard.Key.home: "Home", keyboard.Key.end: "End",
    keyboard.Key.page_up: "PageUp", keyboard.Key.page_down: "PageDown",
    keyboard.Key.up: "↑", keyboard.Key.down: "↓",
    keyboard.Key.left: "←", keyboard.Key.right: "→",
    keyboard.Key.esc: "Esc", keyboard.Key.pause: "Pause",
    keyboard.Key.print_screen: "PrintScreen",
    keyboard.Key.scroll_lock: "ScrollLock", keyboard.Key.caps_lock: "CapsLock",
    keyboard.Key.num_lock: "NumLock",
    mouse.Button.x1: "Mouse4",
    mouse.Button.x2: "Mouse5",
}

NAME_TO_KEY = {v: k for k, v in SPECIAL_KEY_NAMES.items()}

# =========================
# 线程安全的钓鱼记录管理
# =========================
class FishRecord:
    """单条鱼的记录"""
    def __init__(self, name, quality, weight):
        self.name = name if name else "未知"
        self.quality = quality if quality in QUALITY_LEVELS else "标准"
        self.weight = weight if weight else "0"
        self.timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.session_id = current_session_id

    def to_line(self):
        """转换为文件存储格式"""
        return f"{self.session_id}|{self.timestamp}|{self.name}|{self.quality}|{self.weight}\n"

    @staticmethod
    def from_line(line):
        """从文件行解析"""
        try:
            parts = line.strip().split("|")
            if len(parts) >= 5:
                record = FishRecord.__new__(FishRecord)
                record.session_id = parts[0]
                record.timestamp = parts[1]
                record.name = parts[2]
                record.quality = parts[3]
                record.weight = parts[4]
                return record
        except:
            pass
        return None

class ThreadSafeFishRecords:
    """线程安全的钓鱼记录管理器"""
    def __init__(self):
        self._lock = threading.RLock()
        self._current_session_fish = []
        self._all_fish_records = []
    
    def add_record(self, record):
        """添加记录"""
        with self._lock:
            self._current_session_fish.append(record)
            self._all_fish_records.append(record)
            return record
    
    def get_current_session(self):
        """获取当前会话记录"""
        with self._lock:
            return self._current_session_fish.copy()
    
    def get_all_records(self):
        """获取所有记录"""
        with self._lock:
            return self._all_fish_records.copy()
    
    def clear_current_session(self):
        """清空当前会话"""
        with self._lock:
            self._current_session_fish.clear()
    
    def clear_all_records(self):
        """清空所有记录"""
        with self._lock:
            self._current_session_fish.clear()
            self._all_fish_records.clear()
    
    def load_records(self, records):
        """加载记录"""
        with self._lock:
            self._all_fish_records = records.copy()
    
    def count_by_quality(self, use_session=True):
        """按品质统计数量"""
        with self._lock:
            records = self._current_session_fish if use_session else self._all_fish_records
            counts = {
                "标准": 0,
                "非凡": 0,
                "稀有": 0,
                "史诗": 0,
                "传说": 0,
                "传奇": 0
            }
            for record in records:
                quality = record.quality
                if quality in counts:
                    counts[quality] += 1
                elif quality == "传奇":
                    counts["传说"] += 1
            return counts

# 创建线程安全的记录管理器
fish_records = ThreadSafeFishRecords()

# =========================
# 模板缓存和性能优化
# =========================
class TemplateCache:
    """模板缓存管理器，提高性能"""
    def __init__(self):
        self._cache = {}
        self._scale_cache = {}
        self._lock = threading.RLock()
    
    def get_template(self, template_name, scale_x, scale_y):
        """获取缩放后的模板"""
        cache_key = f"{template_name}_{scale_x:.2f}_{scale_y:.2f}"
        
        with self._lock:
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        # 加载并缩放模板
        template_path = os.path.join(template_folder_path, f"{template_name}_grayscale.png")
        if not os.path.exists(template_path):
            return None
        
        try:
            img = Image.open(template_path)
            template = np.array(img)
            
            # 缩放模板
            if scale_x != 1.0 or scale_y != 1.0:
                h, w = template.shape[:2]
                new_w = max(1, int(w * scale_x))
                new_h = max(1, int(h * scale_y))
                template = cv2.resize(template, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            
            with self._lock:
                self._cache[cache_key] = template
            return template
            
        except Exception as e:
            print(f"❌ [错误] 加载模板失败 {template_name}: {e}")
            return None
    
    def clear_cache(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._scale_cache.clear()

# 创建全局模板缓存
template_cache = TemplateCache()

# =========================
# 鼠标控制器
# =========================
class MouseController:
    """线程安全的鼠标控制器"""
    def __init__(self):
        self._lock = threading.RLock()
        self.user32 = ctypes.WinDLL("user32")
        self._mouse_down = False
    
    def press_and_release(self, down_time, up_time):
        """按下和释放鼠标按钮（带时间抖动）"""
        with self._lock:
            actual_down_time = add_jitter(down_time)
            actual_up_time = add_jitter(up_time)
            
            start_time = time.time()
            
            if self._mouse_down:
                self.user32.mouse_event(0x04, 0, 0, 0, 0)
                self._mouse_down = False
            
            self.user32.mouse_event(0x02, 0, 0, 0, 0)
            self._mouse_down = True
            time.sleep(actual_down_time)
            
            self.user32.mouse_event(0x04, 0, 0, 0, 0)
            self._mouse_down = False
            time.sleep(actual_up_time)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            print_timing_info("收杆", down_time + up_time, total_time)
            return total_time
    
    def click(self, x=None, y=None):
        """点击鼠标（可选位置）"""
        with self._lock:
            if x is not None and y is not None:
                self.user32.SetCursorPos(x, y)
                time.sleep(0.05)
            
            if self._mouse_down:
                self.user32.mouse_event(0x04, 0, 0, 0, 0)
                self._mouse_down = False
            
            self.user32.mouse_event(0x02, 0, 0, 0, 0)
            time.sleep(0.1)
            self.user32.mouse_event(0x04, 0, 0, 0, 0)
            time.sleep(0.05)
    
    def ensure_up(self):
        """确保鼠标抬起状态"""
        with self._lock:
            if self._mouse_down:
                self.user32.mouse_event(0x04, 0, 0, 0, 0)
                self._mouse_down = False

# 创建全局鼠标控制器
mouse_controller = MouseController()

# =========================
# 热键管理器
# =========================
class HotkeyManager:
    """热键管理器"""
    def __init__(self):
        self.keyboard_listener = None
        self.mouse_listener = None
        self.current_modifiers = set()
        self._lock = threading.RLock()
        
        self.MODIFIER_KEYS = {
            keyboard.Key.ctrl_l: 'ctrl',
            keyboard.Key.ctrl_r: 'ctrl',
            keyboard.Key.alt_l: 'alt',
            keyboard.Key.alt_r: 'alt',
            keyboard.Key.alt_gr: 'alt',
            keyboard.Key.shift_l: 'shift',
            keyboard.Key.shift_r: 'shift',
        }
    
    def start(self):
        """启动热键监听"""
        with self._lock:
            if self.keyboard_listener is None or not self.keyboard_listener.running:
                self.keyboard_listener = keyboard.Listener(
                    on_press=self._on_key_press,
                    on_release=self._on_key_release
                )
                self.keyboard_listener.daemon = True
                self.keyboard_listener.start()
            
            if self.mouse_listener is None or not self.mouse_listener.running:
                self.mouse_listener = mouse.Listener(on_click=self._on_mouse_click)
                self.mouse_listener.daemon = True
                self.mouse_listener.start()
    
    def stop(self):
        """停止热键监听"""
        with self._lock:
            if self.keyboard_listener is not None:
                try:
                    self.keyboard_listener.stop()
                except:
                    pass
                self.keyboard_listener = None
            
            if self.mouse_listener is not None:
                try:
                    self.mouse_listener.stop()
                except:
                    pass
                self.mouse_listener = None
    
    def _on_key_press(self, key):
        """键盘按下事件"""
        time.sleep(0.02)
        
        if key in self.MODIFIER_KEYS:
            self.current_modifiers.add(self.MODIFIER_KEYS[key])
            return
        
        self._check_hotkey_match(key)
    
    def _on_key_release(self, key):
        """键盘释放事件"""
        if key in self.MODIFIER_KEYS:
            self.current_modifiers.discard(self.MODIFIER_KEYS[key])
    
    def _on_mouse_click(self, x, y, button, pressed):
        """鼠标点击事件"""
        if not pressed:
            return
        
        self._check_hotkey_match(button)
    
    def _check_hotkey_match(self, key):
        """检查按键是否匹配热键"""
        main_key_match = False
        
        if key == hotkey_main_key:
            main_key_match = True
        elif hasattr(key, 'char') and hasattr(hotkey_main_key, 'char'):
            if key.char and hotkey_main_key.char:
                main_key_match = (key.char.lower() == hotkey_main_key.char.lower())
        elif isinstance(key, mouse.Button) and isinstance(hotkey_main_key, mouse.Button):
            main_key_match = (key == hotkey_main_key)
        
        if main_key_match:
            if self.current_modifiers == hotkey_modifiers:
                toggle_run()

# 创建全局热键管理器
hotkey_manager = HotkeyManager()

# =========================
# 工具函数
# =========================
@safe_execute("获取当前屏幕分辨率", (1920, 1080))
def get_current_screen_resolution():
    """获取当前系统的屏幕分辨率"""
    try:
        user32 = ctypes.WinDLL("user32")
        width = user32.GetSystemMetrics(0)
        height = user32.GetSystemMetrics(1)
        return width, height
    except Exception as e:
        print(f"❌ [错误] 获取屏幕分辨率失败: {e}")
        return 1920, 1080

@safe_execute("获取最大屏幕分辨率", (1920, 1080))
def get_max_screen_resolution():
    """获取电脑屏幕的最大分辨率"""
    try:
        class DEVMODEW(ctypes.Structure):
            _fields_ = [
                ("dmDeviceName", ctypes.c_wchar * 32),
                ("dmSpecVersion", ctypes.wintypes.WORD),
                ("dmDriverVersion", ctypes.wintypes.WORD),
                ("dmSize", ctypes.wintypes.WORD),
                ("dmDriverExtra", ctypes.wintypes.WORD),
                ("dmFields", ctypes.wintypes.DWORD),
                ("dmPositionX", ctypes.wintypes.LONG),
                ("dmPositionY", ctypes.wintypes.LONG),
                ("dmDisplayOrientation", ctypes.wintypes.DWORD),
                ("dmDisplayFixedOutput", ctypes.wintypes.DWORD),
                ("dmColor", ctypes.wintypes.SHORT),
                ("dmDuplex", ctypes.wintypes.SHORT),
                ("dmYResolution", ctypes.wintypes.SHORT),
                ("dmTTOption", ctypes.wintypes.SHORT),
                ("dmCollate", ctypes.wintypes.SHORT),
                ("dmFormName", ctypes.c_wchar * 32),
                ("dmLogPixels", ctypes.wintypes.WORD),
                ("dmBitsPerPel", ctypes.wintypes.DWORD),
                ("dmPelsWidth", ctypes.wintypes.DWORD),
                ("dmPelsHeight", ctypes.wintypes.DWORD),
                ("dmDisplayFlags", ctypes.wintypes.DWORD),
                ("dmDisplayFrequency", ctypes.wintypes.DWORD),
                ("dmICMMethod", ctypes.wintypes.DWORD),
                ("dmICMIntent", ctypes.wintypes.DWORD),
                ("dmMediaType", ctypes.wintypes.DWORD),
                ("dmDitherType", ctypes.wintypes.DWORD),
                ("dmReserved1", ctypes.wintypes.DWORD),
                ("dmReserved2", ctypes.wintypes.DWORD),
                ("dmPanningWidth", ctypes.wintypes.DWORD),
                ("dmPanningHeight", ctypes.wintypes.DWORD)
            ]
        
        user32 = ctypes.windll.user32
        devmode = DEVMODEW()
        devmode.dmSize = ctypes.sizeof(DEVMODEW)
        
        max_width, max_height = 0, 0
        i = 0
        while user32.EnumDisplaySettingsW(None, i, ctypes.byref(devmode)):
            if devmode.dmPelsWidth > max_width:
                max_width = devmode.dmPelsWidth
                max_height = devmode.dmPelsHeight
            i += 1
        
        if max_width == 0 or max_height == 0:
            max_width = user32.GetSystemMetrics(0)
            max_height = user32.GetSystemMetrics(1)
        
        return max_width, max_height
    except:
        try:
            user32 = ctypes.windll.user32
            current_width = user32.GetSystemMetrics(0)
            current_height = user32.GetSystemMetrics(1)
            return current_width, current_height
        except:
            return 1920, 1080

def parse_hotkey_string(hotkey_str):
    """解析热键字符串"""
    parts = [p.strip() for p in hotkey_str.split('+')]
    modifiers = set()
    main_key = None
    main_key_name = ""

    for part in parts:
        part_lower = part.lower()
        if part_lower == 'ctrl':
            modifiers.add('ctrl')
        elif part_lower == 'alt':
            modifiers.add('alt')
        elif part_lower == 'shift':
            modifiers.add('shift')
        else:
            main_key_name = part
            if part in NAME_TO_KEY:
                main_key = NAME_TO_KEY[part]
            elif len(part) == 1:
                main_key = keyboard.KeyCode.from_char(part.lower())
            else:
                try:
                    main_key = getattr(keyboard.Key, part.lower())
                except AttributeError:
                    if part == "Mouse4":
                        main_key = mouse.Button.x1
                    elif part == "Mouse5":
                        main_key = mouse.Button.x2
                    else:
                        main_key = keyboard.KeyCode.from_char(part[0].lower())

    return modifiers, main_key, main_key_name

def format_hotkey_display(modifiers, main_key_name):
    """格式化热键显示字符串"""
    parts = []
    if 'ctrl' in modifiers:
        parts.append('Ctrl')
    if 'alt' in modifiers:
        parts.append('Alt')
    if 'shift' in modifiers:
        parts.append('Shift')
    parts.append(main_key_name)
    return '+'.join(parts)

def key_to_name(key):
    """将按键对象转换为显示名称"""
    if key in SPECIAL_KEY_NAMES:
        return SPECIAL_KEY_NAMES[key]
    elif hasattr(key, 'vk') and key.vk is not None:
        vk = key.vk
        if 65 <= vk <= 90:
            return chr(vk)
        elif 48 <= vk <= 57:
            return chr(vk)
        elif 96 <= vk <= 105:
            return f"Num{vk - 96}"
        elif hasattr(key, 'char') and key.char and key.char.isprintable():
            return key.char.upper()
        else:
            return f"Key{vk}"
    elif hasattr(key, 'char') and key.char and key.char.isprintable():
        return key.char.upper()
    return str(key)
# =========================
# 字体大小设置 - 改为动态计算
# =========================
def calculate_font_size(base_size=10):
    """根据分辨率动态计算字体大小"""
    screen_width, _ = get_current_screen_resolution()
    
    # 基础字体大小
    if screen_width <= 1920:  # 1080P及以下
        return base_size
    elif screen_width <= 2560:  # 2K
        return int(base_size * 1.1)
    else:  # 4K及以上
        return int(base_size * 1.2)

font_size = calculate_font_size()
preset_btns = []
input_entries = []
combo_boxes = []
fish_tree_ref = None
# =========================
# 缩放函数
# =========================
def calculate_scale_factors():
    """计算缩放比例"""
    global SCALE_X, SCALE_Y, SCALE_UNIFORM

    SCALE_X = TARGET_WIDTH / BASE_WIDTH
    SCALE_Y = TARGET_HEIGHT / BASE_HEIGHT
    SCALE_UNIFORM = SCALE_Y

    return SCALE_X, SCALE_Y, SCALE_UNIFORM

def scale_coords(x, y, w, h):
    """根据分辨率缩放坐标"""
    return (int(x * SCALE_X), int(y * SCALE_Y), int(w * SCALE_X), int(h * SCALE_Y))

def scale_coords_uniform(x, y, w, h):
    """使用统一缩放比例缩放坐标"""
    return (int(x * SCALE_UNIFORM), int(y * SCALE_UNIFORM), int(w * SCALE_UNIFORM), int(h * SCALE_UNIFORM))

def scale_point(x, y):
    """根据分辨率缩放单点坐标"""
    return (int(x * SCALE_X), int(y * SCALE_Y))

def scale_point_center_anchored(x, y):
    """使用中心锚定方式缩放单点坐标"""
    scale = SCALE_UNIFORM
    center_offset_x = x - BASE_WIDTH / 2
    center_offset_y = y - BASE_HEIGHT / 2
    return (int(TARGET_WIDTH / 2 + center_offset_x * scale),
            int(TARGET_HEIGHT / 2 + center_offset_y * scale))

def scale_corner_anchored(base_x, base_y, base_w, base_h, anchor="bottom_right"):
    """缩放锚定在角落的UI元素坐标"""
    if anchor == "bottom_right":
        offset_from_right = BASE_WIDTH - base_x
        offset_from_bottom = BASE_HEIGHT - base_y
        scale = SCALE_UNIFORM
        new_x = TARGET_WIDTH - int(offset_from_right * scale)
        new_y = TARGET_HEIGHT - int(offset_from_bottom * scale)
        new_w = int(base_w * scale)
        new_h = int(base_h * scale)
        return (new_x, new_y, new_w, new_h)
    elif anchor == "center":
        return scale_coords_uniform(base_x, base_y, base_w, base_h)
    else:
        return scale_coords(base_x, base_y, base_w, base_h)

def scale_coords_bottom_anchored(base_x, base_y, base_w, base_h):
    """缩放锚定在底部中央的UI元素坐标"""
    scale = SCALE_UNIFORM
    center_offset_x = base_x - BASE_WIDTH / 2
    new_x = int(TARGET_WIDTH / 2 + center_offset_x * scale)
    offset_from_bottom = BASE_HEIGHT - base_y
    new_y = TARGET_HEIGHT - int(offset_from_bottom * scale)
    new_w = int(base_w * scale)
    new_h = int(base_h * scale)
    return (new_x, new_y, new_w, new_h)

def scale_coords_top_center(base_x, base_y, base_w, base_h):
    """缩放锚定在顶部中央的UI元素坐标"""
    scale = SCALE_UNIFORM
    center_offset_x = base_x - BASE_WIDTH / 2
    new_x = int(TARGET_WIDTH / 2 + center_offset_x * scale)
    new_y = int(base_y * scale)
    new_w = int(base_w * scale)
    new_h = int(base_h * scale)
    return (new_x, new_y, new_w, new_h)

# =========================
# 区域坐标（将在update_region_coords中更新）
# =========================
region3_coords = None
region4_coords = None
region5_coords = None
region6_coords = None

def update_region_coords():
    """根据当前缩放比例更新所有区域坐标"""
    global region3_coords, region4_coords, region5_coords, region6_coords
    region3_coords = scale_coords_top_center(1172, 165, 34, 34)
    region4_coords = scale_coords_bottom_anchored(1100, 1329, 10, 19)
    region5_coords = scale_coords_bottom_anchored(1212, 1329, 10, 19)
    region6_coords = scale_coords_bottom_anchored(1146, 1316, 17, 21)
    reload_templates_if_scale_changed()

def reload_templates_if_scale_changed():
    """如果缩放比例变化，重新加载所有模板"""
    global _cached_scale_x, _cached_scale_y
    
    if '_cached_scale_x' not in globals() or '_cached_scale_y' not in globals():
        _cached_scale_x = SCALE_X
        _cached_scale_y = SCALE_Y
    
    if _cached_scale_x != SCALE_X or _cached_scale_y != SCALE_Y:
        _cached_scale_x = SCALE_X
        _cached_scale_y = SCALE_Y
        print(f"🔄 [模板] 分辨率变化，重新加载模板 (缩放: X={SCALE_X:.2f}, Y={SCALE_Y:.2f})")
        template_cache.clear_cache()

# =========================
# 优化的模板匹配函数
# =========================
@safe_execute("模板匹配", None)
def optimized_match_template(image, template_name, threshold=0.8):
    """优化的模板匹配函数"""
    scale = SCALE_UNIFORM
    template = template_cache.get_template(template_name, scale, scale)
    
    if template is None or image is None:
        return None
    
    try:
        res = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        
        if max_val > threshold:
            return {
                "matched": True,
                "confidence": max_val,
                "location": max_loc,
                "template_size": template.shape
            }
        else:
            return {
                "matched": False,
                "confidence": max_val,
                "location": None,
                "template_size": template.shape
            }
    except Exception as e:
        print(f"❌ [错误] 模板匹配失败 {template_name}: {e}")
        return None

# =========================
# 修复的区域捕获函数
# =========================
@safe_execute("区域捕获", None)
def safe_capture_region(x, y, w, h, scr):
    """安全捕获屏幕区域"""
    if scr is None:
        return None
    
    screen_width, screen_height = get_current_screen_resolution()
    if x < 0 or y < 0 or x + w > screen_width or y + h > screen_height:
        x = max(0, min(x, screen_width - w))
        y = max(0, min(y, screen_height - h))
        w = min(w, screen_width - x)
        h = min(h, screen_height - y)
    
    if w <= 0 or h <= 0:
        return None
    
    try:
        region = (x, y, x + w, y + h)
        frame = scr.grab(region)
        if frame is None:
            return None
        
        img = np.array(frame)
        gray_img = cv2.cvtColor(img, cv2.COLOR_RGBA2GRAY)
        return gray_img
    except Exception as e:
        print(f"❌ [错误] 捕获区域失败 ({x},{y},{w},{h}): {e}")
        return None

# =========================
# 修复的鱼饵识别函数
# =========================
@safe_execute("鱼饵识别", None)
def bait_math_val(scr):
    """识别鱼饵数量"""
    if debug_mode:
        add_debug_info({
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "action": "bait_recognition_start",
            "message": "开始识别鱼饵数量"
        })
    
    x1, y1, x2, y2 = BAIT_REGION_BASE
    base_w = x2 - x1
    base_h = y2 - y1
    
    actual_x1, actual_y1, actual_w, actual_h = scale_corner_anchored(x1, y1, base_w, base_h, anchor="bottom_right")
    actual_x2 = actual_x1 + actual_w
    actual_y2 = actual_y1 + actual_h

    region_gray = safe_capture_region(actual_x1, actual_y1, actual_w, actual_h, scr)
    if region_gray is None:
        if debug_mode:
            add_debug_info({
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "action": "bait_recognition_failed",
                "message": "无法获取鱼饵区域图像"
            })
        return None
    
    scale = SCALE_UNIFORM
    crop_h = max(1, int(BAIT_CROP_HEIGHT_BASE * scale))
    crop_w = max(1, int(BAIT_CROP_WIDTH1_BASE * scale))
    
    img_h, img_w = region_gray.shape[:2]
    crop_h = min(crop_h, img_h)
    crop_w = min(crop_w, img_w // 2)
    
    digits = []
    
    if crop_w * 2 <= img_w:
        for i in range(2):
            x_start = i * crop_w
            x_end = x_start + crop_w
            digit_region = region_gray[0:crop_h, x_start:x_end]
            
            best_digit = None
            best_confidence = 0
            
            for digit in range(10):
                match_result = optimized_match_template(digit_region, str(digit), threshold=0.7)
                if match_result and match_result["matched"] and match_result["confidence"] > best_confidence:
                    best_confidence = match_result["confidence"]
                    best_digit = digit
            
            if best_digit is not None:
                digits.append(best_digit)
    
    if not digits:
        mid_start = max(0, (img_w - crop_w) // 2)
        mid_end = min(mid_start + crop_w, img_w)
        digit_region = region_gray[0:crop_h, mid_start:mid_end]
        
        best_digit = None
        best_confidence = 0
        
        for digit in range(10):
            match_result = optimized_match_template(digit_region, str(digit), threshold=0.7)
            if match_result and match_result["matched"] and match_result["confidence"] > best_confidence:
                best_confidence = match_result["confidence"]
                best_digit = digit
        
        if best_digit is not None:
            digits.append(best_digit)
    
    if digits:
        result = 0
        for i, digit in enumerate(reversed(digits)):
            result += digit * (10 ** i)
        
        if debug_mode:
            add_debug_info({
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "action": "bait_recognition_result",
                "message": "鱼饵识别完成",
                "result": result,
                "digits": digits
            })
        
        return result
    else:
        if debug_mode:
            add_debug_info({
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "action": "bait_recognition_no_match",
                "message": "未识别到有效数字"
            })
        return None

# =========================
# 修复的加时识别函数
# =========================
@safe_execute("加时识别", False)
def fangzhu_jiashi(scr):
    """识别加时界面"""
    if debug_mode:
        add_debug_info({
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "action": "jiashi_recognition_start",
            "message": "开始识别加时界面"
        })
    
    x, y, w, h = JIASHI_REGION_BASE
    scale = SCALE_UNIFORM
    center_offset_x = x - BASE_WIDTH / 2
    center_offset_y = y - BASE_HEIGHT / 2
    actual_x = int(TARGET_WIDTH / 2 + center_offset_x * scale)
    actual_y = int(TARGET_HEIGHT / 2 + center_offset_y * scale)
    actual_w = int(w * scale)
    actual_h = int(h * scale)
    
    region_gray = safe_capture_region(actual_x, actual_y, actual_w, actual_h, scr)
    if region_gray is None:
        if debug_mode:
            add_debug_info({
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "action": "jiashi_recognition_failed",
                "message": "无法获取加时区域图像"
            })
        return False
    
    match_result = optimized_match_template(region_gray, "chang", threshold=0.8)
    
    result = match_result["matched"] if match_result else False
    
    if debug_mode:
        add_debug_info({
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "action": "jiashi_recognition_result",
            "message": "加时识别完成",
            "result": "是" if result else "否",
            "confidence": match_result["confidence"] if match_result else 0
        })
    
    return result

# =========================
# 修复的钓鱼状态识别函数
# =========================
@safe_execute("钓鱼状态识别", False)
def check_fishing_status(scr, status_type):
    """检查钓鱼状态（星星、F1、F2、上鱼）"""
    status_functions = {
        "star": (region3_coords, "star"),
        "f1": (region4_coords, "F1"),
        "f2": (region5_coords, "F2"),
        "shangyu": (region6_coords, "shangyu")
    }
    
    if status_type not in status_functions:
        return False
    
    coords, template_name = status_functions[status_type]
    region_gray = safe_capture_region(*coords, scr)
    
    if region_gray is None:
        return False
    
    match_result = optimized_match_template(region_gray, template_name, threshold=0.8)
    return match_result["matched"] if match_result else False

# =========================
# 抛竿函数（带时间抖动）
# =========================
def cast_rod_with_jitter(f_key_type="F2"):
    """带时间抖动的抛竿操作"""
    global paogantime
    
    with param_lock:
        base_time = paogantime
    
    actual_time = add_jitter(base_time)
    
    start_time = time.time()
    mouse_controller.click()
    time.sleep(actual_time)
    end_time = time.time()
    
    print_timing_info("抛竿", base_time, actual_time)
    
    return actual_time

# =========================
# OCR相关函数
# =========================
@safe_execute("捕获鱼信息区域", None)
def capture_fish_info_region(scr_param=None):
    """截取鱼信息区域的图像"""
    if scr_param is None:
        return None

    x1, y1, x2, y2 = FISH_INFO_REGION_BASE
    region = (
        int(x1 * SCALE_X),
        int(y1 * SCALE_Y),
        int(x2 * SCALE_X),
        int(y2 * SCALE_Y)
    )

    try:
        frame = scr_param.grab(region)
        if frame is None:
            if debug_mode:
                add_debug_info({
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                    "action": "capture_error",
                    "error": "截取图像失败"
                })
            return None
        img = np.array(frame)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
        
        if debug_mode:
            add_debug_info({
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "action": "capture_region",
                "message": "成功截取鱼信息区域"
            })
        
        return img_rgb
    except Exception as e:
        print(f"❌ [错误] 截取鱼信息区域失败: {e}")
        if debug_mode:
            add_debug_info({
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "action": "capture_error",
                "error": str(e)
            })
        return None

@safe_execute("OCR识别鱼信息", (None, None, None))
def recognize_fish_info_ocr(img):
    """使用OCR识别鱼的信息"""
    if not OCR_AVAILABLE or ocr_engine is None:
        if debug_mode:
            add_debug_info({
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "action": "ocr_error",
                "error": "OCR引擎不可用"
            })
        return None, None, None

    if img is None:
        if debug_mode:
            add_debug_info({
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "action": "ocr_error",
                "error": "输入图像为空"
            })
        return None, None, None

    try:
        result, elapse = ocr_engine(img)
        
        if result is None:
            result = []
        
        full_text = ""
        for line in result:
            if isinstance(line, list) and len(line) >= 2:
                full_text += line[1] + " "

        full_text = full_text.strip()

        fish_name = None
        fish_quality = None
        fish_weight = None

        if len(result) > 0 and full_text:
            # 识别品质
            for quality in QUALITY_LEVELS:
                if quality in full_text:
                    fish_quality = quality
                    break

            # 识别重量
            weight_pattern = r'(\d+\.?\d*)\s*(kg|g|千克|克)?'
            weight_matches = re.findall(weight_pattern, full_text, re.IGNORECASE)
            if weight_matches:
                for match in weight_matches:
                    if match[0]:
                        fish_weight = match[0]
                        unit = match[1].lower() if match[1] else "kg"
                        if unit in ['g', '克']:
                            fish_weight = str(float(fish_weight) / 1000)
                        fish_weight = f"{float(fish_weight):.2f}kg"

            # 识别鱼名
            fish_name_patterns = [
                r'你钓到了\s*[「【\[]?\s*(.+?)\s*[」】\]]?\s*(?:标准|非凡|稀有|史诗|传说|传奇|$)',
                r'首次捕获\s*[「【\[]?\s*(.+?)\s*[」】\]]?\s*(?:标准|非凡|稀有|史诗|传说|传奇|$)',
                r'钓到了\s*[「【\[]?\s*(.+?)\s*[」】\]]?\s*(?:标准|非凡|稀有|史诗|传说|传奇|$)',
                r'捕获\s*[「【\[]?\s*(.+?)\s*[」】\]]?\s*(?:标准|非凡|稀有|史诗|传说|传奇|$)',
            ]

            for pattern in fish_name_patterns:
                match = re.search(pattern, full_text)
                if match:
                    extracted_name = match.group(1).strip()
                    extracted_name = re.sub(r'\d+\.?\d*\s*(kg|g|千克|克)?', '', extracted_name, flags=re.IGNORECASE)
                    extracted_name = re.sub(r'[^\u4e00-\u9fa5a-zA-Z\s]', '', extracted_name)
                    extracted_name = extracted_name.strip()
                    if extracted_name and len(extracted_name) >= 2:
                        fish_name = extracted_name
                        break

            if not fish_name:
                name_text = full_text
                prefixes_to_remove = ['你钓到了', '首次捕获', '钓到了', '捕获', '你钓到', '钓到']
                for prefix in prefixes_to_remove:
                    name_text = name_text.replace(prefix, ' ')
                if fish_quality:
                    name_text = name_text.replace(fish_quality, ' ')
                name_text = re.sub(r'\d+\.?\d*\s*(kg|g|千克|克)?', '', name_text, flags=re.IGNORECASE)
                name_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z]', ' ', name_text)
                chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,}', name_text)
                if chinese_words:
                    fish_name = max(chinese_words, key=len)
        
        if debug_mode:
            debug_info = {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "action": "ocr_recognize",
                "message": "鱼信息OCR识别完成",
                "ocr_result": result,
                "full_text": full_text,
                "elapse": elapse,
                "image_shape": img.shape if img is not None else "无图像",
                "result_count": len(result),
                "has_text": bool(full_text)
            }
            add_debug_info(debug_info)
            
            debug_info = {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "action": "fish_info_recognition_complete",
                "message": "鱼信息识别完整流程完成",
                "parsed_info": {
                    "鱼名": fish_name if fish_name else "未识别",
                    "品质": fish_quality if fish_quality else "未识别",
                    "重量": fish_weight if fish_weight else "未识别"
                },
                "full_text": full_text
            }
            add_debug_info(debug_info)

        if len(result) == 0 or not full_text:
            return None, None, None

        return fish_name, fish_quality, fish_weight

    except Exception as e:
        print(f"❌ [错误] OCR识别失败: {e}")
        if debug_mode:
            add_debug_info({
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "action": "ocr_error",
                "error": str(e),
                "exception_type": type(e).__name__
            })
        return None, None, None

# =========================
# 钓鱼记录函数
# =========================
@safe_execute("保存钓鱼记录", None)
def save_fish_record(fish_record):
    """保存单条钓鱼记录到文件"""
    try:
        with open(FISH_RECORD_FILE, "a", encoding="utf-8") as f:
            f.write(fish_record.to_line())
    except Exception as e:
        print(f"❌ [错误] 保存钓鱼记录失败: {e}")

@safe_execute("加载所有钓鱼记录", None)
def load_all_fish_records():
    """加载所有历史钓鱼记录"""
    all_records = []
    try:
        if os.path.exists(FISH_RECORD_FILE):
            with open(FISH_RECORD_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        record = FishRecord.from_line(line)
                        if record:
                            all_records.append(record)
            print(f"📊 [信息] 已加载 {len(all_records)} 条历史钓鱼记录")
    except Exception as e:
        print(f"❌ [错误] 加载钓鱼记录失败: {e}")
    
    fish_records.load_records(all_records)

def start_new_session():
    """开始新的钓鱼会话"""
    global current_session_id
    current_session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fish_records.clear_current_session()
    print(f"🎣 [会话] 新钓鱼会话开始: {current_session_id}")

def end_current_session():
    """结束当前钓鱼会话"""
    global current_session_id
    current_session = fish_records.get_current_session()
    if current_session:
        print(f"📊 [会话] 本次钓鱼结束，共钓到 {len(current_session)} 条鱼")
        quality_count = fish_records.count_by_quality(use_session=True)
        for q, count in quality_count.items():
            if count > 0:
                emoji = QUALITY_COLORS.get(q, "⚪")
                print(f"   {emoji} {q}: {count} 条")
    current_session_id = None

@safe_execute("记录钓到的鱼", None)
def record_caught_fish():
    """识别并记录钓到的鱼"""
    global record_fish_enabled

    if debug_mode:
        add_debug_info({
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "action": "fish_record_start",
            "message": "开始记录钓到的鱼",
            "ocr_available": OCR_AVAILABLE,
            "record_fish_enabled": record_fish_enabled
        })

    if not OCR_AVAILABLE or not record_fish_enabled:
        if debug_mode:
            add_debug_info({
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "action": "fish_record_check",
                "message": "钓鱼记录未执行",
                "reason": "OCR不可用" if not OCR_AVAILABLE else "钓鱼记录开关已关闭"
            })
        return None

    time.sleep(0.3)

    if debug_mode:
        add_debug_info({
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "action": "fish_record_capture_start",
            "message": "准备截取鱼信息区域"
        })

    with MSSContext() as scr:
        img = capture_fish_info_region(scr)
        if img is None:
            if debug_mode:
                add_debug_info({
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                    "action": "fish_record_capture_failed",
                    "message": "鱼信息区域截取失败"
                })
            return None

        if debug_mode:
            add_debug_info({
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "action": "fish_record_capture_success",
                "message": "鱼信息区域截取成功",
                "image_shape": img.shape if img is not None else "无图像"
            })

        fish_name, fish_quality, fish_weight = recognize_fish_info_ocr(img)

        if debug_mode:
            add_debug_info({
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "action": "fish_record_ocr_result",
                "message": "OCR识别完成",
                "fish_name": fish_name,
                "fish_quality": fish_quality,
                "fish_weight": fish_weight,
                "has_valid_data": fish_name is not None or fish_quality is not None or fish_weight is not None
            })

        if fish_name is None and fish_quality is None and fish_weight is None:
            if debug_mode:
                add_debug_info({
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                    "action": "fish_record_ocr_no_data",
                    "message": "OCR识别未获取到有效鱼信息"
                })
            return None

        if debug_mode:
            add_debug_info({
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "action": "fish_record_save_start",
                "message": "准备保存钓鱼记录",
                "raw_fish_quality": fish_quality
            })

        try:
            if fish_quality == "传奇":
                fish_quality = "传说"
            fish = FishRecord(fish_name, fish_quality, fish_weight)
            
            fish_records.add_record(fish)
            save_fish_record(fish)
            
            if debug_mode:
                add_debug_info({
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                    "action": "fish_record_save_success",
                    "message": "钓鱼记录保存成功",
                    "record": {
                        "name": fish.name,
                        "quality": fish.quality,
                        "weight": fish.weight,
                        "timestamp": fish.timestamp
                    }
                })
            
            quality_emoji = QUALITY_COLORS.get(fish.quality, "⚪")
            print(f"🐟 [钓到] {quality_emoji} {fish.name} | 品质: {fish.quality} | 重量: {fish.weight}")

            if legendary_screenshot_enabled and fish.quality == "传说":
                try:
                    if debug_mode:
                        add_debug_info({
                            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                            "action": "fish_record_screenshot_start",
                            "message": "开始传说鱼自动截屏"
                        })
                    
                    with mss.mss() as sct:
                        monitor = sct.monitors[1]
                        screenshot = sct.grab(monitor)
                        
                        screenshot_dir = os.path.join('.', 'screenshots')
                        os.makedirs(screenshot_dir, exist_ok=True)
                        
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        fish_name_clean = re.sub(r'[^\w\s]', '', fish.name)
                        screenshot_path = os.path.join(screenshot_dir, f"{timestamp}_{fish_name_clean}_{fish.quality}.png")
                        
                        mss.tools.to_png(screenshot.rgb, screenshot.size, output=screenshot_path)
                        print(f"📸 [截屏] 传说鱼已自动保存: {screenshot_path}")
                        
                        if debug_mode:
                            add_debug_info({
                                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                                "action": "fish_record_screenshot_success",
                                "message": "传说鱼自动截屏成功",
                                "screenshot_path": screenshot_path
                            })
                except Exception as e:
                    print(f"❌ [错误] 截图失败: {e}")
                    if debug_mode:
                        add_debug_info({
                            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                            "action": "fish_record_screenshot_failed",
                            "message": "传说鱼自动截屏失败",
                            "error": str(e)
                        })

            if gui_fish_update_callback:
                try:
                    gui_fish_update_callback()
                    if debug_mode:
                        add_debug_info({
                            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                            "action": "fish_record_gui_update",
                            "message": "钓鱼记录GUI更新成功"
                        })
                except Exception as e:
                    if debug_mode:
                        add_debug_info({
                            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                            "action": "fish_record_gui_update_failed",
                            "message": "钓鱼记录GUI更新失败",
                            "error": str(e)
                        })
            
            return fish
        except Exception as e:
            if debug_mode:
                add_debug_info({
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                    "action": "fish_record_save_failed",
                    "message": "钓鱼记录保存失败",
                    "error": str(e)
                })
            return None


@safe_execute("保存参数", False)
def save_parameters():
    """保存参数到文件"""
    params = {
        "t": t,
        "leftclickdown": leftclickdown,
        "leftclickup": leftclickup,
        "times": times,
        "paogantime": paogantime,
        "jiashi_var": jiashi_var,
        "resolution": resolution_choice,
        "custom_width": TARGET_WIDTH,
        "custom_height": TARGET_HEIGHT,
        "hotkey": hotkey_name,
        "record_fish_enabled": record_fish_enabled,
        "legendary_screenshot_enabled": legendary_screenshot_enabled,
        "jitter_range": JITTER_RANGE,
    }
    
    if os.path.exists(PARAMETER_FILE):
        try:
            backup_file = f"{PARAMETER_FILE}.backup"
            with open(PARAMETER_FILE, 'r', encoding='utf-8') as src:
                with open(backup_file, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
        except:
            pass
    
    with open(PARAMETER_FILE, "w", encoding='utf-8') as f:
        json.dump(params, f, ensure_ascii=False, indent=2)
    print("💾 [保存] 参数已成功保存到文件")
    return True

@safe_execute("加载参数", False)
def load_parameters():
    """从文件加载参数"""
    global t, leftclickdown, leftclickup, times, paogantime, jiashi_var
    global resolution_choice, TARGET_WIDTH, TARGET_HEIGHT, SCALE_X, SCALE_Y
    global hotkey_name, hotkey_modifiers, hotkey_main_key
    global JITTER_RANGE, record_fish_enabled, legendary_screenshot_enabled
    
    if not os.path.exists(PARAMETER_FILE):
        print("📄 [信息] 未找到参数文件，使用默认值")
        return False
    
    try:
        with open(PARAMETER_FILE, "r", encoding='utf-8') as f:
            params = json.load(f)
        
        
        t = params.get("t", t)
        leftclickdown = params.get("leftclickdown", leftclickdown)
        leftclickup = params.get("leftclickup", leftclickup)
        times = params.get("times", times)
        paogantime = params.get("paogantime", paogantime)
        jiashi_var = params.get("jiashi_var", jiashi_var)
        resolution_choice = params.get("resolution", "2K")
        record_fish_enabled = params.get("record_fish_enabled", True)
        legendary_screenshot_enabled = params.get("legendary_screenshot_enabled", True)
        JITTER_RANGE = params.get("jitter_range", 15)
        
        saved_hotkey = params.get("hotkey", "F2")
        try:
            modifiers, main_key, main_key_name = parse_hotkey_string(saved_hotkey)
            if main_key is not None:
                hotkey_name = saved_hotkey
                hotkey_modifiers = modifiers
                hotkey_main_key = main_key
        except Exception:
            hotkey_name = "F2"
            hotkey_modifiers = set()
            hotkey_main_key = keyboard.Key.f2
        
        if resolution_choice == "1080P":
            TARGET_WIDTH, TARGET_HEIGHT = 1920, 1080
        elif resolution_choice == "2K":
            TARGET_WIDTH, TARGET_HEIGHT = 2560, 1440
        elif resolution_choice == "4K":
            TARGET_WIDTH, TARGET_HEIGHT = 3840, 2160
        elif resolution_choice == "current":
            TARGET_WIDTH, TARGET_HEIGHT = get_current_screen_resolution()
        elif resolution_choice == "自定义":
            TARGET_WIDTH = params.get("custom_width", 2560)
            TARGET_HEIGHT = params.get("custom_height", 1440)
        
        SCALE_X = TARGET_WIDTH / BASE_WIDTH
        SCALE_Y = TARGET_HEIGHT / BASE_HEIGHT
        calculate_scale_factors()
        update_region_coords()
        
        print(f"✅ [加载] 参数加载成功")
        return True
        
    except Exception as e:
        print(f"❌ [错误] 加载参数失败: {e}")
        return False

@safe_execute("更新参数", False)
def update_parameters(t_var, leftclickdown_var, leftclickup_var, times_var, paogantime_var, jiashi_var_option,
                      resolution_var, custom_width_var, custom_height_var, hotkey_var=None, record_fish_var=None,
                      legendary_screenshot_var=None, jitter_var=None):
    """更新所有参数"""
    global t, leftclickdown, leftclickup, times, paogantime, jiashi_var
    global resolution_choice, TARGET_WIDTH, TARGET_HEIGHT, SCALE_X, SCALE_Y
    global hotkey_name, hotkey_modifiers, hotkey_main_key
    global record_fish_enabled, legendary_screenshot_enabled, JITTER_RANGE

    with param_lock:
        try:
            t = float(t_var.get())
            leftclickdown = float(leftclickdown_var.get())
            leftclickup = float(leftclickup_var.get())
            times = int(times_var.get())
            paogantime = float(paogantime_var.get())
            jiashi_var = jiashi_var_option.get()
            
            if t <= 0 or leftclickdown <= 0 or leftclickup <= 0 or times <= 0 or paogantime <= 0:
                raise ValueError("参数值必须大于0")
            
            if record_fish_var is not None:
                record_fish_enabled = bool(record_fish_var.get())
            
            if legendary_screenshot_var is not None:
                legendary_screenshot_enabled = bool(legendary_screenshot_var.get())
            
            if jitter_var is not None:
                JITTER_RANGE = max(0, min(50, int(jitter_var.get())))

            if hotkey_var is not None:
                new_hotkey = hotkey_var.get()
                if new_hotkey:
                    try:
                        modifiers, main_key, main_key_name = parse_hotkey_string(new_hotkey)
                        if main_key is not None:
                            hotkey_name = new_hotkey
                            hotkey_modifiers = modifiers
                            hotkey_main_key = main_key
                    except Exception:
                        print("⚠️  [警告] 热键解析失败，保持原有设置")

            resolution_choice = resolution_var.get()
            if resolution_choice == "1080P":
                TARGET_WIDTH, TARGET_HEIGHT = 1920, 1080
            elif resolution_choice == "2K":
                TARGET_WIDTH, TARGET_HEIGHT = 2560, 1440
            elif resolution_choice == "4K":
                TARGET_WIDTH, TARGET_HEIGHT = 3840, 2160
            elif resolution_choice == "current":
                TARGET_WIDTH, TARGET_HEIGHT = get_current_screen_resolution()
                custom_width_var.set(str(TARGET_WIDTH))
                custom_height_var.set(str(TARGET_HEIGHT))
            elif resolution_choice == "自定义":
                min_width, max_width = 800, 7680
                min_height, max_height = 600, 4320
                
                try:
                    width = int(custom_width_var.get())
                    height = int(custom_height_var.get())
                    
                    if width < min_width or width > max_width or height < min_height or height > max_height:
                        raise ValueError(f"分辨率必须在{min_width}x{min_height}到{max_width}x{max_height}之间")
                    
                    TARGET_WIDTH = width
                    TARGET_HEIGHT = height
                    
                    custom_width_var.set(str(TARGET_WIDTH))
                    custom_height_var.set(str(TARGET_HEIGHT))
                except ValueError as e:
                    print(f"⚠️  [警告] 分辨率设置无效: {e}")
                    TARGET_WIDTH, TARGET_HEIGHT = 2560, 1440
                    custom_width_var.set("2560")
                    custom_height_var.set("1440")

            SCALE_X = TARGET_WIDTH / BASE_WIDTH
            SCALE_Y = TARGET_HEIGHT / BASE_HEIGHT
            calculate_scale_factors()
            update_region_coords()

            print("┌" + "─" * 48 + "┐")
            print("│  ⚙️  参数更新成功                              │")
            print("├" + "─" * 48 + "┤")
            print(f"│  ⏱️  循环间隔: {t:.1f}s    📍 收线: {leftclickdown:.1f}s    📍 放线: {leftclickup:.1f}s")
            print(f"│  🎣 最大拉杆: {times}次     ⏳ 抛竿: {paogantime:.1f}s    {'✅' if jiashi_var else '❌'} 加时: {'是' if jiashi_var else '否'}")
            print(f"│  🖥️  分辨率: {resolution_choice} ({TARGET_WIDTH}×{TARGET_HEIGHT})")
            print(f"│  📐 缩放比例: X={SCALE_X:.2f}  Y={SCALE_Y:.2f}  统一={SCALE_UNIFORM:.2f}")
            print(f"│  ⌨️  热键: {hotkey_name}")
            print(f"│  🎲 时间抖动: ±{JITTER_RANGE}%")
            print("└" + "─" * 48 + "┘")
            
            save_parameters()
            return True
            
        except ValueError as e:
            print(f"⚠️  [警告] 参数验证失败: {e}")
            return False
        except Exception as e:
            print(f"❌ [错误] 更新参数失败: {e}")
            return False

# =========================
# 调试窗口
# =========================
def show_debug_window():
    """显示调试窗口，展示OCR识别的详细信息"""
    global debug_window, debug_auto_refresh
    
    if debug_window is not None and debug_window.winfo_exists():
        debug_window.destroy()
    
    debug_window = ttkb.Toplevel()
    debug_window.title("🐛 调试信息")
    debug_window.geometry("800x600")
    debug_window.minsize(600, 400)
    debug_window.resizable(True, True)
    
    try:
        import sys
        import os
        if hasattr(sys, '_MEIPASS'):
            icon_path = os.path.join(sys._MEIPASS, "666.ico")
        else:
            icon_path = "666.ico"
        debug_window.iconbitmap(icon_path)
    except:
        pass
    
    main_frame = ttkb.Frame(debug_window, padding=12)
    main_frame.pack(fill=BOTH, expand=YES)
    
    title_label = ttkb.Label(main_frame, text="OCR 调试信息", font=("Segoe UI", 14, "bold"), bootstyle="primary")
    title_label.pack(pady=(0, 10))
    
    control_frame = ttkb.Frame(main_frame)
    control_frame.pack(fill=X, pady=(0, 10))
    
    auto_refresh_var = ttkb.BooleanVar(value=debug_auto_refresh)
    auto_refresh_check = ttkb.Checkbutton(
        control_frame, 
        text="自动刷新", 
        variable=auto_refresh_var, 
        bootstyle="info"
    )
    auto_refresh_check.pack(side=LEFT)
    
    def toggle_auto_refresh():
        global debug_auto_refresh
        debug_auto_refresh = auto_refresh_var.get()
    
    auto_refresh_check.configure(command=toggle_auto_refresh)
    
    def update_resolution_label():
        max_width, max_height = get_max_screen_resolution()
        current_width, current_height = get_current_screen_resolution()
        
        resolution_text = f"🖥️  当前分辨率: {current_width}×{current_height} | 最大分辨率: {max_width}×{max_height}\n" + \
                          f"🖥️  缩放比例: X={SCALE_X:.2f} Y={SCALE_Y:.2f} 统一={SCALE_UNIFORM:.2f}"
        resolution_label.configure(text=resolution_text)
    
    resolution_label = ttkb.Label(
        control_frame, 
        font=("Consolas", 10),
        bootstyle="info"
    )
    resolution_label.pack(side=TOP, fill=X, pady=(5, 0))
    
    update_resolution_label()
    
    def manual_ocr_trigger():
        temp_scr = None
        try:
            debug_info = {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "action": "manual_ocr_start",
                "message": "开始手动触发OCR识别，正在初始化截图对象..."
            }
            add_debug_info(debug_info)
            update_debug_info()
            
            with MSSContext() as temp_scr:
                debug_info = {
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                    "action": "manual_ocr_scr_init",
                    "message": "截图对象初始化成功，正在执行OCR识别..."
                }
                add_debug_info(debug_info)
                update_debug_info()
                
                img = capture_fish_info_region(temp_scr)
                if img is not None:
                    fish_name, fish_quality, fish_weight = recognize_fish_info_ocr(img)
                    debug_info = {
                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                        "action": "manual_ocr_complete",
                        "parsed_info": {
                            "鱼名": fish_name if fish_name else "未识别",
                            "品质": fish_quality if fish_quality else "未识别",
                            "重量": fish_weight if fish_weight else "未识别"
                        },
                        "message": "手动触发OCR识别完成",
                        "image_shape": img.shape
                    }
                    add_debug_info(debug_info)
                else:
                    debug_info = {
                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                        "action": "manual_ocr_failed",
                        "message": "OCR识别失败，无法截取鱼信息区域"
                    }
                    add_debug_info(debug_info)
                
                update_debug_info()
                
        except Exception as e:
            debug_info = {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "action": "manual_ocr_error",
                "error": f"手动触发OCR识别失败: {str(e)}",
                "exception_type": type(e).__name__
            }
            add_debug_info(debug_info)
            update_debug_info()
    
    manual_ocr_btn = ttkb.Button(
        control_frame, 
        text="🔍 手动触发OCR", 
        command=manual_ocr_trigger, 
        bootstyle="primary-outline"
    )
    manual_ocr_btn.pack(side=RIGHT, padx=(10, 0))
    
    refresh_btn = ttkb.Button(
        control_frame, 
        text="🔄 刷新", 
        command=lambda: update_debug_info(), 
        bootstyle="info-outline"
    )
    refresh_btn.pack(side=RIGHT, padx=(10, 0))
    
    debug_mode_var = ttkb.BooleanVar(value=debug_mode)
    debug_mode_check = ttkb.Checkbutton(
        control_frame, 
        text="启用调试模式", 
        variable=debug_mode_var, 
        bootstyle="warning"
    )
    debug_mode_check.pack(side=RIGHT)
    
    def toggle_debug_mode():
        global debug_mode
        debug_mode = debug_mode_var.get()
    
    debug_mode_check.configure(command=toggle_debug_mode)
    
    info_frame = ttkb.Frame(main_frame)
    info_frame.pack(fill=BOTH, expand=YES)
    
    scrollbar = ttkb.Scrollbar(info_frame, orient="vertical")
    scrollbar.pack(side=RIGHT, fill=Y)
    
    debug_text = tk.Text(
        info_frame,
        wrap="word",
        font=("Consolas", 10),
        bg="#1e1e1e",
        fg="#d4d4d4",
        insertbackground="white",
        yscrollcommand=scrollbar.set
    )
    debug_text.pack(fill=BOTH, expand=YES)
    scrollbar.configure(command=debug_text.yview)
    
    debug_text.tag_configure("line_number", foreground="#606060")
    debug_text.tag_configure("timestamp", foreground="#569cd6")
    debug_text.tag_configure("region", foreground="#4ec9b0")
    debug_text.tag_configure("ocr_result", foreground="#ce9178")
    debug_text.tag_configure("parsed_info", foreground="#dcdcaa")
    debug_text.tag_configure("error", foreground="#f48771")
    
    def update_debug_info():
        debug_text.delete(1.0, END)
        
        if not debug_mode:
            debug_text.insert(END, "🔴 调试模式已关闭\n", "error")
            debug_text.insert(END, "请勾选'启用调试模式'以查看OCR调试信息\n")
            return
        
        max_width, max_height = get_max_screen_resolution()
        current_width, current_height = TARGET_WIDTH, TARGET_HEIGHT
        
        with debug_history_lock:
            debug_info_list = list(debug_info_history)
        
        debug_text.insert(END, "🟢 调试模式已启用\n", "timestamp")
        debug_text.insert(END, f"📊 历史记录: 当前共有 {len(debug_info_list)} 条调试信息\n")
        debug_text.insert(END, f"🔄 自动刷新: {'开启' if debug_auto_refresh else '关闭'}\n")
        debug_text.insert(END, "-" * 60 + "\n")
        
        debug_text.insert(END, f"📋 共显示 {len(debug_info_list)} 条调试信息\n", "timestamp")
        debug_text.insert(END, "显示所有日志：\n")
        debug_text.insert(END, "-" * 60 + "\n")
        
        if not debug_info_list:
            debug_text.insert(END, "📭 暂无调试信息\n")
            debug_text.insert(END, "等待OCR识别...\n")
            debug_text.insert(END, "💡 提示: 点击'手动触发OCR'按钮可立即测试OCR识别\n")
            return
        
        for info in debug_info_list:
            timestamp = info.get("timestamp", "未知时间")
            region = info.get("region", {})
            ocr_result = info.get("ocr_result", [])
            parsed_info = info.get("parsed_info", {})
            error = info.get("error", None)
            action = info.get("action", "未知操作")
            message = info.get("message", None)
            elapse = info.get("elapse", None)
            image_shape = info.get("image_shape", None)
            result_count = info.get("result_count", None)
            has_text = info.get("has_text", None)
            exception_type = info.get("exception_type", None)
            full_text = info.get("full_text", None)
            
            debug_text.insert(END, f"📅 {timestamp} | 🔧 {action}\n", "timestamp")
            
            if message:
                debug_text.insert(END, f"💬 {message}\n")
            
            if region:
                x1, y1, x2, y2 = region.get("x1", 0), region.get("y1", 0), region.get("x2", 0), region.get("y2", 0)
                width, height = x2 - x1, y2 - y1
                debug_text.insert(END, f"📍 识别区域: ({x1}, {y1}) - ({x2}, {y2}) | 宽: {width}, 高: {height}\n", "region")
            
            if image_shape:
                debug_text.insert(END, f"🖼️ 图像尺寸: {image_shape}\n")
            
            if elapse is not None and isinstance(elapse, (int, float)):
                debug_text.insert(END, f"⏱️ 识别耗时: {elapse:.3f}秒\n")
            
            if result_count is not None:
                debug_text.insert(END, f"📊 识别结果: {result_count} 行文本 | 包含有效文本: {'是' if has_text else '否'}\n")
            
            if full_text:
                debug_text.insert(END, f"📝 完整识别文本: {full_text}\n")
            
            if ocr_result:
                debug_text.insert(END, "📋 OCR原始结果 (包含置信度):\n", "ocr_result")
                for i, line in enumerate(ocr_result):
                    if isinstance(line, list) and len(line) >= 2:
                        text = line[1]
                        confidence = line[2] if len(line) > 2 else 0
                        if isinstance(confidence, (int, float)):
                            debug_text.insert(END, f"   [{i+1}] {text} (置信度: {confidence:.2f})\n")
                        else:
                            debug_text.insert(END, f"   [{i+1}] {text} (置信度: {confidence})\n")
                    else:
                        debug_text.insert(END, f"   [{i+1}] {line}\n")
            else:
                debug_text.insert(END, "📋 OCR原始结果: 无\n", "ocr_result")
            
            if parsed_info:
                debug_text.insert(END, "🔍 解析结果:\n", "parsed_info")
                for key, value in parsed_info.items():
                    debug_text.insert(END, f"   {key}: {value}\n")
            
            if error:
                error_line = f"❌ 错误: {error}\n"
                if exception_type:
                    error_line += f"   异常类型: {exception_type}\n"
                debug_text.insert(END, error_line, "error")
            
            debug_text.insert(END, "-" * 60 + "\n")
        
        debug_text.see(END)
    
    after_id = None
    
    def schedule_update():
        global after_id
        if debug_auto_refresh and debug_window is not None and debug_window.winfo_exists():
            update_debug_info()
            after_id = debug_window.after(1000, schedule_update)
    
    schedule_update()
    
    def on_close():
        global debug_window, after_id
        if debug_window is not None:
            if after_id is not None:
                debug_window.after_cancel(after_id)
                after_id = None
            debug_window.destroy()
            debug_window = None
    
    debug_window.protocol("WM_DELETE_WINDOW", on_close)
    
    update_debug_info()
    
    return debug_window

# =========================
# 字体样式
# =========================
@safe_execute("字体样式初始化", None)
def init_font_styles(style):
    """根据分辨率动态初始化所有字体样式"""
    screen_width, _ = get_current_screen_resolution()
    base_size = calculate_font_size()
    
    font_sizes = {
        "Title": int(base_size * 1.4),
        "Subtitle": int(base_size * 0.8),
        "Label": base_size,
        "Entry": base_size,
        "Button": base_size,
        "Treeview": base_size,
        "Combobox": base_size,
        "Small": int(base_size * 0.7),
        "Stats": int(base_size * 1.1),
        "StatsTotal": int(base_size * 1.2),
    }
    
    base_font = "Segoe UI"
    
    try:
        label_font = (base_font, font_sizes["Label"])
        label_styles = [
            "TLabel",
            "TLabelframe.Label",
            "Status.TLabel",
            "Stats.TLabel"
        ]
        for style_name in label_styles:
            style.configure(style_name, font=label_font)
        
        entry_font = (base_font, font_sizes["Entry"])
        entry_styles = ["TEntry", "Entry"]
        for style_name in entry_styles:
            style.configure(style_name, font=entry_font)
        
        combobox_font = (base_font, font_sizes["Combobox"])
        combobox_styles = [
            "TCombobox",
            "Combobox",
            "TCombobox.Listbox",
            "Combobox.Listbox"
        ]
        for style_name in combobox_styles:
            style.configure(style_name, font=combobox_font)
        
        style.configure("TCheckbutton", font=label_font)
        
        treeview_font = (base_font, font_sizes["Treeview"])
        treeview_rowheight = int(font_sizes["Treeview"] * 2.2)
        treeview_styles = [
            ("Treeview", treeview_font, treeview_rowheight),
            ("CustomTreeview.Treeview", treeview_font, treeview_rowheight)
        ]
        for style_name, font, rowheight in treeview_styles:
            style.configure(style_name, font=font, rowheight=rowheight)
            style.configure(f"{style_name}.Heading", font=(base_font, font_sizes["Label"], "bold"))
        
        scale_styles = ["Horizontal.TScale", "Vertical.TScale"]
        for style_name in scale_styles:
            style.configure(style_name, font=label_font)
        
        radiobutton_styles = {
            "TRadiobutton": label_font,
            "Toolbutton.TRadiobutton": label_font,
            "InfoOutline.TRadiobutton": label_font,
            "SuccessOutline.TRadiobutton": label_font,
            "DangerOutline.TRadiobutton": label_font,
        }
        for style_name, font in radiobutton_styles.items():
            style.configure(style_name, font=font)
        
        button_font = (base_font, font_sizes["Button"])
        
        base_button_styles = [
            "TButton",
            "Button",
            "Toolbutton",
            "Outline.TButton",
            "Toolbutton.TButton",
            "Outline.Toolbutton.TButton"
        ]
        for style_name in base_button_styles:
            style.configure(style_name, font=button_font)
    except Exception as e:
        print(f"❌ [错误] 初始化字体样式失败: {e}")

@safe_execute("更新控件字体", None)
def update_all_widget_fonts(widget, style):
    """更新所有控件的字体大小"""
    init_font_styles(style)
    
    base_font = "Segoe UI"
    base_size = calculate_font_size()
    
    def update_widget_font(w):
        try:
            widget_type = type(w).__name__
            
            if widget_type in ["Frame", "TFrame", "TTKFrame", "Labelframe"]:
                for child in w.winfo_children():
                    update_widget_font(child)
                return
            
            try:
                w.configure(font=(base_font, base_size))
            except:
                pass
            
            for child in w.winfo_children():
                update_widget_font(child)
                
        except Exception:
            pass
    
    update_widget_font(widget)
    widget.update_idletasks()

# =========================
# 日志相关函数
# =========================
def clear_logs():
    """清空日志"""
    log_manager.clear_logs()

def toggle_log_pause():
    """切换日志暂停状态"""
    log_manager.log_paused = not log_manager.log_paused
    if hasattr(toggle_log_pause, '_pause_btn'):
        toggle_log_pause._pause_btn.configure(
            text="▶️ 继续" if log_manager.log_paused else "⏸️ 暂停"
        )

def update_log_level(*args):
    """更新日志级别"""
    if hasattr(update_log_level, '_log_level_var'):
        log_manager.log_level = update_log_level._log_level_var.get()
        log_manager.load_history_to_gui()

def export_logs():
    """导出日志到文件"""
    file_path = filedialog.asksaveasfilename(
        defaultextension=".log",
        filetypes=[("日志文件", "*.log"), ("文本文件", "*.txt"), ("所有文件", "*.*")]
    )
    if file_path:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                for log_entry in log_manager.log_history:
                    f.write(f"[{log_entry['timestamp']}] [{log_entry['source']}] {log_entry['message']}\n")
            print(f"✅ 日志已导出到: {file_path}")
        except Exception as e:
            print(f"❌ 导出日志失败: {e}")

# =========================
# GUI主函数
# =========================
@safe_execute("创建GUI", None)
def create_gui():
    """创建主GUI界面"""
    if not load_parameters():
        print("⚠️  [警告] 参数加载失败，使用默认值")

    root = ttkb.Window(themename="darkly")
    root.title("🎣 PartyFish 自动钓鱼助手 v2.9")
    root.geometry("1200x900")
    root.minsize(840, 600)
    root.maxsize(2560, 1440)
    root.resizable(True, True)
    
    # 定义滚轮事件处理函数

    def on_tree_mousewheel(event):
        fish_tree.yview_scroll(int(-1*(event.delta/120)), "units")
        return "break"

    def on_log_mousewheel(event):
        log_text.yview_scroll(int(-1*(event.delta/120)), "units")
        return "break"

    try:
        import sys
        import os
        if hasattr(sys, '_MEIPASS'):
            icon_path = os.path.join(sys._MEIPASS, "666.ico")
        else:
            icon_path = "666.ico"
        root.iconbitmap(icon_path)
    except:
        pass
    
    def on_window_resize(event):
        if not fish_tree_ref:
            return
            
        window_width = root.winfo_width()
        available_width = max(window_width - 350, 500)
        
        time_ratio = 63
        name_ratio = 80
        quality_ratio = 40
        weight_ratio = 70
        total_ratio = time_ratio + name_ratio + quality_ratio + weight_ratio
        
        tree_container_width = available_width - 30
        
        time_width = int(tree_container_width * (time_ratio / total_ratio))
        name_width = int(tree_container_width * (name_ratio / total_ratio))
        quality_width = int(tree_container_width * (quality_ratio / total_ratio))
        weight_width = int(tree_container_width - time_width - name_width - quality_width - 4)
        
        time_width = max(time_width, 120)
        name_width = max(name_width, 100)
        quality_width = max(quality_width, 50)
        weight_width = max(weight_width, 80)
        
        fish_tree_ref.column("时间", width=time_width, anchor="center")
        fish_tree_ref.column("名称", width=name_width, anchor="center")
        fish_tree_ref.column("品质", width=quality_width, anchor="center")
        fish_tree_ref.column("重量", width=weight_width, anchor="center")
    
    root.bind("<Configure>", on_window_resize)

    main_frame = ttkb.Frame(root, padding=12)
    main_frame.pack(fill=BOTH, expand=YES)

    main_frame.columnconfigure(0, weight=0, minsize=320)
    main_frame.columnconfigure(1, weight=3, minsize=500)
    main_frame.rowconfigure(0, weight=1)

    # 左侧面板 - 带滚动条
    left_container = ttkb.Frame(main_frame)
    left_container.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
    
    left_scrollbar = ttkb.Scrollbar(left_container, orient="vertical", bootstyle="info")
    left_scrollbar.pack(side=RIGHT, fill=Y)
    
    left_canvas = tk.Canvas(
        left_container,
        yscrollcommand=left_scrollbar.set,
        background="#212529",
        highlightthickness=0
    )
    left_canvas.pack(side=LEFT, fill=BOTH, expand=YES)
    
    left_scrollbar.config(command=left_canvas.yview)
    
    left_panel = ttkb.Frame(left_canvas)
    left_canvas_window = left_canvas.create_window((0, 0), window=left_panel, anchor="nw")
    
    # 创建左侧滚轮事件处理函数
    def on_left_mousewheel(event):
        left_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        left_canvas.update_idletasks()
        return "break"
    # 绑定滚轮事件到左侧所有组件
    def bind_left_scroll(widget):
        widget.bind("<MouseWheel>", on_left_mousewheel)
        widget.bind("<Enter>", lambda e: widget.focus_set())
    # 绑定到左侧所有相关组件
    bind_left_scroll(left_container)
    bind_left_scroll(left_canvas)
    bind_left_scroll(left_panel)
    # ===== 修改点3：同时绑定到左侧面板内的所有子组件 =====
    def bind_all_children(parent):
        for child in parent.winfo_children():
            try:
                # 递归绑定所有子组件
                bind_left_scroll(child)
                bind_all_children(child)
            except:
                pass
    
    # 稍后在 left_panel 完全创建后绑定
    def bind_left_panel_children():
        bind_all_children(left_panel)
    
    # 在布局完成后绑定子组件
    root.after(100, bind_left_panel_children)
    
    def on_canvas_configure(event):
        left_canvas.itemconfig(left_canvas_window, width=event.width)
    
    left_canvas.bind("<Configure>", on_canvas_configure)
    
    def update_scroll_region(event):
        left_canvas.configure(scrollregion=left_canvas.bbox("all"))
    
    left_panel.bind("<Configure>", update_scroll_region)
    
    def on_canvas_configure(event):
        left_canvas.itemconfig(left_canvas_window, width=event.width)
    
    left_canvas.bind("<Configure>", on_canvas_configure)
    
    def update_scroll_region(event):
        left_canvas.configure(scrollregion=left_canvas.bbox("all"))
    
    left_panel.bind("<Configure>", update_scroll_region)
    
    title_frame = ttkb.Frame(left_panel)
    title_frame.pack(fill=X, pady=(0, 5))

    title_label = ttkb.Label(
        title_frame,
        text="🎣 PartyFish",
        bootstyle="light"
    )
    title_label.pack()

    subtitle_label = ttkb.Label(
        title_frame,
        text="自动钓鱼参数配置",
        bootstyle="light"
    )
    subtitle_label.pack()
    
    separator = ttkb.Separator(left_panel, bootstyle="secondary")
    separator.pack(fill=X, pady=(0, 5))

    params_card = ttkb.Labelframe(
        left_panel,
        text=" ⚙️ 钓鱼参数 ",
        padding=8,
        bootstyle="info"
    )
    params_card.pack(fill=X, pady=(0, 4))

    def create_param_row(parent, label_text, var, row, tooltip=""):
        label = ttkb.Label(parent, text=label_text)
        label.grid(row=row, column=0, sticky=W, pady=3, padx=(0, 8))

        entry = ttkb.Entry(parent, textvariable=var, width=10)
        entry.grid(row=row, column=1, sticky=E, pady=3)
        
        input_entries.append(entry)
        
        return entry

    t_var = ttkb.StringVar(value=str(t))
    create_param_row(params_card, "循环间隔 (秒)", t_var, 0)

    leftclickdown_var = ttkb.StringVar(value=str(leftclickdown))
    create_param_row(params_card, "收线时间 (秒)", leftclickdown_var, 1)

    leftclickup_var = ttkb.StringVar(value=str(leftclickup))
    create_param_row(params_card, "放线时间 (秒)", leftclickup_var, 2)

    times_var = ttkb.StringVar(value=str(times))
    create_param_row(params_card, "最大拉杆次数", times_var, 3)

    paogantime_var = ttkb.StringVar(value=str(paogantime))
    create_param_row(params_card, "抛竿时间 (秒)", paogantime_var, 4)

    params_card.columnconfigure(0, weight=1)
    params_card.columnconfigure(1, weight=0)

    jiashi_card = ttkb.Labelframe(
        left_panel,
        text=" ⏱️ 加时选项 ",
        padding=8,
        bootstyle="warning"
    )
    jiashi_card.pack(fill=X, pady=(0, 4))

    jiashi_var_option = ttkb.IntVar(value=jiashi_var)

    jiashi_frame = ttkb.Frame(jiashi_card)
    jiashi_frame.pack(fill=X)

    jiashi_label = ttkb.Label(jiashi_frame, text="是否自动加时")
    jiashi_label.pack(side=LEFT)

    jiashi_btn_frame = ttkb.Frame(jiashi_frame)
    jiashi_btn_frame.pack(side=RIGHT)

    jiashi_yes = ttkb.Radiobutton(
        jiashi_btn_frame,
        text="是",
        variable=jiashi_var_option,
        value=1,
        bootstyle="success-outline-toolbutton"
    )
    jiashi_yes.pack(side=LEFT, padx=5)

    jiashi_no = ttkb.Radiobutton(
        jiashi_btn_frame,
        text="否",
        variable=jiashi_var_option,
        value=0,
        bootstyle="danger-outline-toolbutton"
    )
    jiashi_no.pack(side=LEFT, padx=5)

    hotkey_card = ttkb.Labelframe(
        left_panel,
        text=" ⌨️ 热键设置 ",
        padding=8,
        bootstyle="secondary"
    )
    hotkey_card.pack(fill=X, pady=(0, 4))

    hotkey_var = ttkb.StringVar(value=hotkey_name)

    is_capturing_hotkey = [False]
    captured_modifiers = [set()]
    captured_main_key = [None]
    captured_main_key_name = [""]
    capture_listener = [None]

    hotkey_frame = ttkb.Frame(hotkey_card)
    hotkey_frame.pack(fill=X)

    hotkey_label = ttkb.Label(hotkey_frame, text="启动/暂停热键")
    hotkey_label.pack(side=LEFT)

    hotkey_btn = ttkb.Button(
        hotkey_frame,
        text=hotkey_name,
        bootstyle="info-outline",
        width=14
    )
    hotkey_btn.pack(side=RIGHT)

    hotkey_info_label = ttkb.Label(
        hotkey_card,
        text=f"按 {hotkey_name} 启动/暂停 | 点击按钮修改",
        bootstyle="info"
    )
    hotkey_info_label.pack(pady=(3, 0))

    hotkey_tip_label = ttkb.Label(
        hotkey_card,
        text="",
        bootstyle="secondary"
    )

    def stop_hotkey_capture():
        is_capturing_hotkey[0] = False
        if capture_listener[0] is not None:
            try:
                capture_listener[0].stop()
            except:
                pass
            capture_listener[0] = None
        
        if 'mouse_capture_listener' in globals():
            mouse_listener = globals()['mouse_capture_listener']
            if mouse_listener is not None:
                try:
                    mouse_listener.stop()
                except:
                    pass
            globals()['mouse_capture_listener'] = None
        
        hotkey_btn.configure(bootstyle="info-outline")
        hotkey_tip_label.pack_forget()
        hotkey_info_label.configure(text=f"按 {hotkey_var.get()} 启动/暂停 | 点击按钮修改")

    def on_capture_key_press(key):
        if not is_capturing_hotkey[0]:
            return False
        
        if key in MODIFIER_KEYS:
            captured_modifiers[0].add(MODIFIER_KEYS[key])
            display_parts = []
            if 'ctrl' in captured_modifiers[0]:
                display_parts.append('Ctrl')
            if 'alt' in captured_modifiers[0]:
                display_parts.append('Alt')
            if 'shift' in captured_modifiers[0]:
                display_parts.append('Shift')
            display_parts.append('...')
            root.after(0, lambda: hotkey_btn.configure(text='+'.join(display_parts)))
            return True

        captured_main_key[0] = key
        captured_main_key_name[0] = key_to_name(key)

        new_hotkey = format_hotkey_display(captured_modifiers[0], captured_main_key_name[0])

        def update_gui():
            hotkey_var.set(new_hotkey)
            hotkey_btn.configure(text=new_hotkey)
            hotkey_info_label.configure(text=f"新热键: {new_hotkey} | 点击保存生效")
            stop_hotkey_capture()

        root.after(0, update_gui)
        return False

    def on_capture_key_release(key):
        if not is_capturing_hotkey[0]:
            return False
        if key in MODIFIER_KEYS:
            captured_modifiers[0].discard(MODIFIER_KEYS[key])
        return True

    def on_capture_mouse_click(x, y, button, pressed):
        if not is_capturing_hotkey[0] or not pressed:
            return
        
        if button not in [mouse.Button.x1, mouse.Button.x2]:
            return
        
        captured_main_key[0] = button
        captured_main_key_name[0] = key_to_name(button)
        
        new_hotkey = format_hotkey_display(captured_modifiers[0], captured_main_key_name[0])
        
        def update_gui():
            hotkey_var.set(new_hotkey)
            hotkey_btn.configure(text=new_hotkey)
            hotkey_info_label.configure(text=f"新热键: {new_hotkey} | 点击保存生效")
            stop_hotkey_capture()
        
        root.after(0, update_gui)

    def start_hotkey_capture():
        if is_capturing_hotkey[0]:
            stop_hotkey_capture()
            return

        is_capturing_hotkey[0] = True
        captured_modifiers[0] = set()
        captured_main_key[0] = None
        captured_main_key_name[0] = ""

        hotkey_btn.configure(text="请按键...", bootstyle="warning")
        hotkey_info_label.configure(text="按下组合键（如Ctrl+F2）或单键/鼠标侧键")
        hotkey_tip_label.configure(text="5秒内按键，或再次点击取消")
        hotkey_tip_label.pack(pady=(2, 0))

        capture_listener[0] = keyboard.Listener(
            on_press=on_capture_key_press,
            on_release=on_capture_key_release
        )
        capture_listener[0].start()
        
        global mouse_capture_listener
        mouse_capture_listener = mouse.Listener(on_click=on_capture_mouse_click)
        mouse_capture_listener.daemon = True
        mouse_capture_listener.start()

        def auto_cancel():
            if is_capturing_hotkey[0]:
                root.after(0, lambda: hotkey_btn.configure(text=hotkey_var.get()))
                stop_hotkey_capture()
        root.after(5000, auto_cancel)

    hotkey_btn.configure(command=start_hotkey_capture)

    resolution_card = ttkb.Labelframe(
        left_panel,
        text=" 🖥️ 分辨率设置 ",
        padding=8,
        bootstyle="success"
    )
    resolution_card.pack(fill=X, pady=(0, 4))

    resolution_var = ttkb.StringVar(value=resolution_choice)
    custom_width_var = ttkb.StringVar(value=str(TARGET_WIDTH))
    custom_height_var = ttkb.StringVar(value=str(TARGET_HEIGHT))

    res_btn_frame = ttkb.Frame(resolution_card)
    res_btn_frame.pack(fill=X, pady=(0, 6))
    
    custom_frame = ttkb.Frame(resolution_card)

    custom_width_label = ttkb.Label(custom_frame, text="宽:")
    custom_width_label.pack(side=LEFT, padx=(0, 3))

    custom_width_entry = ttkb.Entry(custom_frame, textvariable=custom_width_var, width=6)
    custom_width_entry.pack(side=LEFT, padx=(0, 10))

    custom_height_label = ttkb.Label(custom_frame, text="高:")
    custom_height_label.pack(side=LEFT, padx=(0, 3))

    custom_height_entry = ttkb.Entry(custom_frame, textvariable=custom_height_var, width=6)
    custom_height_entry.pack(side=LEFT)

    resolution_info_var = ttkb.StringVar(value=f"当前: {TARGET_WIDTH}×{TARGET_HEIGHT}")
    info_label = ttkb.Label(
        resolution_card,
        textvariable=resolution_info_var,
        bootstyle="info"
    )

    def update_resolution_info():
        res = resolution_var.get()
        if res == "1080P":
            resolution_info_var.set("当前: 1920×1080")
        elif res == "2K":
            resolution_info_var.set("当前: 2560×1440")
        elif res == "4K":
            resolution_info_var.set("当前: 3840×2160")
        elif res == "current":
            current_width, current_height = get_current_screen_resolution()
            resolution_info_var.set(f"当前: {current_width}×{current_height}")
        else:
            resolution_info_var.set(f"当前: {custom_width_var.get()}×{custom_height_var.get()}")

    def on_resolution_change():
        update_resolution_info()
        
        if resolution_var.get() == "current":
            current_width, current_height = get_current_screen_resolution()
            custom_width_var.set(str(current_width))
            custom_height_var.set(str(current_height))
        elif resolution_var.get() == "1080P":
            custom_width_var.set("1920")
            custom_height_var.set("1080")
        elif resolution_var.get() == "2K":
            custom_width_var.set("2560")
            custom_height_var.set("1440")
        elif resolution_var.get() == "4K":
            custom_width_var.set("3840")
            custom_height_var.set("2160")

    res_btn_frame.columnconfigure(0, weight=1)
    res_btn_frame.columnconfigure(1, weight=1)
    
    rb_1080p = ttkb.Radiobutton(
        res_btn_frame,
        text="1080P",
        variable=resolution_var,
        value="1080P",
        bootstyle="info-outline-toolbutton",
        width=10,
        command=on_resolution_change
    )
    rb_1080p.grid(row=0, column=0, padx=2, pady=2, sticky="ew")
    
    rb_2k = ttkb.Radiobutton(
        res_btn_frame,
        text="2K",
        variable=resolution_var,
        value="2K",
        bootstyle="info-outline-toolbutton",
        width=10,
        command=on_resolution_change
    )
    rb_2k.grid(row=0, column=1, padx=2, pady=2, sticky="ew")
    
    rb_4k = ttkb.Radiobutton(
        res_btn_frame,
        text="4K",
        variable=resolution_var,
        value="4K",
        bootstyle="info-outline-toolbutton",
        width=10,
        command=on_resolution_change
    )
    rb_4k.grid(row=1, column=0, padx=2, pady=2, sticky="ew")
    
    rb_current = ttkb.Radiobutton(
        res_btn_frame,
        text="当前",
        variable=resolution_var,
        value="current",
        bootstyle="info-outline-toolbutton",
        width=10,
        command=on_resolution_change
    )
    rb_current.grid(row=1, column=1, padx=2, pady=2, sticky="ew")
    
    rb_custom = ttkb.Radiobutton(
        res_btn_frame,
        text="自定义",
        variable=resolution_var,
        value="自定义",
        bootstyle="info-outline-toolbutton",
        width=10,
        command=on_resolution_change
    )
    rb_custom.grid(row=2, column=0, padx=2, pady=2, sticky="ew")
    
    custom_input_frame = ttkb.Frame(res_btn_frame)
    custom_input_frame.grid(row=2, column=1, padx=2, pady=2, sticky="ew")
    
    custom_width_label = ttkb.Label(custom_input_frame, text="宽:", width=2)
    custom_width_label.pack(side=LEFT, padx=(0, 2))

    custom_width_entry = ttkb.Entry(custom_input_frame, textvariable=custom_width_var, width=5)
    custom_width_entry.pack(side=LEFT, padx=(0, 8))

    custom_height_label = ttkb.Label(custom_input_frame, text="高:", width=2)
    custom_height_label.pack(side=LEFT, padx=(0, 2))

    custom_height_entry = ttkb.Entry(custom_input_frame, textvariable=custom_height_var, width=5)
    custom_height_entry.pack(side=LEFT)
    
    info_label.pack(pady=(8, 0))

    jitter_card = ttkb.Labelframe(
        left_panel,
        text=" ⏱️ 时间抖动设置 ",
        padding=8,
        bootstyle="warning"
    )
    jitter_card.pack(fill=X, pady=(0, 4))

    jitter_var = ttkb.IntVar(value=JITTER_RANGE)
    
    jitter_frame = ttkb.Frame(jitter_card)
    jitter_frame.pack(fill=X, pady=(5, 0))
    
    jitter_label = ttkb.Label(jitter_frame, text="时间抖动范围 (±%):")
    jitter_label.pack(side=LEFT)
    
    jitter_scale = ttkb.Scale(
        jitter_frame,
        from_=0,
        to=30,
        orient="horizontal",
        variable=jitter_var,
        bootstyle="warning",
        length=120
    )
    jitter_scale.pack(side=LEFT, padx=10)
    
    jitter_value_label = ttkb.Label(jitter_frame, text=f"{jitter_var.get()}%")
    jitter_value_label.pack(side=LEFT)
    
    def update_jitter_value(*args):
        jitter_value_label.config(text=f"{jitter_var.get()}%")
    
    jitter_var.trace("w", update_jitter_value)
    
    jitter_info_label = ttkb.Label(
        jitter_card,
        text="在抛竿和收杆时间上添加随机波动，避免检测",
        bootstyle="secondary",
        font=("Segoe UI", 8)
    )
    jitter_info_label.pack(pady=(5, 0))

    record_card = ttkb.Labelframe(
        left_panel,
        text=" 📝 钓鱼记录设置 ",
        padding=8,
        bootstyle="info"
    )
    record_card.pack(fill=X, pady=(0, 4))

    record_fish_var = ttkb.IntVar(value=1 if record_fish_enabled else 0)

    record_frame = ttkb.Frame(record_card)
    record_frame.pack(fill=X)

    record_label = ttkb.Label(record_frame, text="是否启用钓鱼记录")
    record_label.pack(side=LEFT)

    record_btn_frame = ttkb.Frame(record_frame)
    record_btn_frame.pack(side=RIGHT)

    record_yes = ttkb.Radiobutton(
        record_btn_frame,
        text="是",
        variable=record_fish_var,
        value=1,
        bootstyle="success-outline-toolbutton"
    )
    record_yes.pack(side=LEFT, padx=5)

    record_no = ttkb.Radiobutton(
        record_btn_frame,
        text="否",
        variable=record_fish_var,
        value=0,
        bootstyle="danger-outline-toolbutton"
    )
    record_no.pack(side=LEFT, padx=5)

    legendary_screenshot_var = ttkb.IntVar(value=1 if legendary_screenshot_enabled else 0)
    
    legendary_frame = ttkb.Frame(record_card)
    legendary_frame.pack(fill=X, pady=(5, 0))
    
    legendary_label = ttkb.Label(legendary_frame, text="传说/传奇鱼自动截屏")
    legendary_label.pack(side=LEFT)
    
    legendary_btn_frame = ttkb.Frame(legendary_frame)
    legendary_btn_frame.pack(side=RIGHT)
    
    legendary_yes = ttkb.Radiobutton(
        legendary_btn_frame,
        text="是",
        variable=legendary_screenshot_var,
        value=1,
        bootstyle="success-outline-toolbutton"
    )
    legendary_yes.pack(side=LEFT, padx=5)
    
    legendary_no = ttkb.Radiobutton(
        legendary_btn_frame,
        text="否",
        variable=legendary_screenshot_var,
        value=0,
        bootstyle="danger-outline-toolbutton"
    )
    legendary_no.pack(side=LEFT, padx=5)

    btn_frame = ttkb.Frame(left_panel)
    btn_frame.pack(fill=X, pady=(8, 0))

    @safe_execute("更新参数并刷新", None)
    def update_and_refresh():
        """更新参数并刷新显示"""
        success = update_parameters(
            t_var, leftclickdown_var, leftclickup_var, times_var,
            paogantime_var, jiashi_var_option, resolution_var,
            custom_width_var, custom_height_var, hotkey_var, record_fish_var,
            legendary_screenshot_var, jitter_var
        )
        
        if success:
            resolution_info_var.set(f"当前: {TARGET_WIDTH}×{TARGET_HEIGHT}")
            hotkey_info_label.config(text=f"按 {hotkey_name} 启动/暂停 | 点击按钮修改")
            hotkey_btn.configure(text=hotkey_name)
            
            status_label.config(text="✅ 参数已保存", bootstyle="success")
            root.after(2000, lambda: status_label.config(text=f"按 {hotkey_name} 启动/暂停", bootstyle="light"))
        else:
            status_label.config(text="❌ 参数保存失败", bootstyle="danger")
            root.after(2000, lambda: status_label.config(text=f"按 {hotkey_name} 启动/暂停", bootstyle="light"))

    update_button = ttkb.Button(
        btn_frame,
        text="💾 保存设置",
        command=update_and_refresh,
        bootstyle="success",
        width=16
    )
    update_button.pack(pady=3, fill=X)

    debug_button = ttkb.Button(
        btn_frame,
        text="🐛 调试",
        command=show_debug_window,
        bootstyle="warning-outline",
        width=16
    )
    debug_button.pack(pady=3, fill=X)

    status_frame = ttkb.Frame(left_panel)
    status_frame.pack(fill=X, pady=(8, 0))

    separator = ttkb.Separator(status_frame, bootstyle="secondary")
    separator.pack(fill=X, pady=(0, 5))

    status_label = ttkb.Label(
        status_frame,
        text=f"按 {hotkey_name} 启动/暂停",
        bootstyle="light"
    )
    status_label.pack()

    version_label = ttkb.Label(
        status_frame,
        text="v2.9 | PartyFish",
        bootstyle="light"
    )
    version_label.pack(pady=(2, 0))

    def open_github(event=None):
        webbrowser.open("https://github.com/FADEDTUMI/PartyFish/")

    dev_frame = ttkb.Frame(status_frame)
    dev_frame.pack(pady=(3, 0))

    dev_label = ttkb.Label(
        dev_frame,
        text="by ",
        bootstyle="light"
    )
    dev_label.pack(side=LEFT)

    dev_link = ttkb.Label(
        dev_frame,
        text="FadedTUMI/PeiXiaoXiao/MaiDong",
        bootstyle="info",
        cursor="hand2"
    )
    dev_link.pack(side=LEFT)
    dev_link.bind("<Button-1>", open_github)

    def on_enter(event):
        dev_link.configure(bootstyle="primary")

    def on_leave(event):
        dev_link.configure(bootstyle="info")

    dev_link.bind("<Enter>", on_enter)
    dev_link.bind("<Leave>", on_leave)

    right_panel = ttkb.Frame(main_frame)
    right_panel.grid(row=0, column=1, sticky="nsew")
    
    right_panel.columnconfigure(0, weight=1)
    right_panel.rowconfigure(0, weight=1)

    style = ttk.Style()
    
    style.configure("OceanBlue.TLabelframe", bordercolor="#1E90FF")
    style.configure("OceanBlue.TLabelframe.Label", foreground="#1E90FF")
    
    fish_record_card = ttkb.Labelframe(
        right_panel,
        text=" 🐟 钓鱼记录 ",
        padding=12,
        bootstyle="primary"
    )
    fish_record_card.pack(fill=BOTH, expand=YES)
    fish_record_card.configure(style="OceanBlue.TLabelframe")

    record_view_frame = ttkb.Frame(fish_record_card)
    record_view_frame.pack(fill=X, pady=(0, 10))

    view_mode = ttkb.StringVar(value="current")

    current_btn = ttkb.Radiobutton(
        record_view_frame,
        text="本次钓鱼",
        variable=view_mode,
        value="current",
        bootstyle="info-outline-toolbutton",
        command=lambda: update_fish_display()
    )
    current_btn.pack(side=LEFT, padx=5)

    all_btn = ttkb.Radiobutton(
        record_view_frame,
        text="历史总览",
        variable=view_mode,
        value="all",
        bootstyle="info-outline-toolbutton",
        command=lambda: update_fish_display()
    )
    all_btn.pack(side=LEFT, padx=5)

    refresh_btn = ttkb.Button(
        record_view_frame,
        text="🔄",
        command=lambda: update_fish_display(),
        bootstyle="info-outline",
        width=3
    )
    refresh_btn.pack(side=RIGHT, padx=5)

    search_frame = ttkb.Frame(fish_record_card)
    search_frame.pack(fill=X, pady=(0, 10))

    search_var = ttkb.StringVar()
    search_entry = ttkb.Entry(search_frame, textvariable=search_var, width=15)
    search_entry.pack(side=LEFT, padx=(0, 5))
    search_entry.insert(0, "搜索鱼名...")
    
    input_entries.append(search_entry)

    def on_search_focus_in(event):
        if search_entry.get() == "搜索鱼名...":
            search_entry.delete(0, "end")

    def on_search_focus_out(event):
        if not search_entry.get():
            search_entry.insert(0, "搜索鱼名...")

    search_entry.bind("<FocusIn>", on_search_focus_in)
    search_entry.bind("<FocusOut>", on_search_focus_out)
    search_entry.bind("<Return>", lambda e: update_fish_display())

    search_btn = ttkb.Button(
        search_frame,
        text="🔍",
        command=lambda: update_fish_display(),
        bootstyle="info-outline",
        width=3
    )
    search_btn.pack(side=LEFT, padx=(0, 10))

    quality_var = ttkb.StringVar(value="全部")
    quality_label = ttkb.Label(search_frame, text="品质:")
    quality_label.pack(side=LEFT)
    quality_combo = ttkb.Combobox(
        search_frame,
        textvariable=quality_var,
        values=["全部"] + GUI_QUALITY_LEVELS,
        width=8,
        state="readonly"
    )
    quality_combo.pack(side=LEFT, padx=5)
    quality_combo.bind("<<ComboboxSelected>>", lambda e: update_fish_display())
    
    combo_boxes.append(quality_combo)

    style.configure("Purple.TLabelframe", bordercolor="#9B59B6")
    style.configure("Purple.TLabelframe.Label", foreground="#9B59B6")
    
    stats_card = ttkb.Labelframe(
        fish_record_card,
        text=" 📊 钓鱼统计 ",
        padding=15,
        bootstyle="primary"
    )
    stats_card.pack(fill=X, pady=(0, 10))
    stats_card.configure(relief="solid", borderwidth=1)
    stats_card.configure(style="Purple.TLabelframe")
    
    stats_grid = ttkb.Frame(stats_card)
    stats_grid.pack(fill=X, expand=True)
    
    standard_var = ttkb.StringVar(value="⚪ 标准: 0 (0.00%)")
    uncommon_var = ttkb.StringVar(value="🟢 非凡: 0 (0.00%)")
    rare_var = ttkb.StringVar(value="🔵 稀有: 0 (0.00%)")
    epic_var = ttkb.StringVar(value="🟣 史诗: 0 (0.00%)")
    legendary_var = ttkb.StringVar(value="🟡 传说: 0 (0.00%)")
    total_var = ttkb.StringVar(value="📝 总计: 0 条")
    
    standard_label = ttkb.Label(stats_grid, textvariable=standard_var, foreground="#FFFFFF")
    standard_label.pack(side=LEFT, padx=10, pady=8, expand=True, fill=X)
    
    uncommon_label = ttkb.Label(stats_grid, textvariable=uncommon_var, foreground="#2ECC71")
    uncommon_label.pack(side=LEFT, padx=10, pady=8, expand=True, fill=X)
    
    rare_label = ttkb.Label(stats_grid, textvariable=rare_var, foreground="#1E90FF")
    rare_label.pack(side=LEFT, padx=10, pady=8, expand=True, fill=X)
    
    epic_label = ttkb.Label(stats_grid, textvariable=epic_var, foreground="#9B59B6")
    epic_label.pack(side=LEFT, padx=10, pady=8, expand=True, fill=X)
    
    legendary_label = ttkb.Label(stats_grid, textvariable=legendary_var, foreground="#F1C40F")
    legendary_label.pack(side=LEFT, padx=10, pady=8, expand=True, fill=X)
    
    total_frame = ttkb.Frame(stats_card)
    total_frame.pack(fill=X, expand=True)
    
    total_label = ttkb.Label(total_frame, textvariable=total_var, bootstyle="success")
    total_label.pack(side=LEFT, padx=10, pady=8)
    
    clear_btn = ttkb.Button(
        total_frame,
        text="🗑️ 清空记录",
        command=lambda: clear_fish_records(),
        bootstyle="danger-outline"
    )
    clear_btn.pack(side=RIGHT, padx=10, pady=8)
    
    tree_container = ttkb.Frame(fish_record_card)
    tree_container.pack(fill=BOTH, expand=YES, pady=(0, 8))

    columns = ("时间", "名称", "品质", "重量")
    fish_tree = ttkb.Treeview(
        tree_container,
        columns=columns,
        show="headings",
        style="CustomTreeview.Treeview"
    )
    
    global fish_tree_ref
    fish_tree_ref = fish_tree

    tree_scroll = ttkb.Scrollbar(tree_container, orient="vertical", command=fish_tree.yview, bootstyle="rounded")
    fish_tree.configure(yscrollcommand=tree_scroll.set)

    fish_tree.heading("时间", text="时间")
    fish_tree.heading("名称", text="鱼名")
    fish_tree.heading("品质", text="品质")
    fish_tree.heading("重量", text="重量")

    fish_tree.column("时间", width=0, anchor="center", stretch=YES)
    fish_tree.column("名称", width=0, anchor="center", stretch=YES)
    fish_tree.column("品质", width=0, anchor="center", stretch=YES)
    fish_tree.column("重量", width=0, anchor="center", stretch=YES)

    fish_tree.pack(side=LEFT, fill=BOTH, expand=YES)
    tree_scroll.pack(side=RIGHT, fill=Y)
    
    # 绑定钓鱼记录Treeview滚轮事件
    fish_tree.bind("<MouseWheel>", on_tree_mousewheel)
    fish_tree.bind("<Enter>", lambda e: fish_tree.focus_set())

    fish_tree.tag_configure("标准", background="#FFFFFF", foreground="#000000")
    fish_tree.tag_configure("非凡", background="#2ECC71", foreground="#000000")
    fish_tree.tag_configure("稀有", background="#1E90FF", foreground="#FFFFFF")
    fish_tree.tag_configure("史诗", background="#9B59B6", foreground="#FFFFFF")
    fish_tree.tag_configure("传说", background="#F1C40F", foreground="#000000")
    fish_tree.tag_configure("传奇", background="#F1C40F", foreground="#000000")

    stats_var = ttkb.StringVar(value="共 0 条记录")
    stats_label = ttkb.Label(
        fish_record_card,
        textvariable=stats_var,
        bootstyle="info"
    )
    stats_label.pack()

    @safe_execute("更新钓鱼记录显示", None)
    def update_fish_display():
        """更新钓鱼记录显示"""
        for item in fish_tree.get_children():
            fish_tree.delete(item)

        keyword = search_var.get()
        if keyword == "搜索鱼名...":
            keyword = ""

        use_session = (view_mode.get() == "current")
        quality_filter = quality_var.get()

        filtered = []
        all_records = []
        
        if use_session:
            all_records = fish_records.get_current_session()
        else:
            all_records = fish_records.get_all_records()
        
        for record in all_records:
            if quality_filter != "全部":
                if quality_filter == "传说":
                    if record.quality not in ["传说", "传奇"]:
                        continue
                else:
                    if record.quality != quality_filter:
                        continue
            
            if keyword and keyword.lower() not in record.name.lower():
                continue
            
            filtered.append(record)
        
        quality_counts = fish_records.count_by_quality(use_session)
        total = sum(quality_counts.values())
        
        total_legendary = quality_counts["传说"] + quality_counts["传奇"]
        
        def calc_percentage(count):
            return (count / total * 100) if total > 0 else 0
        
        standard_var.set(f"⚪ 标准: {quality_counts['标准']} ({calc_percentage(quality_counts['标准']):.2f}%)")
        uncommon_var.set(f"🟢 非凡: {quality_counts['非凡']} ({calc_percentage(quality_counts['非凡']):.2f}%)")
        rare_var.set(f"🔵 稀有: {quality_counts['稀有']} ({calc_percentage(quality_counts['稀有']):.2f}%)")
        epic_var.set(f"🟣 史诗: {quality_counts['史诗']} ({calc_percentage(quality_counts['史诗']):.2f}%)")
        legendary_var.set(f"🟡 传说: {total_legendary} ({calc_percentage(total_legendary):.2f}%)")
        total_var.set(f"📊 总计: {total} 条")

        for record in reversed(filtered[-100:]):
            time_display = record.timestamp if record.timestamp else "未知时间"
            quality_tag = record.quality if record.quality in ["标准", "非凡", "稀有", "史诗", "传说", "传奇"] else "标准"

            fish_tree.insert("", "end", values=(
                time_display,
                record.name,
                record.quality,
                record.weight
            ), tags=(quality_tag,))

        total_display = len(filtered)
        if use_session:
            stats_var.set(f"本次: {total_display} 条")
        else:
            stats_var.set(f"总计: {total_display} 条")

    global gui_fish_update_callback
    def safe_update():
        try:
            root.after(0, update_fish_display)
        except Exception as e:
            print(f"❌ [错误] GUI更新失败: {e}")

    gui_fish_update_callback = safe_update

    @safe_execute("清空钓鱼记录", None)
    def clear_fish_records():
        """清空钓鱼记录"""
        use_session = (view_mode.get() == "current")
        if use_session:
            confirm_text = "确定要清空本次钓鱼记录吗？"
        else:
            confirm_text = "确定要清空所有历史钓鱼记录吗？此操作不可恢复！"
        
        result = messagebox.askyesno("确认清空", confirm_text, parent=root)
        if not result:
            return
        
        if use_session:
            fish_records.clear_current_session()
        else:
            fish_records.clear_all_records()
            try:
                with open(FISH_RECORD_FILE, "w", encoding="utf-8") as f:
                    f.write("")
            except Exception as e:
                print(f"❌ [错误] 清空记录文件失败: {e}")
        
        update_fish_display()
    
    update_fish_display()
    
    # =========================
    # 运行日志显示区域
    # =========================
    log_card = ttkb.Labelframe(
        right_panel,
        text=" 📝 运行日志 ",
        padding=12,
        bootstyle="secondary"
    )
    log_card.pack(fill=BOTH, expand=YES, pady=(8, 0))
    
    # 创建日志文本组件
    log_frame = ttkb.Frame(log_card)
    log_frame.pack(fill=BOTH, expand=YES)
    
    log_text = tk.Text(
        log_frame,
        wrap="word",
        font=("Consolas", calculate_font_size(9)),
        bg="#1e1e1e",
        fg="#d4d4d4",
        insertbackground="white",
        height=12
    )
    
    # 绑定日志文本滚轮事件
    log_text.bind("<MouseWheel>", on_log_mousewheel)
    log_text.bind("<Enter>", lambda e: log_text.focus_set())
    
    # 添加滚动条
    log_scrollbar = ttkb.Scrollbar(log_frame, orient="vertical", command=log_text.yview, bootstyle="rounded")
    log_text.configure(yscrollcommand=log_scrollbar.set)
    
    log_text.pack(side=LEFT, fill=BOTH, expand=YES)
    log_scrollbar.pack(side=RIGHT, fill=Y)
    
    # 配置日志文本样式
    log_text.tag_configure("info", foreground="#4ec9b0")       # 信息 - 青色
    log_text.tag_configure("success", foreground="#4ec9b0")    # 成功 - 绿色
    log_text.tag_configure("warning", foreground="#dcdcaa")    # 警告 - 黄色
    log_text.tag_configure("error", foreground="#f48771")      # 错误 - 红色
    log_text.tag_configure("time", foreground="#569cd6")       # 时间 - 蓝色
    log_text.tag_configure("action", foreground="#c586c0")     # 动作 - 紫色
    log_text.tag_configure("system", foreground="#d4d4d4")     # 系统 - 白色
    log_text.tag_configure("debug", foreground="#9cdcfe")      # 调试 - 浅蓝
    
    # 将日志文本组件绑定到日志管理器
    log_manager.log_text_widget = log_text
    
    # 创建控制按钮栏
    log_control_frame = ttkb.Frame(log_card)
    log_control_frame.pack(fill=X, pady=(8, 0))
    
    # 日志级别选择
    log_level_var = ttkb.StringVar(value="all")
    log_level_frame = ttkb.Frame(log_control_frame)
    log_level_frame.pack(side=LEFT)
    
    ttkb.Label(log_level_frame, text="日志级别:").pack(side=LEFT, padx=(0, 5))
    
    log_level_combo = ttkb.Combobox(
        log_level_frame,
        textvariable=log_level_var,
        values=["all", "info", "warning", "error"],
        width=8,
        state="readonly"
    )
    log_level_combo.pack(side=LEFT)
    log_level_combo.bind("<<ComboboxSelected>>", lambda e: update_log_level())
    
    # 保存变量供函数使用
    update_log_level._log_level_var = log_level_var
    
    # 控制按钮
    log_btn_frame = ttkb.Frame(log_control_frame)
    log_btn_frame.pack(side=RIGHT)
    
    clear_log_btn = ttkb.Button(
        log_btn_frame,
        text="🚮 清空",
        command=clear_logs,
        bootstyle="danger-outline",
        width=8
    )
    clear_log_btn.pack(side=LEFT, padx=2)
    
    pause_log_btn = ttkb.Button(
        log_btn_frame,
        text="⏸️ 暂停",
        command=toggle_log_pause,
        bootstyle="warning-outline",
        width=8
    )
    pause_log_btn.pack(side=LEFT, padx=2)
    
    # 保存按钮引用供函数使用
    toggle_log_pause._pause_btn = pause_log_btn
    
    export_log_btn = ttkb.Button(
        log_btn_frame,
        text="📤 导出",
        command=export_logs,
        bootstyle="info-outline",
        width=8
    )
    export_log_btn.pack(side=LEFT, padx=2)
    
    auto_scroll_var = ttkb.BooleanVar(value=True)
    auto_scroll_check = ttkb.Checkbutton(
        log_btn_frame,
        text="自动滚动",
        variable=auto_scroll_var,
        bootstyle="info",
        width=10
    )
    auto_scroll_check.pack(side=LEFT, padx=2)
    
    # 将自动滚动变量绑定到日志管理器
    log_manager.set_auto_scroll_var(auto_scroll_var)
    
    # 加载历史日志
    log_manager.load_history_to_gui()

    # 初始化字体样式
    update_all_widget_fonts(root, style)
    
    class DummyEvent:
        def __init__(self, width):
            self.width = width
    
    on_window_resize(DummyEvent(root.winfo_width()))
    
    def on_closing():
        """窗口关闭事件处理"""
        if messagebox.askokcancel("退出", "确定要退出PartyFish吗？"):
            cleanup_resources()
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\n\n🛑 [中断] 用户中断程序")
        cleanup_resources()
    except Exception as e:
        print(f"❌ [错误] GUI运行异常: {e}")
        cleanup_resources()

# =========================
# 主循环和线程函数
# =========================
# 全局事件
run_event = threading.Event()
begin_event = threading.Event()

# 全局变量
previous_result = None
current_result = 0
a = 0
result_val_is = None
scr = None
jiashi_var = 0
_cached_scale_x = None
_cached_scale_y = None

def compare_results():
    """比较数字大小"""
    global current_result, previous_result
    if current_result is None or previous_result is None:
        return 0
    if current_result > previous_result:
        return 1
    elif current_result < previous_result:
        return -1
    else:
        return 0

def toggle_run():
    """增强版的启动/暂停切换，带状态验证"""
    global a, previous_result, is_toggling
    
    # 防止重复触发
    if hasattr(toggle_run, '_toggling') and toggle_run._toggling:
        return
    
    toggle_run._toggling = True
    try:
        if run_event.is_set():
            # ===== 安全暂停 =====
            print("⏸️  正在安全暂停...")
            
            # 1. 先清除事件
            run_event.clear()
            
            # 2. 等待当前操作完成（如果有）
            time.sleep(0.1)
            
            # 3. 确保鼠标抬起
            mouse_controller.ensure_up()
            
            # 4. 重置状态
            a = 0
            previous_result = None
            
            # 5. 结束会话
            end_current_session()
            
            print("✅ 已安全暂停")
            
        else:
            # ===== 安全启动 =====
            print("▶️  正在安全启动...")
            
            # 1. 先确保所有状态已重置
            mouse_controller.ensure_up()
            a = 0
            
            # 2. 开始新会话
            start_new_session()
            
            # 3. 初始化鱼饵识别
            with MSSContext() as temp_scr:
                bait_result = bait_math_val(temp_scr)
                if bait_result is not None:
                    previous_result = bait_result
                    # 4. 最后才设置事件
                    run_event.set()
                    print("✅ 已安全启动")
                else:
                    print("⚠️  未识别到鱼饵，启动失败")
                    time.sleep(0.5)  # 短暂延迟后允许重试
                    
    finally:
        toggle_run._toggling = False

@safe_execute("安全的主循环", None)
def safe_main_loop():
    """安全的主循环"""
    global previous_result, current_result, a
    
    while not begin_event.is_set():
        if run_event.is_set():
            with MSSContext() as scr:
                try:
                    if check_fishing_status(scr, "f1"):
                        cast_rod_with_jitter("F1")
                        time.sleep(0.15)
                    elif check_fishing_status(scr, "f2"):
                        cast_rod_with_jitter("F2")
                        time.sleep(0.15)
                    elif check_fishing_status(scr, "shangyu"):
                        mouse_controller.click()
                    
                    time.sleep(0.05)
                    
                    bait_result = bait_math_val(scr)
                    if bait_result is not None:
                        current_result = bait_result
                    else:
                        current_result = previous_result
                        time.sleep(0.1)
                        continue
                    
                    if previous_result is None:
                        previous_result = current_result
                    elif current_result < previous_result:
                        previous_result = current_result
                        
                        while not check_fishing_status(scr, "star") and run_event.is_set():
                            with param_lock:
                                current_times = times
                            
                            if a <= current_times:
                                a += 1
                                mouse_controller.press_and_release(leftclickdown, leftclickup)
                            else:
                                a = 0
                                print("🎣 [提示] 达到最大拉杆次数，本轮结束")
                                break
                        
                        mouse_controller.ensure_up()
                        a = 0
                        
                        if OCR_AVAILABLE and record_fish_enabled:
                            try:
                                record_caught_fish()
                            except Exception as e:
                                print(f"⚠️  [警告] 记录鱼信息失败: {e}")
                    elif current_result > previous_result:
                        previous_result = current_result
                        
                except Exception as e:
                    print(f"❌ [错误] 主循环异常: {e}")
                    if debug_mode:
                        add_debug_info({
                            "timestamp": datetime.datetime.now().strftime("%Y-%m-d %H:%M:%S.%f")[:-3],
                            "action": "main_loop_error",
                            "error": str(e),
                            "traceback": traceback.format_exc()
                        })
        
        time.sleep(0.1)

@safe_execute("安全的加时处理线程", None)
def safe_jiashi_thread():
    """安全的加时处理线程"""
    global previous_result
    
    while not begin_event.is_set():
        if run_event.is_set():
            with MSSContext() as scr:
                try:
                    with param_lock:
                        current_jiashi = jiashi_var
                    
                    if current_jiashi == 0 or current_jiashi == 1:
                        if fangzhu_jiashi(scr):
                            if current_jiashi == 0:
                                btn_x, btn_y = scale_point_center_anchored(*BTN_NO_JIASHI_BASE)
                            else:
                                btn_x, btn_y = scale_point_center_anchored(*BTN_YES_JIASHI_BASE)
                            
                            mouse_controller.click(btn_x, btn_y)
                            
                            bait_result = bait_math_val(scr)
                            if bait_result is not None:
                                with param_lock:
                                    previous_result = bait_result
                                    
                except Exception as e:
                    print(f"❌ [错误] 加时线程异常: {e}")
        
        time.sleep(0.05)

def cleanup_resources():
    """清理所有资源"""
    print("🧹 [清理] 正在清理资源...")
    
    hotkey_manager.stop()
    
    begin_event.set()
    run_event.clear()
    
    template_cache.clear_cache()
    
    end_current_session()
    
    try:
        save_parameters()
    except:
        pass
    
    print("✅ [清理] 资源清理完成")

# =========================
# 程序入口点
# =========================
if __name__ == "__main__":
    try:
        print()
        print("╔" + "═" * 50 + "╗")
        print("║" + " " * 50 + "║")
        print("║     🎣  PartyFish 自动钓鱼助手  v2.9     ║")
        print("║" + " " * 50 + "║")
        print("╠" + "═" * 50 + "╣")
        
        load_parameters()
        
        CURRENT_SCREEN_WIDTH, CURRENT_SCREEN_HEIGHT = get_current_screen_resolution()
        print(f"║  📺 当前分辨率: {CURRENT_SCREEN_WIDTH}×{CURRENT_SCREEN_HEIGHT}".ljust(45)+"║")
        print(f"║  ⌨️ 快捷键: {hotkey_name}启动/暂停脚本".ljust(42)+"║")
        print(f"║  🎲 时间抖动: ±{JITTER_RANGE}%".ljust(42)+"   ║")
        print("║  🔧 开发者: FadedTUMI/PeiXiaoXiao/MaiDong        ║")
        print("╚" + "═" * 50 + "╝")
        print()
        
        print("📊 [初始化] 正在加载钓鱼记录...")
        load_all_fish_records()
        
        print("🖼️  [初始化] 正在预加载模板...")
        for digit in range(10):
            template_cache.get_template(str(digit), SCALE_UNIFORM, SCALE_UNIFORM)
        for template in ["star", "F1", "F2", "shangyu", "chang"]:
            template_cache.get_template(template, SCALE_UNIFORM, SCALE_UNIFORM)
        print("✅ [初始化] 模板预加载完成")
        
        print("🎮 [初始化] 正在启动热键监听...")
        hotkey_manager.start()
        print("✅ [初始化] 热键监听已启动")
        
        print("⏱️  [初始化] 正在启动加时处理线程...")
        jiashi_thread = threading.Thread(target=safe_jiashi_thread, daemon=True)
        jiashi_thread.start()
        print("✅ [初始化] 加时处理线程已启动")
        
        print("🔄 [初始化] 正在启动主循环线程...")
        main_thread = threading.Thread(target=safe_main_loop, daemon=True)
        main_thread.start()
        print("✅ [初始化] 主循环线程已启动")
        
        print()
        print("┌" + "─" * 48 + "┐")
        print(f"│  🚀 程序已就绪，按 {hotkey_name} 开始自动钓鱼！".ljust(34) + "│")
        print("└" + "─" * 48 + "┘")
        print()
        
        create_gui()
        
    except Exception as e:
        print(f"❌ [错误] 程序启动失败: {e}")
        traceback.print_exc()
    finally:
        cleanup_resources()
        print("\n👋 [退出] 程序已安全退出")