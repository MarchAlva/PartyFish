# 放生功能设置
release_fish_enabled = False  # 是否启用放生功能
release_standard_enabled = False  # 是否放生标准鱼
release_uncommon_enabled = False  # 是否放生非凡鱼
release_rare_enabled = False  # 是否放生稀有鱼
release_epic_enabled = False  # 是否放生史诗鱼
release_legendary_enabled = False  # 是否放生传奇鱼
release_phantom_rare_enabled = False  # 是否放生幻神稀有鱼


def set_release_fish_enabled(enabled: bool):
    """设置是否启用放生功能
    
    Args:
        enabled: 是否启用放生功能
    """
    global release_fish_enabled
    release_fish_enabled = enabled


def is_release_fish_enabled() -> bool:
    """检查是否启用放生功能
    
    Returns:
        bool: 是否启用放生功能
    """
    return release_fish_enabled


def set_release_standard_enabled(enabled: bool):
    """设置是否放生标准鱼
    
    Args:
        enabled: 是否放生标准鱼
    """
    global release_standard_enabled
    release_standard_enabled = enabled


def is_release_standard_enabled() -> bool:
    """检查是否放生标准鱼
    
    Returns:
        bool: 是否放生标准鱼
    """
    return release_standard_enabled


def set_release_uncommon_enabled(enabled: bool):
    """设置是否放生非凡鱼
    
    Args:
        enabled: 是否放生非凡鱼
    """
    global release_uncommon_enabled
    release_uncommon_enabled = enabled


def is_release_uncommon_enabled() -> bool:
    """检查是否放生非凡鱼
    
    Returns:
        bool: 是否放生非凡鱼
    """
    return release_uncommon_enabled


def set_release_rare_enabled(enabled: bool):
    """设置是否放生稀有鱼
    
    Args:
        enabled: 是否放生稀有鱼
    """
    global release_rare_enabled
    release_rare_enabled = enabled


def is_release_rare_enabled() -> bool:
    """检查是否放生稀有鱼
    
    Returns:
        bool: 是否放生稀有鱼
    """
    return release_rare_enabled


def set_release_epic_enabled(enabled: bool):
    """设置是否放生史诗鱼
    
    Args:
        enabled: 是否放生史诗鱼
    """
    global release_epic_enabled
    release_epic_enabled = enabled


def is_release_epic_enabled() -> bool:
    """检查是否放生史诗鱼
    
    Returns:
        bool: 是否放生史诗鱼
    """
    return release_epic_enabled


def set_release_legendary_enabled(enabled: bool):
    """设置是否放生传奇鱼
    
    Args:
        enabled: 是否放生传奇鱼
    """
    global release_legendary_enabled
    release_legendary_enabled = enabled


def is_release_legendary_enabled() -> bool:
    """检查是否放生传奇鱼
    
    Returns:
        bool: 是否放生传奇鱼
    """
    return release_legendary_enabled


def set_release_phantom_rare_enabled(enabled: bool):
    """设置是否放生幻神稀有鱼
    
    Args:
        enabled: 是否放生幻神稀有鱼
    """
    global release_phantom_rare_enabled
    release_phantom_rare_enabled = enabled


def is_release_phantom_rare_enabled() -> bool:
    """检查是否放生幻神稀有鱼
    
    Returns:
        bool: 是否放生幻神稀有鱼
    """
    return release_phantom_rare_enabled


def should_release_fish(rarity: str) -> bool:
    """检查是否应该放生某种稀有度的鱼
    
    Args:
        rarity: 鱼的稀有度
        
    Returns:
        bool: 是否应该放生
    """
    if not release_fish_enabled:
        return False
    
    rarity = rarity.lower()
    
    if "标准" in rarity:
        return release_standard_enabled
    elif "非凡" in rarity:
        return release_uncommon_enabled
    elif "稀有" in rarity:
        return release_rare_enabled
    elif "史诗" in rarity:
        return release_epic_enabled
    elif "传奇" in rarity:
        return release_legendary_enabled
    elif "幻神" in rarity:
        return release_phantom_rare_enabled
    
    return False
