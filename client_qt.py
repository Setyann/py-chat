import json
import os
import shutil
import socket
import subprocess
import sys
import urllib.request
from datetime import date, datetime, timedelta

from PySide6.QtCore import (QByteArray, QSize, Qt, QThread, QTimer, QVariantAnimation,
                            QEasingCurve, Signal, QWIDGETSIZE_MAX)
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

CLIENT_VERSION = "1.2"  # должна совпадать с version.txt в репозитории
SERVER_IP = "26.182.197.26"  # IP ноутбука из окна Radmin VPN
PORT = 5000

GITHUB_USER = "Setyann"
GITHUB_REPO = "py-chat"
BRANCH = "main"
RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{BRANCH}"
APP_FILE = os.path.abspath(__file__)
APP_DIR = os.path.dirname(APP_FILE)

EMOJIS = ["😀", "😂", "😍", "👍", "🔥", "😎", "🎉", "😢", "❤️", "🤔", "🙌", "😅", "🥳", "🤯", "💯", "😜", "🤩", "😇", "😴", "🤪", "😡", "🤬", "🥺", "😱", "🤤", "😷", "🤮", "🤢", "🤑", "🤠", "👻", "💀", "☠️", "👽", "🤖", "🎃", "🦄", "🐶", "🐱", "🐼", "🐨", "🦊", "🐸", "🐵", "🐔", "🦉", "🦋", "🌸", "🌞", "🌈", "⚡", "❄️", "🔥", "💧", "🌊", "🍎", "🍕", "🍔", "🍟", "🍣", "🍩", "🍪", "☕", "🍺", "🍷", "🍹", "🍾", "🎂", "🎁", "🎈", "🎀", "🎵", "🎶", "🎤", "🎧", "🎸", "🎹", "🥁", "🏆", "🏅", "🥇", "🥈", "🥉", "⚽", "🏀", "🏈", "⚾", "🎾", "🏐", "🏓", "🏸", "🥊", "🥋", "⛳", "🏹", "🎣", "🚴‍♂️", "🏋️‍♀️", "🤸‍♂️", "🤼‍♀️", "🤽‍♂️", "🤾‍♀️", "🏊‍♂️", "🧗‍♀️", "🏄‍♂️", "🛹", "⛷️", "🏂", "🪂", "🚣‍♀️", "🛶", "🛥️", "🚤", "⛴️", "🛳️", "✈️", "🚁", "🚀", "🛸"]

# SVG-код иконок (стиль Lucide). Цвет задаётся в make_icon.
ICONS = {
    "send": '<path d="M22 2L11 13" /><path d="M22 2l-7 20-4-9-9-4 20-7z" />',
    "smile": '<circle cx="12" cy="12" r="10" /><path d="M8 14s1.5 2 4 2 4-2 4-2" />'
             '<line x1="9" y1="9" x2="9.01" y2="9" /><line x1="15" y1="9" x2="15.01" y2="9" />',
    "down": '<path d="M12 5v14" /><path d="M19 12l-7 7-7-7" />',
}


def make_icon(name, color="#f2f2f7", size=20):
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>'
    )
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


STYLE = """
QMainWindow, QWidget#root { background: #1e1f29; }
QWidget#header, QWidget#footer { background: #2a2c3a; }
QWidget#online { background: #232533; }
QWidget#emojibar { background: #2a2c3a; }
QLabel#title { color: #f2f2f7; font: bold 13pt 'Segoe UI'; }
QLabel#status { color: #8a8da3; font: 9pt 'Segoe UI'; }
QLabel#online { color: #8a8da3; font: 9pt 'Segoe UI'; }
QLineEdit { background: #2a2c3a; color: #f2f2f7; border: none;
            border-radius: 8px; padding: 8px; font: 10pt 'Segoe UI'; }
QLineEdit#msg { background: #1e1f29; }
QPushButton { background: #5b6cff; color: white; border: none; outline: none;
              border-radius: 8px; padding: 8px 14px; font: bold 10pt 'Segoe UI'; }
QPushButton:focus { outline: none; }
QPushButton:disabled { background: #3a3d52; color: #8a8da3; }
QPushButton#send { padding: 0; border-radius: 20px; }
QPushButton#send:disabled { background: #3a3d52; }
QPushButton#toggle { background: transparent; padding: 0; border-radius: 20px; }
QPushButton#toggle:hover { background: #3a3d52; }
QPushButton#jump { background: #2a2c3a; color: #f2f2f7; border: 1px solid #3a3d52;
                   border-radius: 16px; padding: 6px 14px; font: 9pt 'Segoe UI'; }
QPushButton#emoji { background: transparent; padding: 2px 4px; font: 14pt 'Segoe UI'; }
QPushButton#emoji:hover { background: #3a3d52; }
QScrollArea { border: none; background: #1e1f29; }
QScrollArea#emojiscroll { background: #2a2c3a; }
QScrollBar:vertical { background: #1e1f29; width: 8px; }
QScrollBar::handle:vertical { background: #3a3d52; border-radius: 4px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
QScrollBar:horizontal { background: #2a2c3a; height: 6px; }
QScrollBar::handle:horizontal { background: #3a3d52; border-radius: 3px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; }
"""

AVATAR_COLORS = ["#ff7eb6", "#7ee787", "#f9c74f", "#4cc9f0", "#c792ea", "#ff9e64"]


def color_for(name):
    return AVATAR_COLORS[sum(map(ord, name)) % len(AVATAR_COLORS)]


def day_label(d):
    today = date.today()
    if d == today:
        return "Сегодня"
    if d == today - timedelta(days=1):
        return "Вчера"
    return d.strftime("%d.%m.%Y")


def version_tuple(v):
    return tuple(int(x) for x in v.split(".") if x.isdigit())


def pack(data):
    return (json.dumps(data, ensure_ascii=False) + "\n").encode("utf-8")


class Receiver(QThread):
    """Фоновый поток: читает JSON-записи из сокета и отправляет их в окно."""
    message = Signal(object)
    disconnected = Signal()

    def __init__(self, sock):
        super().__init__()
        self.sock = sock

    def run(self):
        buffer = b""
        while True:
            try:
                chunk = self.sock.recv(4096)
            except OSError:
                break
            if not chunk:
                break
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                try:
                    self.message.emit(json.loads(line.decode("utf-8")))
                except ValueError:
                    pass
        self.disconnected.emit()


class UpdateChecker(QThread):
    """Проверяет version.txt в репозитории в фоне, чтобы окно не зависало."""
    found = Signal(str)

    def run(self):
        try:
            with urllib.request.urlopen(f"{RAW_URL}/version.txt", timeout=5) as r:
                remote = r.read().decode("utf-8").strip()
        except OSError:
            return  # нет интернета или GitHub недоступен: молча пропускаем
        if version_tuple(remote) > version_tuple(CLIENT_VERSION):
            self.found.emit(remote)


def install_update():
    """Возвращает (успех, текст лога)."""
    if os.path.isdir(os.path.join(APP_DIR, ".git")):
        result = subprocess.run(["git", "pull", "--ff-only"], cwd=APP_DIR,
                                capture_output=True, text=True)
        return result.returncode == 0, (result.stdout + result.stderr).strip()

    # папка не из git: скачиваем только сам клиент
    try:
        with urllib.request.urlopen(f"{RAW_URL}/client_qt.py", timeout=10) as r:
            code = r.read().decode("utf-8")
        shutil.copy(APP_FILE, APP_FILE + ".bak")
        with open(APP_FILE, "w", encoding="utf-8") as f:
            f.write(code)
        return True, "Файл обновлён"
    except OSError as e:
        return False, str(e)


class DaySeparator(QLabel):
    def __init__(self, text):
        super().__init__(text)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(
            "background: #2a2c3a; color: #8a8da3; border-radius: 10px;"
            "padding: 3px 12px; font: 8pt 'Segoe UI';"
        )


class Bubble(QWidget):
    def __init__(self, author, text, mine=False, system=False, grouped=False, time_str=""):
        super().__init__()
        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 1 if grouped else 6, 12, 1)

        if system:
            label = QLabel(text)
            label.setStyleSheet("color: #6e7191; font: italic 9pt 'Segoe UI';")
            label.setAlignment(Qt.AlignCenter)
            outer.addWidget(label)
            return

        column = QVBoxLayout()
        column.setSpacing(2)

        bubble_text = QLabel(text)
        bubble_text.setWordWrap(True)
        bubble_text.setMaximumWidth(300)
        bubble_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bubble_bg = "#5b6cff" if mine else "#3a3d52"
        bubble_text.setStyleSheet(
            f"background: {bubble_bg}; color: #f2f2f7; font: 10pt 'Segoe UI';"
            "border-radius: 10px; padding: 7px 12px;"
        )

        if not grouped:
            meta = QLabel(f"{'Вы' if mine else author}  {time_str}")
            meta.setStyleSheet("color: #8a8da3; font: 8pt 'Segoe UI';")
            meta.setAlignment(Qt.AlignRight if mine else Qt.AlignLeft)
            column.addWidget(meta)

        column.addWidget(bubble_text, alignment=Qt.AlignRight if mine else Qt.AlignLeft)

        if mine:
            outer.addStretch()
            outer.addLayout(column)
        else:
            if grouped:
                spacer = QWidget()
                spacer.setFixedSize(32, 32)
                outer.addWidget(spacer, alignment=Qt.AlignTop)
            else:
                avatar = QLabel(author[:1].upper())
                avatar.setFixedSize(32, 32)
                avatar.setAlignment(Qt.AlignCenter)
                avatar.setStyleSheet(
                    f"background: {color_for(author)}; color: #111;"
                    "border-radius: 16px; font: bold 10pt 'Segoe UI';"
                )
                outer.addWidget(avatar, alignment=Qt.AlignTop)
            outer.addLayout(column)
            outer.addStretch()

    def play_in(self, on_step=None):
        """Анимация появления: пузырь «выезжает» по высоте за 250 мс.
        Работает через высоту, а не через прозрачность, поэтому не ломает отрисовку."""
        target = self.sizeHint().height()
        self.setFixedHeight(0)
        anim = QVariantAnimation(self)
        anim.setStartValue(0)
        anim.setEndValue(target)
        anim.setDuration(250)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        def step(value):
            self.setFixedHeight(int(value))
            if on_step:
                on_step()

        def done():
            self.setMinimumHeight(0)
            self.setMaximumHeight(QWIDGETSIZE_MAX)

        anim.valueChanged.connect(step)
        anim.finished.connect(done)
        self._anim = anim  # держим ссылку, чтобы анимация не удалилась сборщиком мусора
        anim.start()


class ChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Чат друзей")
        self.resize(480, 640)
        self.setStyleSheet(STYLE)
        self.sock = None
        self.name = ""

        self.last_date = None
        self.last_author = None
        self.unread = 0
        self.in_history = False

        root = QWidget()
        root.setObjectName("root")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # шапка
        header = QWidget()
        header.setObjectName("header")
        h = QHBoxLayout(header)
        h.setContentsMargins(12, 10, 12, 10)
        title = QLabel("Чат друзей")
        title.setObjectName("title")
        self.status = QLabel("Не подключено")
        self.status.setObjectName("status")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Ваше имя")
        self.name_edit.setFixedWidth(120)
        self.name_edit.returnPressed.connect(self.connect_to_server)
        self.connect_btn = QPushButton("Войти")
        self.connect_btn.clicked.connect(self.connect_to_server)
        h.addWidget(title)
        h.addSpacing(10)
        h.addWidget(self.status)
        h.addStretch()
        h.addWidget(self.name_edit)
        h.addWidget(self.connect_btn)
        layout.addWidget(header)

        # строка онлайн-участников
        online_bar = QWidget()
        online_bar.setObjectName("online")
        ob = QHBoxLayout(online_bar)
        ob.setContentsMargins(12, 5, 12, 5)
        self.online = QLabel("В сети: никого")
        self.online.setObjectName("online")
        ob.addWidget(self.online)
        layout.addWidget(online_bar)

        # лента сообщений
        self.messages_widget = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setAlignment(Qt.AlignTop)
        self.messages_layout.setSpacing(2)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.messages_widget)
        self.scroll.verticalScrollBar().valueChanged.connect(self.on_scroll)
        layout.addWidget(self.scroll, stretch=1)

        # кнопка «вниз» поверх ленты
        self.jump_btn = QPushButton(self.scroll.viewport())
        self.jump_btn.setObjectName("jump")
        self.jump_btn.setIcon(make_icon("down", "#f2f2f7", 16))
        self.jump_btn.setIconSize(QSize(16, 16))
        self.jump_btn.clicked.connect(self.jump_to_bottom)
        self.jump_btn.hide()

        # панель эмодзи
        emoji_scroll = QScrollArea()
        emoji_scroll.setObjectName("emojiscroll")
        emoji_scroll.setWidgetResizable(True)
        emoji_scroll.setFixedHeight(50)
        emoji_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        emoji_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.emoji_bar = QWidget()
        self.emoji_bar.setObjectName("emojibar")
        eb = QHBoxLayout(self.emoji_bar)
        eb.setContentsMargins(12, 4, 12, 4)
        for emoji in EMOJIS:
            btn = QPushButton(emoji)
            btn.setObjectName("emoji")
            btn.clicked.connect(lambda checked=False, e=emoji: self.insert_emoji(e))
            eb.addWidget(btn)
        eb.addStretch()
        emoji_scroll.setWidget(self.emoji_bar)
        self.emoji_panel = emoji_scroll
        self.emoji_panel.hide()
        layout.addWidget(self.emoji_panel)

        # нижняя панель
        footer = QWidget()
        footer.setObjectName("footer")
        f = QHBoxLayout(footer)
        f.setContentsMargins(12, 10, 12, 10)

        self.emoji_toggle = QPushButton()
        self.emoji_toggle.setObjectName("toggle")
        self.emoji_toggle.setIcon(make_icon("smile", "#8a8da3", 20))
        self.emoji_toggle.setIconSize(QSize(20, 20))
        self.emoji_toggle.setFixedSize(40, 40)
        self.emoji_toggle.clicked.connect(
            lambda: self.emoji_panel.setVisible(not self.emoji_panel.isVisible()))

        self.msg_edit = QLineEdit()
        self.msg_edit.setObjectName("msg")
        self.msg_edit.setPlaceholderText("Сообщение...")
        self.msg_edit.setEnabled(False)
        self.msg_edit.returnPressed.connect(self.send)

        self.send_btn = QPushButton()
        self.send_btn.setObjectName("send")
        self.send_btn.setIcon(make_icon("send", "#ffffff", 18))
        self.send_btn.setIconSize(QSize(18, 18))
        self.send_btn.setFixedSize(40, 40)
        self.send_btn.setEnabled(False)
        self.send_btn.clicked.connect(self.send)

        f.addWidget(self.emoji_toggle)
        f.addWidget(self.msg_edit)
        f.addWidget(self.send_btn)
        layout.addWidget(footer)

        self.setCentralWidget(root)

        # проверка обновлений через пару секунд после запуска
        QTimer.singleShot(1500, self.start_update_check)

    # ----- эмодзи -----

    def insert_emoji(self, emoji):
        self.msg_edit.insert(emoji)
        self.msg_edit.setFocus()

    # ----- лента сообщений -----

    def show_message(self, author, text, mine=False, system=False, when=None, history=False):
        when = when or datetime.now()
        if self.last_date != when.date():
            self.add_widget(DaySeparator(day_label(when.date())), center=True)
            self.last_date = when.date()
            self.last_author = None

        key = "me" if mine else author
        grouped = not system and key == self.last_author
        self.last_author = None if system else key

        bubble = Bubble(author, text, mine=mine, system=system, grouped=grouped,
                        time_str=when.strftime("%H:%M"))
        self.add_widget(bubble, incoming=not mine and not system and not history, animate=True)

    def add_widget(self, widget, incoming=False, center=False, animate=False):
        bar = self.scroll.verticalScrollBar()
        was_at_bottom = bar.value() >= bar.maximum() - 30
        follow = was_at_bottom or not incoming

        self.messages_layout.addWidget(
            widget, alignment=Qt.AlignCenter if center else Qt.Alignment()
        )
        self.messages_layout.invalidate()
        self.messages_layout.activate()

        if animate and isinstance(widget, Bubble):
            widget.play_in(self.scroll_to_bottom if follow else None)

        if follow:
            QTimer.singleShot(50, self.scroll_to_bottom)
        else:
            self.unread += 1
            self.update_jump_button()

    def scroll_to_bottom(self):
        bar = self.scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def jump_to_bottom(self):
        self.scroll_to_bottom()
        self.unread = 0
        self.jump_btn.hide()

    def on_scroll(self, value):
        bar = self.scroll.verticalScrollBar()
        if value >= bar.maximum() - 30:
            self.unread = 0
            self.jump_btn.hide()

    def update_jump_button(self):
        self.jump_btn.setText(f" {self.unread} новых" if self.unread else "")
        self.jump_btn.adjustSize()
        self.place_jump_button()
        self.jump_btn.show()
        self.jump_btn.raise_()

    def place_jump_button(self):
        vp = self.scroll.viewport()
        x = (vp.width() - self.jump_btn.width()) // 2
        y = vp.height() - self.jump_btn.height() - 12
        self.jump_btn.move(x, y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.jump_btn.isVisible():
            self.place_jump_button()

    # ----- сеть -----

    def connect_to_server(self):
        self.name = self.name_edit.text().strip()
        if not self.name or self.sock:
            return
        try:
            self.sock = socket.create_connection((SERVER_IP, PORT), timeout=5)
            self.sock.settimeout(None)
            self.sock.sendall(pack({"type": "join", "name": self.name}))
        except OSError as e:
            self.sock = None
            self.show_message("", f"Не удалось подключиться: {e}", system=True)
            return

        self.name_edit.setEnabled(False)
        self.connect_btn.setEnabled(False)
        self.msg_edit.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.msg_edit.setFocus()
        self.status.setText("● В сети")
        self.status.setStyleSheet("color: #3ddc84; font: 9pt 'Segoe UI';")

        self.receiver = Receiver(self.sock)
        self.receiver.message.connect(self.on_incoming)
        self.receiver.disconnected.connect(self.on_lost)
        self.receiver.start()

    def on_incoming(self, data):
        kind = data.get("type")
        when = None
        if "time" in data:
            when = datetime.strptime(data["time"], "%Y-%m-%d %H:%M:%S")

        if kind == "users":
            names = [n for n in data["list"] if n]
            self.online.setText(f"В сети ({len(names)}): " + ", ".join(names))
            return

        if kind == "system":
            self.show_message("", data["text"], system=True, when=when)
            return

        if kind == "msg":
            history = data.get("history", False)
            author = data["author"]
            mine = author == self.name

            if history:
                self.in_history = True
            elif self.in_history:
                self.in_history = False
                self.show_message("", "— конец истории —", system=True)

            self.show_message(author, data["text"], mine=mine, when=when, history=history)

            if not history and not mine and not self.isActiveWindow():
                QApplication.beep()
                QApplication.alert(self)

    # ----- обновление -----

    def start_update_check(self):
        self.checker = UpdateChecker()
        self.checker.found.connect(self.offer_update)
        self.checker.start()

    def offer_update(self, version):
        answer = QMessageBox.question(
            self, "Обновление",
            f"Доступна версия {version} (у вас {CLIENT_VERSION}). Обновить?",
        )
        if answer != QMessageBox.Yes:
            return
        ok, log = install_update()
        if not ok:
            QMessageBox.warning(self, "Ошибка обновления", log or "Неизвестная ошибка")
            return
        QMessageBox.information(self, "Готово", "Обновление установлено. Приложение перезапустится.")
        if self.sock:
            self.sock.close()
        subprocess.Popen([sys.executable, APP_FILE])
        QApplication.quit()

    # ----- отправка -----

    def on_lost(self):
        self.status.setText("● Отключено")
        self.status.setStyleSheet("color: #ff5c5c; font: 9pt 'Segoe UI';")
        self.show_message("", "Соединение с сервером потеряно", system=True)
        self.msg_edit.setEnabled(False)
        self.send_btn.setEnabled(False)

    def send(self):
        text = self.msg_edit.text().strip()
        if not text or self.sock is None:
            return
        try:
            self.sock.sendall(pack({"type": "msg", "text": text}))
        except OSError:
            self.on_lost()
            return
        self.msg_edit.clear()

    def closeEvent(self, event):
        if self.sock:
            self.sock.close()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatWindow()
    window.show()
    sys.exit(app.exec())