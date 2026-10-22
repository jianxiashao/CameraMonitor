"""环形录像：每路留最近一段时间的缩时画面，用来回答"刚才那几分钟发生了什么"。

只按 1 帧/秒、宽 480 录，目的是让 25 路也压得住 CPU 与磁盘，不是用来取证的。
文件放在系统临时目录，按 1 分钟一段滚动删除，退出后不保证保留。
"""
import os
import shutil
import sys
import tempfile
import time

import av
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

SEGMENT_SECONDS = 60
DEFAULT_MINUTES = 10
DEFAULT_FPS = 1
DEFAULT_WIDTH = 480
FOLDER_NAME = 'camera-monitor-ring'
# 画面异常时把事发片段另存到这里，避免被环形缓冲滚掉
EVENTS_FOLDER = 'camera-monitor-events'
# 磁盘剩这么点就不再录：环形录像只是兜底，不能把现场磁盘写满
MIN_FREE_BYTES = 512 * 1024 * 1024


def default_folder():
    return os.path.join(tempfile.gettempdir(), FOLDER_NAME)


def _frame_from_image(image, width):
    """QImage → av.VideoFrame(rgb24)。行宽可能带对齐填充，所以逐行拼。"""
    scaled = image.scaledToWidth(min(width, image.width()), Qt.TransformationMode.FastTransformation)
    scaled = scaled.convertToFormat(QImage.Format.Format_RGB888)
    frame = av.VideoFrame(scaled.width(), scaled.height(), 'rgb24')
    plane = frame.planes[0]
    source = scaled.constBits().tobytes()
    stride = scaled.bytesPerLine()
    row_bytes = min(stride, plane.line_size)
    padding = b'\x00' * max(0, plane.line_size - row_bytes)
    rows = []
    for y in range(scaled.height()):
        start = y * stride
        rows.append(source[start:start + row_bytes])
        if padding:
            rows.append(padding)
    plane.update(b''.join(rows))
    return frame


class RingRecorder:
    """单路环形录像。add() 由界面定时器驱动，不自己开线程。"""

    def __init__(self, ip, folder=None, minutes=DEFAULT_MINUTES, fps=DEFAULT_FPS,
                 width=DEFAULT_WIDTH, segment_seconds=SEGMENT_SECONDS):
        self.ip = ip
        self.root = os.path.join(folder or default_folder(), ip.replace(':', '_'))
        self.minutes = max(1, minutes)
        self.fps = max(1, fps)
        self.width = width
        self.segment_seconds = segment_seconds
        self.container = None
        self.stream = None
        self.segment_started = 0.0
        self.segment_path = ''
        self.frames = 0

    # ---------- 写 ----------

    def _open_segment(self, now):
        self._close_segment()
        os.makedirs(self.root, exist_ok=True)
        # 毫秒命名：同一秒内开的新分段不会互相覆盖
        self.segment_path = os.path.join(self.root, f'{int(time.time() * 1000)}.mp4')
        self.container = av.open(self.segment_path, 'w')
        self.stream = self.container.add_stream('mpeg4', rate=self.fps)
        self.stream.pix_fmt = 'yuv420p'
        self.segment_started = now
        self._trim()

    def _close_segment(self):
        if self.container is None:
            return
        try:
            for packet in self.stream.encode():
                self.container.mux(packet)
        finally:
            self.container.close()
            self.container = None
            self.stream = None

    def add(self, image):
        """喂一帧；只有真正写进去了才返回 True。"""
        if image is None or image.isNull():
            return False
        now = time.monotonic()
        if self.container is None or now - self.segment_started >= self.segment_seconds:
            self._open_segment(now)
        frame = _frame_from_image(image, self.width)
        if not self.stream.width:
            self.stream.width, self.stream.height = frame.width, frame.height
        for packet in self.stream.encode(frame):
            self.container.mux(packet)
        self.frames += 1
        return True

    def _trim(self):
        """删掉超过保留时长的分段。"""
        keep_after = time.time() - self.minutes * 60
        for label, path in self.segments():
            if label < keep_after:
                try:
                    os.remove(path)
                except OSError:
                    pass

    # ---------- 读 ----------

    def segments(self):
        """返回 [(开始时间戳, 路径)]，按时间升序。"""
        try:
            names = sorted(os.listdir(self.root))
        except OSError:
            return []
        found = []
        for name in names:
            if not name.endswith('.mp4'):
                continue
            stem = name[:-4]
            if not stem.isdigit():
                continue
            # 文件名是毫秒时间戳，换回秒方便和保留时长比较
            found.append((int(stem) / 1000.0, os.path.join(self.root, name)))
        return found

    def close(self):
        self._close_segment()

    def freeze(self, keep=2):
        """把最近几段另存到事件目录，返回保存下来的文件路径。

        环形缓冲只留 10 分钟，出事之后再来看往往已经被滚掉了；
        画面异常发生时先把事发片段复制出来，回看才有东西可看。
        """
        self._close_segment()
        saved = []
        segments = self.segments()
        if not segments:
            return saved
        target = os.path.join(tempfile.gettempdir(), EVENTS_FOLDER,
                              f'{int(time.time())}-{self.ip.replace(":", "_")}')
        try:
            os.makedirs(target, exist_ok=True)
        except OSError:
            return saved
        for _, path in segments[-max(1, keep):]:
            destination = os.path.join(target, os.path.basename(path))
            try:
                shutil.copy2(path, destination)
            except OSError:
                continue
            saved.append(destination)
        return saved

    def clear(self):
        self.close()
        for _, path in self.segments():
            try:
                os.remove(path)
            except OSError:
                pass


def default_enabled():
    """默认要不要录。

    测试进程（argv 里带 unittest）默认关：每秒给有画面的格子编码 mp4
    会把整套用例拖慢，还会往临时目录写一堆文件。生产环境默认开。
    """
    if os.environ.get('CAMERA_MONITOR_NO_RECORDING'):
        return False
    return 'unittest' not in ' '.join(sys.argv)


class RecorderPool:
    """按 ip 管一组录制器；没在录的相机不会占资源。"""

    def __init__(self, folder=None, minutes=DEFAULT_MINUTES, enabled=None):
        self.folder = folder or default_folder()
        self.minutes = minutes
        self.enabled = default_enabled() if enabled is None else enabled
        self.recorders = {}
        # 磁盘写满时置上原因，界面提示一次就够
        self.stopped_reason = ''

    def _has_space(self):
        if self.stopped_reason:
            return False
        try:
            free = shutil.disk_usage(self.folder).free
        except OSError:
            return True         # 查不到就按有空间处理，别因为统计失败停止录像
        if free < MIN_FREE_BYTES:
            self.stopped_reason = f'磁盘剩余不足 {MIN_FREE_BYTES // (1024 ** 2)} MB，已暂停录像'
            return False
        return True

    def add(self, ip, image):
        if not self.enabled:
            return False
        if not self._has_space():
            return False
        recorder = self.recorders.get(ip)
        if recorder is None:
            recorder = RingRecorder(ip, self.folder, minutes=self.minutes)
            self.recorders[ip] = recorder
        return recorder.add(image)

    def segments(self, ip):
        recorder = self.recorders.get(ip)
        if recorder is not None:
            return recorder.segments()
        # 没在录的相机也允许回看上次留下的画面
        return RingRecorder(ip, self.folder, minutes=self.minutes).segments()

    def freeze(self, ip, keep=2):
        """画面异常时把这一路的事发片段另存一份。"""
        recorder = self.recorders.get(ip)
        if recorder is None:
            return []
        return recorder.freeze(keep=keep)

    def close(self):
        for recorder in self.recorders.values():
            recorder.close()
        self.recorders.clear()


def frames_of(segments):
    """把若干分段的画面按时间顺序解码出来，供回放界面逐帧取用。"""
    for _, path in segments:
        try:
            with av.open(path) as source:
                if not source.streams.video:
                    continue
                video = source.streams.video[0]
                for frame in source.decode(video):
                    rgb = frame.reformat(format='rgb24')
                    plane = rgb.planes[0]
                    yield QImage(bytes(plane), rgb.width, rgb.height, plane.line_size,
                                 QImage.Format.Format_RGB888)
        except (av.error.FFmpegError, OSError):
            # 分段正在写、或文件被清掉：跳过这一段，别让回放整体失败
            continue
