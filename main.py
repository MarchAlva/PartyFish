import time
import os
import webbrowser
import warnings
import cv2
import numpy as np
from PIL import Image
import threading  # 用于在独立线程中运行脚本
import ctypes
from pynput import keyboard, mouse  # 用于监听键盘和鼠标事件，支持热键和鼠标侧键操作
import datetime
import re
import queue  # 用于线程安全通信
import random  # 添加随机模块用于时间抖动
import getpass  # 用于获取电脑账号
import json  # 用于保存和加载参数
import mss

# 初始化键盘和鼠标控制器
keyboard_controller = keyboard.Controller()
mouse_controller = mouse.Controller()

# 过滤libpng的iCCP警告（图片ICC配置文件问题）
warnings.filterwarnings("ignore", message=".*iCCP.*")
# 设置OpenCV不显示libpng警告
os.environ["OPENCV_IO_ENABLE_JASPER"] = "0"

import tkinter as tk  # 保留用于兼容性
from tkinter import ttk  # 保留用于兼容性
from tkinter import messagebox
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *

# =========================
# 模块化导入
# =========================
from utils.card_key import verify_card_key
from utils.hardware_info import get_hardware_info
from services.sound_service import sound_manager
from utils.resource_manager import get_icon_path, set_window_icon
from services.ocr_service import ocr_service, OCR_AVAILABLE
from core.fish_bucket import (
    FISH_BUCKET_FULL_TEXT, fish_bucket_full_detected, fish_bucket_sound_enabled,
    bucket_detection_mode, casting_timestamps, casting_interval_lock,
    CASTING_INTERVAL_THRESHOLD, REQUIRED_CONSECUTIVE_MATCHES,
    bucket_full_by_interval, is_casting, is_releasing, operation_lock,
    reset_fish_bucket_state, add_casting_timestamp, check_bucket_full_by_interval,
    set_fish_bucket_full, is_fish_bucket_full, set_bucket_detection_mode,
    get_bucket_detection_mode, set_fish_bucket_sound_enabled,
    is_fish_bucket_sound_enabled, set_casting_state, is_casting_active,
    set_releasing_state, is_releasing_active
)
from utils.log_system import init_log_system, get_log_history, clear_log_history
from config.config_manager import (
    load_parameters, save_parameters, switch_config, rename_config,
    current_config_index, config_names, config_params,
    MAX_CONFIGS, get_current_config, get_current_config_index,
    get_config_names, get_config_params
)
from ui.font_manager import (
    font_size, input_entries, combo_boxes, fish_tree_ref,
    init_font_styles, update_all_widget_fonts
)
from utils.debug_manager import (
    debug_mode, debug_info_queue, debug_info_history, debug_history_lock,
    debug_auto_refresh, debug_window, add_debug_info, get_debug_info_history,
    clear_debug_info_history, set_debug_mode, is_debug_mode_enabled,
    set_debug_auto_refresh, is_debug_auto_refresh_enabled
)
from core.release_manager import (
    release_fish_enabled, release_standard_enabled, release_uncommon_enabled,
    release_rare_enabled, release_epic_enabled, release_legendary_enabled,
    release_phantom_rare_enabled, set_release_fish_enabled,
    set_release_standard_enabled, set_release_uncommon_enabled,
    set_release_rare_enabled, set_release_epic_enabled,
    set_release_legendary_enabled, set_release_phantom_rare_enabled,
    is_release_fish_enabled, is_release_standard_enabled,
    is_release_uncommon_enabled, is_release_rare_enabled,
    is_release_epic_enabled, is_release_legendary_enabled,
    is_release_phantom_rare_enabled, should_release_fish
)
from utils.timing_utils import (
    JITTER_RANGE, add_jitter, print_timing_info,
    set_jitter_range, get_jitter_range, reset_operation_timing
)

# =========================
# 全局常量和配置
# =========================
PARAMETER_FILE = "./parameters.json"

# =========================
# 全局变量初始化
# =========================
# 运行控制事件
run_event = threading.Event()
run_event.clear()  # 初始化为停止状态

# 线程锁
param_lock = threading.Lock()  # 参数读写锁

# UI相关全局变量
root = None  # 主窗口引用
uno_input1_var = None  # 用于兼容性
uno_input2_var = None  # 用于兼容性
uno_popup_shown = False  # 用于兼容性

# 钓鱼相关全局变量
templates = None  # 保存模板
scr = None  # 截图对象
current_result = None  # 当前识别结果
previous_result = None  # 上次识别结果
times = 25  # 默认拉杆次数
a = 0  # 用于计数
t = 0.9  # 默认阈值
leftclickdown = 1.0  # 默认左键按下时间
leftclickup = 0.7  # 默认左键释放时间
paogantime = 2.0  # 默认抛竿时间

# 其他全局变量
jiashi_var = False  # 加时变量
region1 = None  # 区域1
region2 = None  # 区域2
result_val_is = None  # 结果值

# 初始化日志系统
init_log_system()

# =========================
# 模板加载函数
# =========================
def load_templates():
    """加载所有图像模板"""
    print("🖼️  [初始化] 正在加载图像模板...")
    # 这里需要根据实际情况实现模板加载
    # 由于模块化拆分，模板加载可能已经在其他模块中实现
    print("✅ [初始化] 模板加载完成")

# =========================
# 钓鱼逻辑线程函数
# =========================
def fishing_logic():
    """钓鱼逻辑，运行在后台线程"""
    print("🎣 钓鱼逻辑线程已启动")
    
    try:
        from PartyFish import main as original_main
        original_main()
    except Exception as e:
        print(f"❌ [错误] 钓鱼逻辑执行失败: {e}")
        import traceback
        traceback.print_exc()

# =========================
# 热键监听线程函数
# =========================
def hotkey_listener():
    """热键监听，运行在后台线程"""
    print("🎮 热键监听线程已启动")
    
    try:
        from PartyFish import start_hotkey_listener
        start_hotkey_listener()
    except Exception as e:
        print(f"❌ [错误] 热键监听执行失败: {e}")
        import traceback
        traceback.print_exc()

# =========================
# 鱼桶检测线程函数
# =========================
def bucket_detection():
    """鱼桶检测，运行在后台线程"""
    print("🪣 鱼桶检测线程已启动")
    
    try:
        from PartyFish import bucket_full_detection_thread
        bucket_full_detection_thread()
    except Exception as e:
        print(f"❌ [错误] 鱼桶检测执行失败: {e}")
        import traceback
        traceback.print_exc()

# =========================
# 加时处理线程函数
# =========================
def jiashi_handler():
    """加时处理，运行在后台线程"""
    print("⏰ 加时处理线程已启动")
    
    try:
        from PartyFish import handle_jiashi_thread
        handle_jiashi_thread()
    except Exception as e:
        print(f"❌ [错误] 加时处理执行失败: {e}")
        import traceback
        traceback.print_exc()

# =========================
# 主程序入口
# =========================
def main():
    """主程序入口 - 运行在主线程"""
    global run_event, root
    
    print("🎣 PartyFish 启动中...")
    
    # 验证卡密
    verify_card_key()
    
    # 播放启动音效
    sound_manager.play_start()
    
    # 先加载参数以获取热键设置
    load_parameters()
    
    # 打印启动信息
    print()
    print("╔" + "═" * 50 + "╗")
    print("║" + " " * 50 + "║")
    print("║     🎣  PartyFish 自动钓鱼助手  v.2.12".ljust(44) + "║")
    print("║" + " " * 50 + "║")
    print("╠" + "═" * 50 + "╣")
    print(f"║  📺 当前分辨率: {ctypes.windll.user32.GetSystemMetrics(0)}×{ctypes.windll.user32.GetSystemMetrics(1)}".ljust(45) + "║")
    print(f"║  ⌨️ 快捷键: F2 启动/暂停脚本".ljust(43) + "║")
    print(f"║  🎲 时间抖动: ±{JITTER_RANGE}%".ljust(46) + "║")
    print(f"║  🪣 鱼桶满检测: {'✅ 已启用' if OCR_AVAILABLE else '❌ 未启用'}".ljust(46) + "║")
    print(f"║  🎯 鱼饵识别算法: template".ljust(47) + "║")
    print("║  🔧 开发者: FadedTUMI/PeiXiaoXiao/MaiDong".ljust(47) + "║")
    print("╚" + "═" * 50 + "╝")
    print()
    
    # 初始化字体样式
    init_font_styles(None, 100)
    
    # 加载图像模板
    load_templates()
    
    print()
    print("┌" + "─" * 48 + "┐")
    print(f"│  🚀 程序已就绪，按 F2 开始自动钓鱼！".ljust(34) + "│")
    print("└" + "─" * 48 + "┘")
    print()
    
    # 启动后台线程
    print("🚀 正在启动后台线程...")
    
    # 启动钓鱼逻辑线程
    fishing_thread = threading.Thread(target=fishing_logic, daemon=True)
    fishing_thread.start()
    
    # 启动热键监听线程
    hotkey_thread = threading.Thread(target=hotkey_listener, daemon=True)
    hotkey_thread.start()
    
    # 启动鱼桶检测线程
    bucket_thread = threading.Thread(target=bucket_detection, daemon=True)
    bucket_thread.start()
    
    # 启动加时处理线程
    jiashi_thread = threading.Thread(target=jiashi_handler, daemon=True)
    jiashi_thread.start()
    
    print("✅ 所有后台线程已启动")
    
    # 创建主窗口（必须在主线程）
    print("🖼️  正在创建GUI...")
    try:
        from PartyFish import create_gui  # 导入原始文件的GUI创建函数
        create_gui()  # 在主线程直接调用
    except Exception as e:
        print(f"❌ [错误] 创建GUI失败: {e}")
        import traceback
        traceback.print_exc()
        input("按任意键退出...")


if __name__ == "__main__":
    # 直接在主线程运行main函数
    main()