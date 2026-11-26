"""Password gate for application fullscreen controls (not an OS kiosk lock)."""
import hashlib
import hmac
import secrets

from PySide6.QtCore import QSettings, QTimer, Slot
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QPushButton,
    QVBoxLayout,
)


class ScreenLock:
    KEY = 'fullscreen/password'
    ITERATIONS = 240_000

    def __init__(self, settings=None):
        self.settings = settings if settings is not None else QSettings('CameraMonitor', 'ScreenLock')
        if not self.settings.contains(self.KEY):
            self._save('000000')

    def verify(self, password):
        record = self.settings.value(self.KEY, '')
        try:
            algorithm, rounds, salt, expected = record.split('$')
            if algorithm != 'pbkdf2_sha256' or int(rounds) != self.ITERATIONS:
                return False
            salt_bytes = bytes.fromhex(salt)
            expected_bytes = bytes.fromhex(expected)
            if len(salt_bytes) != 16 or len(expected_bytes) != 32:
                return False
            actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt_bytes, int(rounds))
            return hmac.compare_digest(actual, expected_bytes)
        except (AttributeError, TypeError, ValueError):
            return False

    @classmethod
    def valid_record(cls, record):
        try:
            algorithm, rounds, salt, digest = str(record).split('$')
            return (algorithm == 'pbkdf2_sha256' and int(rounds) == cls.ITERATIONS
                    and len(bytes.fromhex(salt)) == 16 and len(bytes.fromhex(digest)) == 32)
        except (TypeError, ValueError):
            return False

    def set_record(self, record):
        """采用云端算好的维护密码记录（与 _save 写出的格式完全相同）。

        格式不对就不动本机，宁可沿用旧密码也不能把现场锁死。
        """
        if record is None or not self.valid_record(record):
            return False
        previous = self.settings.value(self.KEY)
        if previous != record:
            self.settings.setValue(self.KEY, record)
            self.settings.sync()
            if self.settings.status() != QSettings.Status.NoError:
                # 写不进本机设置：内存里回滚，如实告诉调用方，别让新密码撑到重启就悄悄失效
                if previous is None:
                    self.settings.remove(self.KEY)
                else:
                    self.settings.setValue(self.KEY, previous)
                return False
        return True

    def _save(self, password):
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, self.ITERATIONS)
        record = f'pbkdf2_sha256${self.ITERATIONS}${salt.hex()}${digest.hex()}'
        previous = self.settings.value(self.KEY)
        self.settings.setValue(self.KEY, record)
        self.settings.sync()
        if self.settings.status() != QSettings.Status.NoError:
            if previous is None:
                self.settings.remove(self.KEY)
            else:
                self.settings.setValue(self.KEY, previous)
            raise OSError('无法保存全屏密码，请检查本地设置权限')

    def change_password(self, current, new, confirm):
        if not self.verify(current):
            raise ValueError('当前密码不正确')
        if not new or not new.strip():
            raise ValueError('新密码不能为空')
        if new != confirm:
            raise ValueError('两次输入的新密码不一致')
        self._save(new)

    def reset_password(self, current):
        if not self.verify(current):
            raise ValueError('当前密码不正确')
        self._save('000000')


def _password_field():
    field = QLineEdit()
    field.setEchoMode(QLineEdit.EchoMode.Password)
    return field


class UnlockDialog(QDialog):
    def __init__(self, lock, parent=None):
        super().__init__(parent)
        self.lock = lock
        self.setWindowTitle('验证全屏密码')
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('请输入密码后继续操作'))
        self.password = _password_field()
        self.password.setPlaceholderText('全屏密码')
        layout.addWidget(self.password)
        self.error = QLabel()
        self.error.setStyleSheet('color: #d34848')
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setText('确认')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('取消')
        self._button_connections = [buttons.accepted.connect(self.accept),
                                    buttons.rejected.connect(self.reject)]
        layout.addWidget(buttons)
        self.password.setFocus()
        self.failures = 0
        # 定时器挂在对话框上：对话框关闭时一起销毁，避免它晚点回调已删除的控件
        self.retry_timer = QTimer(self)
        self.retry_timer.setSingleShot(True)
        self.retry_timer.timeout.connect(self._allow_retry)

    @Slot()
    def accept(self):
        if not self.lock.verify(self.password.text()):
            self.failures += 1
            self.error.setText('密码不正确，请重试')
            self.password.clear()
            self.password.setFocus()
            if self.failures >= 5:
                # 现场大屏前可能有人反复试默认密码，连错五次先缓两秒
                self.ok_button.setEnabled(False)
                self.error.setText('连续输错次数过多，请 2 秒后再试')
                self.retry_timer.start(2000)
            return
        self.failures = 0
        self.password.clear()
        super().accept()

    def _allow_retry(self):
        self.ok_button.setEnabled(True)
        self.error.setText('密码不正确，请重试')

    @Slot()
    def reject(self):
        self.password.clear()
        super().reject()


    @Slot(int)
    def done(self, result):
        # Disconnect while the Python receiver is alive, before deferred Qt deletion.
        for connection in self._button_connections:
            self.disconnect(connection)
        self._button_connections.clear()
        super().done(result)


def request_unlock(parent, lock):
    dialog = UnlockDialog(lock, parent)
    try:
        return dialog.exec() == QDialog.DialogCode.Accepted
    finally:
        dialog.password.clear()
        dialog.deleteLater()


class PasswordSettingsDialog(QDialog):
    def __init__(self, lock, parent=None):
        super().__init__(parent)
        self.lock = lock
        self.setWindowTitle('全屏密码设置')
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('初始密码为 000000。修改或恢复初始密码均需要当前密码。'))
        form = QFormLayout()
        self.current_password = _password_field()
        self.new_password = _password_field()
        self.confirm_password = _password_field()
        form.addRow('当前密码', self.current_password)
        form.addRow('新密码', self.new_password)
        form.addRow('确认新密码', self.confirm_password)
        layout.addLayout(form)
        self.message = QLabel()
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.change_button = QPushButton('修改密码')
        self.reset_button = QPushButton('恢复初始密码 000000')
        self._button_connections = [self.change_button.clicked.connect(self._change),
                                    self.reset_button.clicked.connect(self._reset)]
        layout.addWidget(self.change_button)
        layout.addWidget(self.reset_button)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText('关闭')
        self._button_connections.append(buttons.rejected.connect(self.reject))
        layout.addWidget(buttons)

    def _clear(self):
        for field in (self.current_password, self.new_password, self.confirm_password):
            field.clear()

    @Slot()
    def _change(self):
        try:
            self.lock.change_password(self.current_password.text(), self.new_password.text(), self.confirm_password.text())
        except (ValueError, OSError) as error:
            self.message.setText(str(error))
            return
        self._clear()
        self.message.setText('密码已修改')

    @Slot()
    def _reset(self):
        try:
            self.lock.reset_password(self.current_password.text())
        except (ValueError, OSError) as error:
            self.message.setText(str(error))
            return
        self._clear()
        self.message.setText('密码已恢复为 000000')

    @Slot(int)
    def done(self, result):
        self._clear()
        for connection in self._button_connections:
            self.disconnect(connection)
        self._button_connections.clear()
        super().done(result)
