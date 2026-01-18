import getpass

# 尝试导入硬件信息相关库
try:
    import wmi
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False
    print("⚠️  [警告] 无法导入wmi，硬件信息获取可能受限")

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️  [警告] 无法导入psutil，硬件信息获取可能受限")


def get_hardware_info():
    """
    获取硬件信息，包括CPU型号、CPU序列号、GPU型号和电脑账号
    返回格式化的硬件信息字符串
    """
    hardware_info = {}
    
    # 获取电脑账号
    try:
        hardware_info['username'] = getpass.getuser()
    except Exception as e:
        hardware_info['username'] = f"获取失败: {e}"
    
    # 获取CPU信息
    try:
        if WMI_AVAILABLE:
            w = wmi.WMI()
            for processor in w.Win32_Processor():
                hardware_info['cpu_model'] = processor.Name.strip()
                break
        else:
            hardware_info['cpu_model'] = "获取失败: wmi不可用"
    except Exception as e:
        hardware_info['cpu_model'] = f"获取失败: {e}"
    
    # 获取CPU序列号
    try:
        if WMI_AVAILABLE:
            w = wmi.WMI()
            for processor in w.Win32_Processor():
                hardware_info['cpu_serial'] = processor.ProcessorId.strip()
                break
        else:
            hardware_info['cpu_serial'] = "获取失败: wmi不可用"
    except Exception as e:
        hardware_info['cpu_serial'] = f"获取失败: {e}"
    
    # 获取内存信息
    try:
        if PSUTIL_AVAILABLE:
            total_memory = psutil.virtual_memory().total
            # 转换为GB
            total_memory_gb = round(total_memory / (1024 ** 3), 2)
            hardware_info['memory'] = f"{total_memory_gb} GB"
        else:
            hardware_info['memory'] = "获取失败: psutil不可用"
    except Exception as e:
        hardware_info['memory'] = f"获取失败: {e}"
    
    # 获取硬盘信息
    try:
        if WMI_AVAILABLE:
            w = wmi.WMI()
            disk_info = []
            for disk in w.Win32_DiskDrive():
                if disk.Model:
                    disk_info.append(disk.Model.strip())
            hardware_info['disk'] = ", ".join(disk_info) if disk_info else "未知"
        else:
            hardware_info['disk'] = "获取失败: wmi不可用"
    except Exception as e:
        hardware_info['disk'] = f"获取失败: {e}"
    
    # 获取网卡信息
    try:
        if PSUTIL_AVAILABLE:
            net_if_addrs = psutil.net_if_addrs()
            mac_addresses = []
            for interface_name, addresses in net_if_addrs.items():
                for address in addresses:
                    if address.family == psutil.AF_LINK:
                        mac_addresses.append(address.address)
            hardware_info['network'] = ", ".join(mac_addresses) if mac_addresses else "未知"
        else:
            hardware_info['network'] = "获取失败: psutil不可用"
    except Exception as e:
        hardware_info['network'] = f"获取失败: {e}"
    
    # 获取GPU信息
    try:
        if WMI_AVAILABLE:
            w = wmi.WMI()
            gpu_info = []
            for gpu in w.Win32_VideoController():
                if gpu.Name:
                    gpu_info.append(gpu.Name.strip())
            hardware_info['gpu_model'] = ", ".join(gpu_info) if gpu_info else "未知"
        else:
            hardware_info['gpu_model'] = "获取失败: wmi不可用"
    except Exception as e:
        hardware_info['gpu_model'] = f"获取失败: {e}"
    
    # 格式化硬件信息字符串，按照顺序：cpu|内存|硬盘|网卡|gpu型号
    # 保留username和cpu_serial作为前两个字段，保持与现有逻辑兼容
    hardware_str = f"{hardware_info['username']}|{hardware_info['cpu_model']}|{hardware_info['memory']}|{hardware_info['disk']}|{hardware_info['network']}|{hardware_info['gpu_model']}"
    return hardware_str
