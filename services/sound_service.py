import threading

# 尝试导入音效库
try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False
    print("⚠️  [警告] 无法导入winsound，部分音效可能不可用")


class SimpleSoundManager:
    """简化版音效管理器，只使用winsound和控制台铃声"""

    def __init__(self):
        self.enabled = True
        self.can_use_winsound = False
        self._playing = False  # 防止重复播放
        self._lock = threading.Lock()  # 线程锁

        try:
            import winsound
            self.can_use_winsound = True
            print("🔊 [音效] 使用winsound播放音效")
        except ImportError:
            print("🔊 [音效] 使用控制台铃声")

    def _safe_beep(self, frequency, duration):
        """安全的蜂鸣函数"""
        if not self.enabled:
            return

        try:
            if self.can_use_winsound:
                import winsound
                winsound.Beep(frequency, duration)
            else:
                print("\a", end="", flush=True)
        except:
            # 音效失败时静默处理
            pass

    def play_start(self):
        """播放启动音效"""
        with self._lock:
            if not self.enabled or self._playing:
                return
            self._playing = True

        # 在独立线程中播放，避免阻塞
        def _play():
            try:
                self._safe_beep(1000, 200)
                threading.Event().wait(0.05)
                self._safe_beep(1200, 150)
            finally:
                with self._lock:
                    self._playing = False

        threading.Thread(target=_play, daemon=True).start()

    def play_pause(self):
        """播放暂停音效"""
        with self._lock:
            if not self.enabled or self._playing:
                return
            self._playing = True

        def _play():
            try:
                self._safe_beep(600, 200)
                threading.Event().wait(0.05)
                self._safe_beep(500, 150)
            finally:
                with self._lock:
                    self._playing = False

        threading.Thread(target=_play, daemon=True).start()

    def play_resume(self):
        """播放恢复音效"""
        with self._lock:
            if not self.enabled or self._playing:
                return
            self._playing = True

        def _play():
            try:
                self._safe_beep(800, 200)
                threading.Event().wait(0.05)
                self._safe_beep(900, 150)
            finally:
                with self._lock:
                    self._playing = False

        threading.Thread(target=_play, daemon=True).start()


# 使用简化版
sound_manager = SimpleSoundManager()
