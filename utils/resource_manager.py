import os
import sys
import tkinter as tk


def get_icon_path():
    """获取logo.ico图标的路径，处理不同环境下的路径问题

    Returns:
        str: logo.ico图标的完整路径
    """
    if hasattr(sys, "_MEIPASS"):
        # 打包后直接在MEIPASS下查找
        icon_path = os.path.join(sys._MEIPASS, "logo.ico")
    else:
        # 开发环境下直接使用当前目录
        icon_path = "logo.ico"

    return icon_path



def get_resources_path():
    """获取resources目录的路径，处理不同环境下的路径问题

    Returns:
        str: resources目录的完整路径
    """
    if hasattr(sys, "_MEIPASS"):
        # 打包后resources目录在MEIPASS下
        resources_path = os.path.join(sys._MEIPASS, "resources")
    else:
        # 开发环境下直接使用当前目录下的resources
        resources_path = os.path.join(".", "resources")

    return resources_path



def set_window_icon(window):
    """设置窗口图标，同时支持窗口和任务栏

    Args:
        window: 要设置图标的窗口对象
    """
    try:
        # 获取图标路径
        icon_path = get_icon_path()

        # 尝试使用iconphoto方法设置图标（同时支持窗口和任务栏）
        try:
            icon = tk.PhotoImage(file=icon_path)
            window.iconphoto(True, icon)
        except Exception as e1:
            # 如果iconphoto失败，尝试回退到iconbitmap
            try:
                window.iconbitmap(icon_path)
            except Exception as e2:
                print(f"⚠️  [警告] 设置窗口图标失败: {e2}")
    except Exception as e:
        print(f"⚠️  [警告] 设置窗口图标时发生错误: {e}")
