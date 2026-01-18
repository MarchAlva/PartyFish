import hashlib
from functools import lru_cache
from typing import Tuple, Optional

# 尝试导入OCR引擎
try:
    from rapidocr_onnxruntime import RapidOCR
    
    ocr_engine = RapidOCR()
    OCR_AVAILABLE = True
    print("✅ [OCR] RapidOCR 引擎加载成功")
except ImportError:
    OCR_AVAILABLE = False
    ocr_engine = None
    print("⚠️  [OCR] RapidOCR 未安装，钓鱼记录功能将不可用")


class OCRService:
    """OCR服务类，提供OCR识别功能，并带有LRU缓存机制"""
    
    def __init__(self, cache_size: int = 1000):
        """初始化OCR服务
        
        Args:
            cache_size: LRU缓存大小，默认1000条
        """
        self.cache_size = cache_size
        self._setup_cache()
    
    def _setup_cache(self):
        """设置LRU缓存"""
        # 定义带LRU缓存的OCR识别方法
        @lru_cache(maxsize=self.cache_size)
        def _cached_ocr(image_hash: str, image_data):
            """带缓存的OCR识别方法
            
            Args:
                image_hash: 图像数据的哈希值，用于缓存key
                image_data: 图像数据
                
            Returns:
                OCR识别结果
            """
            if not OCR_AVAILABLE or ocr_engine is None:
                return None
            
            try:
                result = ocr_engine(image_data)
                return result
            except Exception as e:
                print(f"❌ [OCR] 识别失败: {e}")
                return None
        
        self._cached_ocr = _cached_ocr
    
    def _compute_image_hash(self, image_data) -> str:
        """计算图像数据的哈希值
        
        Args:
            image_data: 图像数据
            
        Returns:
            图像数据的MD5哈希值
        """
        # 将图像数据转换为bytes
        if hasattr(image_data, 'tobytes'):
            image_bytes = image_data.tobytes()
        else:
            # 如果是numpy数组
            import numpy as np
            if isinstance(image_data, np.ndarray):
                image_bytes = image_data.tobytes()
            else:
                # 直接转换为str并哈希
                image_bytes = str(image_data).encode('utf-8')
        
        # 计算MD5哈希值
        return hashlib.md5(image_bytes).hexdigest()
    
    def recognize(self, image_data) -> Optional[list]:
        """执行OCR识别，带有LRU缓存
        
        Args:
            image_data: 图像数据，可以是numpy数组或其他图像格式
            
        Returns:
            OCR识别结果，如果识别失败返回None
        """
        if not OCR_AVAILABLE or ocr_engine is None:
            return None
        
        # 计算图像哈希值
        image_hash = self._compute_image_hash(image_data)
        
        # 使用缓存的OCR识别方法
        result = self._cached_ocr(image_hash, image_data)
        
        return result
    
    def clear_cache(self):
        """清除OCR缓存"""
        self._cached_ocr.cache_clear()
        print("🗑️  [OCR] 缓存已清除")
    
    def get_cache_info(self) -> dict:
        """获取缓存信息
        
        Returns:
            缓存信息字典，包含命中次数、未命中次数、最大大小、当前大小
        """
        cache_info = self._cached_ocr.cache_info()
        return {
            'hits': cache_info.hits,
            'misses': cache_info.misses,
            'maxsize': cache_info.maxsize,
            'currsize': cache_info.currsize
        }


# 创建OCR服务实例
ocr_service = OCRService()
