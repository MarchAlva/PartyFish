import json
import threading

# 参数文件路径
PARAMETER_FILE = "./parameters.json"

# 配置只管理5个核心钓鱼参数：t, leftclickdown, leftclickup, times, paogantime
# 其他参数保持全局设置，不受配置切换影响

# 配置数量限制
MAX_CONFIGS = 4

# 当前配置索引（0-3）
current_config_index = 0

# 配置名称
config_names = ["配置1", "配置2", "配置3", "配置4"]

# 配置参数，保存5个核心钓鱼参数
config_params = [
    # 配置1
    {"t": 0.9, "leftclickdown": 1, "leftclickup": 0.7, "times": 25, "paogantime": 2},
    # 配置2
    {
        "t": 0.5,
        "leftclickdown": 0.9,
        "leftclickup": 0.5,
        "times": 25,
        "paogantime": 3,
    },
    # 配置3
    {
        "t": 0.2,
        "leftclickdown": 0.4,
        "leftclickup": 0.2,
        "times": 25,
        "paogantime": 0.1,
    },
    # 配置4
    {
        "t": 0.2,
        "leftclickdown": 1.5,
        "leftclickup": 1.0,
        "times": 25,
        "paogantime": 0.1,
    },
]


# 线程锁 - 保护共享变量
param_lock = threading.Lock()  # 参数读写锁


def save_parameters(t, leftclickdown, leftclickup, times, paogantime, other_params=None):
    """保存参数到文件
    
    Args:
        t: 循环间隔
        leftclickdown: 收线时间
        leftclickup: 放线时间
        times: 最大拉杆次数
        paogantime: 抛竿时间
        other_params: 其他参数字典
    """
    # 保存当前配置的核心参数
    config_params[current_config_index] = {
        "t": t,
        "leftclickdown": leftclickdown,
        "leftclickup": leftclickup,
        "times": times,
        "paogantime": paogantime,
    }

    params = {
        # 保存配置信息
        "config_names": config_names,
        "config_params": config_params,
        "current_config_index": current_config_index,
        # 保存全局参数（不受配置切换影响）
        **(other_params or {})
    }
    
    try:
        with open(PARAMETER_FILE, "w", encoding="utf-8") as f:
            json.dump(params, f)
        print("💾 [保存] 参数已成功保存到文件")
    except Exception as e:
        print(f"❌ [错误] 保存参数失败: {e}")



def load_parameters():
    """从文件加载参数
    
    Returns:
        加载的参数字典
    """
    global current_config_index, config_names, config_params
    params = {}
    
    try:
        with open(PARAMETER_FILE, "r", encoding="utf-8") as f:
            params = json.load(f)

            # 加载配置信息
            if "config_names" in params:
                config_names = params["config_names"]
            if "config_params" in params:
                config_params = params["config_params"]
            if "current_config_index" in params:
                current_config_index = params["current_config_index"]
                
        print("📄 [加载] 参数加载成功")
    except FileNotFoundError:
        print("📄 [信息] 未找到参数文件，使用默认值")
    except Exception as e:
        print(f"❌ [错误] 加载参数失败: {e}")
    
    return params



def switch_config(index):
    """切换配置，只更新5个核心钓鱼参数
    
    Args:
        index: 配置索引
        
    Returns:
        是否切换成功
    """
    global current_config_index

    if index < 0 or index >= MAX_CONFIGS:
        return False

    # 切换到新配置
    current_config_index = index

    # 保存参数
    save_parameters(
        t=config_params[current_config_index]["t"],
        leftclickdown=config_params[current_config_index]["leftclickdown"],
        leftclickup=config_params[current_config_index]["leftclickup"],
        times=config_params[current_config_index]["times"],
        paogantime=config_params[current_config_index]["paogantime"]
    )

    return True



def rename_config(index, new_name):
    """重命名配置
    
    Args:
        index: 配置索引
        new_name: 新名称
        
    Returns:
        是否重命名成功
    """
    global config_names
    if index < 0 or index >= MAX_CONFIGS:
        return False

    config_names[index] = new_name
    save_parameters(
        t=config_params[current_config_index]["t"],
        leftclickdown=config_params[current_config_index]["leftclickdown"],
        leftclickup=config_params[current_config_index]["leftclickup"],
        times=config_params[current_config_index]["times"],
        paogantime=config_params[current_config_index]["paogantime"]
    )
    return True



def get_current_config():
    """获取当前配置的核心参数
    
    Returns:
        当前配置的核心参数字典
    """
    return config_params[current_config_index]



def get_current_config_index():
    """获取当前配置索引
    
    Returns:
        当前配置索引
    """
    return current_config_index



def get_config_names():
    """获取配置名称列表
    
    Returns:
        配置名称列表
    """
    return config_names.copy()



def get_config_params():
    """获取配置参数列表
    
    Returns:
        配置参数列表
    """
    return config_params.copy()
