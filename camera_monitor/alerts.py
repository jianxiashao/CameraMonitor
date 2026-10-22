"""画面异常判断：黑屏。

工程上只做抽样，不做整帧分析——25 路每路每秒几十帧，逐像素扫描会把 CPU 吃光。
相机断电、镜头被挡、夜间红外关闭时最常见的现象就是"连上了但一直是黑画面"，
以前只能靠人盯着看，现在由解码线程顺手报出来。
"""
# 三个通道之和低于这个值就算黑（0~765）
BLACK_LEVEL = 30
# 连续这么多帧都黑才告警：夜间车灯扫过、短暂遮挡不该报警
BLACK_FRAMES = 10
# 每帧最多取 8×8 个采样点
SAMPLE_STEPS = 8


def sample_is_black(plane, width, height, stride, level=BLACK_LEVEL):
    """抽样判断这一帧是不是基本全黑。plane 是 rgb24 的字节串。"""
    if width <= 0 or height <= 0 or not plane:
        return False
    if len(plane) < height * stride:
        # 缓冲不完整（多半是还没填满），别急着下结论
        return False
    step_x = max(1, width // SAMPLE_STEPS)
    step_y = max(1, height // SAMPLE_STEPS)
    samples = 0
    for y in range(0, height, step_y):
        row = y * stride
        for x in range(0, width, step_x):
            offset = row + x * 3
            if offset + 2 >= len(plane):
                continue
            samples += 1
            if plane[offset] + plane[offset + 1] + plane[offset + 2] > level:
                return False
    return samples > 0


class BlackScreenWatch:
    """连续若干帧全黑才报一次；恢复时也报一次。"""

    def __init__(self, frames=BLACK_FRAMES):
        self.frames = max(1, frames)
        self.dark = 0
        self.alerting = False

    def observe(self, black):
        """喂一帧的判断结果，返回 'alert' / 'clear' / None。"""
        if black:
            self.dark += 1
            if not self.alerting and self.dark >= self.frames:
                self.alerting = True
                return 'alert'
            return None
        self.dark = 0
        if self.alerting:
            self.alerting = False
            return 'clear'
        return None

    def reset(self):
        self.dark = 0
        self.alerting = False


# 画面连续这么多秒一模一样，就当它卡住了（编码器挂死、网络半通时很常见）
FREEZE_SECONDS = 15


def sample_fingerprint(plane, width, height, stride):
    """取 8×8 个采样点拼成指纹，用来判断画面内容有没有变化。"""
    if width <= 0 or height <= 0 or not plane or len(plane) < height * stride:
        return b''
    step_x = max(1, width // SAMPLE_STEPS)
    step_y = max(1, height // SAMPLE_STEPS)
    samples = bytearray()
    for y in range(0, height, step_y):
        row = y * stride
        for x in range(0, width, step_x):
            offset = row + x * 3
            if offset + 2 < len(plane):
                samples += plane[offset:offset + 3]
    return bytes(samples)


class FreezeWatch:
    """画面长时间没变化就报一次；一旦有变化就清除。

    和黑屏告警互补：黑屏是"一直全黑"，冻结是"一直同一幅画面"。
    """

    def __init__(self, seconds=FREEZE_SECONDS):
        self.seconds = max(1.0, seconds)
        self.fingerprint = None
        self.since = None
        self.alerting = False

    def observe(self, fingerprint, now):
        """喂一帧的指纹，返回 'alert' / 'clear' / None。"""
        if not fingerprint:
            return None
        if fingerprint != self.fingerprint:
            changed = self.alerting
            self.fingerprint = fingerprint
            self.since = now
            if changed:
                self.alerting = False
                return 'clear'
            return None
        if self.since is None:
            self.since = now
            return None
        if not self.alerting and now - self.since >= self.seconds:
            self.alerting = True
            return 'alert'
        return None

    def reset(self):
        self.fingerprint = None
        self.since = None
        self.alerting = False
