import json
import tkinter as tk
from tkinter import messagebox
from utils.hardware_info import get_hardware_info
from utils.resource_manager import set_window_icon

# 硬编码卡密
VALID_CARD_KEY = "免费软件倒卖全家死光光"

# 卡密信息保存键名
CARD_KEY_SAVE_KEY = "card_key"
HARDWARE_INFO_SAVE_KEY = "hardware_info"
PARAMETER_FILE = "./parameters.json"


def verify_card_key():
    """
    验证卡密，绑定硬件信息
    每次启动时调用，硬件信息不一致则需要重新输入卡密
    """
    # 先加载参数，获取保存的卡密和硬件信息
    load_parameters()
    
    # 获取当前硬件信息
    current_hardware = get_hardware_info()
    
    # 读取保存的卡密和硬件信息
    saved_card_key = None
    saved_hardware = None
    
    try:
        with open(PARAMETER_FILE, "r", encoding="utf-8") as f:
            params = json.load(f)
            saved_card_key = params.get(CARD_KEY_SAVE_KEY, None)
            saved_hardware = params.get(HARDWARE_INFO_SAVE_KEY, None)
    except Exception as e:
        print(f"⚠️  [警告] 读取卡密信息失败: {e}")
    
    # 检查是否需要重新输入卡密
    need_reinput = False
    if not saved_card_key:
        need_reinput = True
        print("🔑 [卡密] 首次启动，需要输入卡密")
    elif saved_hardware != current_hardware:
        need_reinput = True
        print("🔄 [卡密] 硬件信息已变更，需要重新输入卡密")
    
    # 需要重新输入卡密
    if need_reinput:
        # 创建卡密输入窗口
        def create_card_key_window():
            """创建卡密输入窗口"""
            # 创建临时根窗口
            temp_root = tk.Tk()
            temp_root.withdraw()  # 隐藏主窗口
            
            # 创建卡密输入对话框
            card_key = tk.StringVar()
            result = [False]  # 使用列表存储结果，以便在内部函数中修改
            
            def on_submit():
                """提交卡密"""
                input_card_key = card_key_entry.get().strip()
                if input_card_key == VALID_CARD_KEY:
                    result[0] = True
                    temp_root.quit()  # 退出对话框
                else:
                    messagebox.showerror("错误", "卡密错误，请重新输入！")
            
            def on_cancel():
                """取消输入"""
                temp_root.quit()  # 退出对话框
                exit()  # 退出程序
            
            # 创建对话框
            dialog = tk.Toplevel(temp_root)
            dialog.title("🔑 卡密验证")
            dialog.geometry("400x200")
            dialog.minsize(350, 180)
            dialog.resizable(False, False)  # 不允许调整大小
            
            # 设置窗口居中
            dialog.update_idletasks()
            width = dialog.winfo_width()
            height = dialog.winfo_height()
            x = (dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (dialog.winfo_screenheight() // 2) - (height // 2)
            dialog.geometry(f"{width}x{height}+{x}+{y}")
            
            # 设置窗口图标
            set_window_icon(dialog)
            
            # 创建对话框内容
            frame = tk.Frame(dialog, padx=20, pady=20)
            frame.pack(fill=tk.BOTH, expand=True)
            
            # 标题
            title_label = tk.Label(frame, text="请输入卡密", font=("Segoe UI", 14, "bold"))
            title_label.pack(pady=(0, 20))
            
            # 卡密输入框
            card_key_entry = tk.Entry(frame, textvariable=card_key, font=("Segoe UI", 12), width=30)
            card_key_entry.pack(pady=(0, 20))
            card_key_entry.focus_set()  # 设置焦点
            
            # 绑定回车键提交
            card_key_entry.bind("<Return>", lambda event: on_submit())
            
            # 按钮框架
            button_frame = tk.Frame(frame)
            button_frame.pack(fill=tk.X, pady=(0, 10))
            
            # 取消按钮
            cancel_btn = tk.Button(button_frame, text="取消", command=on_cancel, width=12)
            cancel_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            # 确定按钮
            submit_btn = tk.Button(button_frame, text="确定", command=on_submit, width=12)
            submit_btn.pack(side=tk.RIGHT)
            
            # 禁用关闭按钮
            def on_close():
                exit()  # 退出程序
            
            dialog.protocol("WM_DELETE_WINDOW", on_close)
            
            # 运行对话框
            temp_root.mainloop()
            
            # 销毁临时窗口
            temp_root.destroy()
            
            return card_key.get().strip() if result[0] else None
        
        # 运行卡密输入对话框
        input_card_key = create_card_key_window()
        
        if input_card_key:
            # 保存卡密和硬件信息
            try:
                # 读取现有参数
                with open(PARAMETER_FILE, "r", encoding="utf-8") as f:
                    params = json.load(f)
            except Exception:
                params = {}
            
            # 更新卡密和硬件信息
            params[CARD_KEY_SAVE_KEY] = input_card_key
            params[HARDWARE_INFO_SAVE_KEY] = current_hardware
            
            # 保存更新后的参数
            with open(PARAMETER_FILE, "w", encoding="utf-8") as f:
                json.dump(params, f)
            
            print("✅ [卡密] 验证成功！")
            print("💾 [卡密] 卡密和硬件信息已保存")
        else:
            print("❌ [卡密] 卡密验证失败，程序退出")
            exit()
    else:
        # 验证通过
        print("✅ [卡密] 卡密验证通过")


def load_parameters():
    """
    加载参数（简化版，只用于卡密验证模块）
    """
    pass
