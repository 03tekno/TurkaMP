import sys
import os
import random
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFrame, QFileDialog, 
                             QListWidget, QSlider, QListWidgetItem, QMenu, QLineEdit)
from PyQt6.QtCore import Qt, QRect, QPointF, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QAction, QPainter, QColor, QLinearGradient, QPen, QFont, QFontMetrics, QIcon, QGuiApplication, QPolygonF
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".turkamp_config.json")
SUPPORTED_FORMATS = ('.mp3', '.wav', '.flac', '.m4a', '.mpga' '.aac', '.ogg', '.opus', '.wma', '.m4b', '.aiff', '.mid', '.amr')
ICON_NAME = "turkamp.png" 

class DragDropList(QListWidget):
    fileDropped = pyqtSignal(list)
    deleteRequested = pyqtSignal()
    clearRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        self.fileDropped.emit(files)

    def show_context_menu(self, position):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #2c3e50; color: white; border: 1px solid #7f8c8d; } QMenu::item:selected { background-color: #34495e; }")
        remove_action = QAction("Parçayı Sil", self)
        remove_action.triggered.connect(lambda: self.deleteRequested.emit())
        clear_action = QAction("Tümünü Sil", self)
        clear_action.triggered.connect(lambda: self.clearRequested.emit())
        if self.itemAt(position): menu.addAction(remove_action)
        menu.addAction(clear_action)
        menu.exec(self.mapToGlobal(position))

class ScrollingLabel(QWidget):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.full_text = ""; self.text_width = 0; self.offset = 0; self.setFixedHeight(35)
        self.timer = QTimer(self); self.timer.timeout.connect(self.update_offset); self.timer.start(30)
        self.setText(text)

    def setText(self, text):
        self.full_text = str(text); metrics = QFontMetrics(QFont("DejaVu Sans", 11))
        self.text_width = metrics.horizontalAdvance(self.full_text); self.space_gap = 150; self.offset = 0; self.update()

    def update_offset(self):
        if not self.full_text: return
        self.offset -= 1
        if abs(self.offset) >= (self.text_width + self.space_gap): self.offset = 0
        self.update()

    def paintEvent(self, event):
        if not self.full_text: return
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor("#FFFFFF")); painter.setFont(QFont("DejaVu Sans", 11))
        metrics = painter.fontMetrics(); y_pos = (self.height() + metrics.ascent() - metrics.descent()) // 2
        painter.drawText(self.offset, y_pos, self.full_text)
        painter.drawText(self.offset + self.text_width + self.space_gap, y_pos, self.full_text)

class ProVolumeKnob(QWidget):
    valueChanged = pyqtSignal(int)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(110, 110); self.value = 75; self.color = QColor("#00e676"); self.is_dark = True

    def setValue(self, val): self.value = max(0, min(100, val)); self.update()

    def mouseMoveEvent(self, event):
        pos = event.position(); delta = pos.y() - self.height()/2
        val = max(0, min(100, 100 - int((delta + 30) * 1.6)))
        self.value = val; self.valueChanged.emit(self.value); self.update()

    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height()) - 15
        rect_f = QRect(0, 0, side, side); rect_f.moveCenter(self.rect().center())
        shadow_rect = rect_f.adjusted(2, 2, 2, 2)
        painter.setBrush(QColor(0,0,0,100)); painter.setPen(Qt.PenStyle.NoPen); painter.drawEllipse(shadow_rect)
        grad = QLinearGradient(QPointF(rect_f.topLeft()), QPointF(rect_f.bottomRight()))
        if self.is_dark:
            grad.setColorAt(0, QColor("#3d3d3d")); grad.setColorAt(0.5, QColor("#2d3436")); grad.setColorAt(1, QColor("#1e1e1e"))
            text_color = QColor("#FFFFFF")
        else:
            grad.setColorAt(0, QColor("#fdfdfd")); grad.setColorAt(0.5, QColor("#d1d8e0")); grad.setColorAt(1, QColor("#a5b1c2"))
            text_color = QColor("#2d3436")
        painter.setBrush(grad); painter.setPen(QPen(QColor("#000000") if self.is_dark else QColor("#778ca3"), 1.5)); painter.drawEllipse(rect_f)
        pen = QPen(self.color, 4.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen); angle = int(self.value * 3.6 * 16)
        painter.drawArc(rect_f.adjusted(6, 6, -6, -6), 90 * 16, -angle)
        painter.setPen(text_color); painter.setFont(QFont("sans-serif", 9, QFont.Weight.Bold))
        painter.drawText(rect_f, Qt.AlignmentFlag.AlignCenter, f"%{self.value}")

class ModernSpectrum(QWidget):
    modeChanged = pyqtSignal(int)

    def __init__(self, player):
        super().__init__()
        self.player = player
        self.color = QColor("#00e676")
        self.bars = 35
        self.mode = 0
        self.heights = [0.0] * self.bars
        self.target_heights = [0.0] * self.bars
        self.timer = QTimer(); self.timer.timeout.connect(self.animate); self.timer.start(30)
        self.setToolTip("Görünümü değiştirmek için tıkla!")

    def mousePressEvent(self, event):
        self.mode = (self.mode + 1) % 10
        self.modeChanged.emit(self.mode)
        self.update()

    def animate(self):
        playing = self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        for i in range(self.bars):
            self.target_heights[i] = random.uniform(5, self.height() - 15) if playing else 0
            self.heights[i] += (self.target_heights[i] - self.heights[i]) * 0.2
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#000000"))
        w = self.width() / self.bars
        mid_y = self.height() / 2
        for i in range(self.bars):
            h = self.heights[i]
            grad = QLinearGradient(QPointF(0, float(self.height())), QPointF(0, float(self.height() - h)))
            grad.setColorAt(0, self.color); grad.setColorAt(1, QColor(255, 255, 255, 180))
            painter.setBrush(grad); painter.setPen(Qt.PenStyle.NoPen)
            if self.mode == 0: painter.drawRoundedRect(int(i * w + 2), int(self.height() - h), int(w - 4), int(h), 2, 2)
            elif self.mode == 1: painter.drawRoundedRect(int(i * w + 2), int(mid_y - h/2), int(w - 4), int(h), 2, 2)
            elif self.mode == 2: painter.drawRoundedRect(int(i * w + 2), 0, int(w - 4), int(h), 2, 2)
            elif self.mode == 3: 
                painter.setPen(QPen(self.color, 2))
                painter.drawLine(int(i * w + w/2), self.height(), int(i * w + w/2), int(self.height() - h))
            elif self.mode == 4: painter.drawEllipse(QPointF(i * w + w/2, self.height() - h), 3, 3)
            elif self.mode == 5: 
                painter.drawRect(int(i * w + 2), int(self.height() - h), int(w - 4), 4)
                painter.drawRect(int(i * w + 2), int(h), int(w - 4), 4)
            elif self.mode == 6: 
                step = (h // 12) * 12
                painter.drawRect(int(i * w + 2), int(self.height() - step), int(w - 4), int(step))
            elif self.mode == 7: 
                for b in range(int(h // 10)): painter.drawRect(int(i * w + 2), self.height() - (b * 10), int(w - 4), 7)
            elif self.mode == 8: 
                if i < self.bars - 1:
                    painter.setPen(QPen(self.color, 2))
                    painter.drawLine(int(i * w), int(self.height() - h), int((i+1) * w), int(self.height() - self.heights[i+1]))
            elif self.mode == 9: 
                painter.setBrush(QColor(self.color.red(), self.color.green(), self.color.blue(), 100))
                poly = QPolygonF([QPointF(i * w, self.height()), QPointF(i * w, self.height() - h), 
                                 QPointF((i+1) * w, self.height() - self.heights[min(i+1, self.bars-1)]), QPointF((i+1) * w, self.height())])
                painter.drawPolygon(poly)

class TurkaPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Turka Music Player")
        icon_path = os.path.join(os.path.dirname(__file__), ICON_NAME)
        if os.path.exists(icon_path): self.setWindowIcon(QIcon(icon_path))

        self.player = QMediaPlayer(); self.audio = QAudioOutput(); self.player.setAudioOutput(self.audio)
        self.is_dark_mode = True; self.is_shuffled = False; self.is_repeated = False; self.is_list_visible = False 
        
        self.themes = ["#00e676", "#00b0ff", "#ff3d00", "#d4af37", "#bd93f9", "#ff79c6", "#8be9fd", "#50fa7b", "#ffb86c", "#ff5555", "#f1fa8c", "#00d2ff", "#9c27b0", "#76ff03", "#ffffff", "#ff9800", "#03a9f4", "#e91e63", "#607d8b", "#795548"]
        self.current_theme_idx = 0
        self.collapsed_width = 440; self.expanded_width = 850; self.player_height = 520
        
        self.init_ui()
        self.setup_logic()
        self.load_settings()
        self.apply_theme_styles()
        self.toggle_list(force=self.is_list_visible)
        self.center_window() # Uygulama açılışında ekranın ortasına al

    def center_window(self):
        qr = self.frameGeometry()
        cp = QGuiApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def init_ui(self):
        main_widget = QWidget(); self.setCentralWidget(main_widget)
        self.layout_horizontal = QHBoxLayout(main_widget); self.layout_horizontal.setContentsMargins(15, 15, 15, 15); self.layout_horizontal.setSpacing(15)

        self.left_panel = QWidget(); self.layout_left = QVBoxLayout(self.left_panel); self.layout_left.setContentsMargins(0, 0, 0, 0); self.layout_left.setSpacing(10); self.left_panel.setFixedWidth(400)
        self.lcd_container = QFrame(); self.lcd_container.setObjectName("LCDContainer"); self.lcd_container.setFixedHeight(180) 
        lcd_lyt = QVBoxLayout(self.lcd_container); lcd_lyt.setContentsMargins(12, 10, 12, 10)
        self.title_lbl = ScrollingLabel("Turka Music Player - Hazır"); lcd_lyt.addWidget(self.title_lbl)
        self.vumeter = ModernSpectrum(self.player); lcd_lyt.addWidget(self.vumeter)
        self.layout_left.addWidget(self.lcd_container)

        self.progress_container = QWidget(); prog_lyt = QVBoxLayout(self.progress_container); prog_lyt.setContentsMargins(5, 0, 5, 0); prog_lyt.setSpacing(2)
        self.time_lbl = QLabel("00:00 / 00:00"); self.time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar = QSlider(Qt.Orientation.Horizontal); prog_lyt.addWidget(self.time_lbl); prog_lyt.addWidget(self.progress_bar); self.layout_left.addWidget(self.progress_container)

        self.top_btn_container = QWidget(); top_btn_layout = QHBoxLayout(self.top_btn_container); top_btn_layout.setContentsMargins(0, 0, 0, 0); top_btn_layout.setSpacing(8) 
        self.btn_add = self.create_rect_btn("Ekle +", 65, 30); self.btn_list_toggle = self.create_rect_btn("Liste ≣", 65, 30)
        self.btn_shuffle = self.create_rect_btn("Rastgele", 65, 30); self.btn_repeat = self.create_rect_btn("Tekrarla", 65, 30)
        self.btn_theme = self.create_rect_btn("Tema", 60, 30); self.btn_mode = self.create_rect_btn("☾", 35, 30) 
        for b in [self.btn_add, self.btn_list_toggle, self.btn_shuffle, self.btn_repeat, self.btn_theme, self.btn_mode]: top_btn_layout.addWidget(b)
        self.layout_left.addWidget(self.top_btn_container)

        self.volume_container = QFrame(); self.volume_container.setObjectName("VolumePanel"); self.volume_container.setFixedHeight(130)
        volume_layout = QHBoxLayout(self.volume_container); volume_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_vol_down = self.create_circle_btn("-", 38); self.knob = ProVolumeKnob(); self.btn_vol_up = self.create_circle_btn("+", 38)
        volume_layout.addWidget(self.btn_vol_down); volume_layout.addWidget(self.knob); volume_layout.addWidget(self.btn_vol_up); self.layout_left.addWidget(self.volume_container)
        
        self.nav_container = QFrame(); self.nav_container.setObjectName("NavPanel"); self.nav_container.setFixedHeight(85)
        nav_layout = QHBoxLayout(self.nav_container); nav_layout.setSpacing(12); nav_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_back5 = self.create_circle_btn("⟲", 38); self.btn_prev = self.create_circle_btn("◀", 48); self.btn_play = self.create_circle_btn("▶", 65); self.btn_next = self.create_circle_btn("▶", 48); self.btn_fwd5 = self.create_circle_btn("⟳", 38)
        for b in [self.btn_back5, self.btn_prev, self.btn_play, self.btn_next, self.btn_fwd5]: nav_layout.addWidget(b)
        self.layout_left.addWidget(self.nav_container); self.layout_horizontal.addWidget(self.left_panel)

        self.right_panel = QWidget(); self.layout_right = QVBoxLayout(self.right_panel); self.layout_right.setContentsMargins(0, 0, 0, 0); self.layout_right.setSpacing(10)
        self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText("Parçalarda ara..."); self.search_bar.setFixedHeight(35)
        self.list = DragDropList(); self.layout_right.addWidget(self.search_bar); self.layout_right.addWidget(self.list); self.layout_horizontal.addWidget(self.right_panel)

    def create_circle_btn(self, text, size): btn = QPushButton(text); btn.setFixedSize(size, size); return btn
    def create_rect_btn(self, text, w, h): btn = QPushButton(text); btn.setFixedSize(w, h); return btn

    def toggle_list(self, force=None):
        if force is not None: self.is_list_visible = force
        else: self.is_list_visible = not self.is_list_visible
        self.right_panel.setVisible(self.is_list_visible)
        new_width = self.expanded_width if self.is_list_visible else self.collapsed_width
        self.setFixedSize(new_width, self.player_height); self.apply_theme_styles()

    def apply_theme_styles(self):
        color = self.themes[self.current_theme_idx]; qcolor = QColor(color)
        self.knob.is_dark = self.is_dark_mode; self.knob.color = qcolor; self.vumeter.color = qcolor
        if self.is_dark_mode:
            bg_style = "QMainWindow { background-color: #121212; }"; panel_bg = "#1e1e1e"; btn_grad = "stop:0 #333, stop:1 #1a1a1a"; shadow_light = "#2a2a2a"; shadow_dark = "#000000"; text_color = "#ffffff"; scroll_color = "#C0C0C0"
        else:
            bg_style = "QMainWindow { background-color: #e0e5ec; }"; panel_bg = "#e0e5ec"; btn_grad = "stop:0 #ffffff, stop:1 #d1d9e6"; shadow_light = "#ffffff"; shadow_dark = "#b8b9be"; text_color = "#333333"; scroll_color = "#000000"
        self.setStyleSheet(bg_style)
        panel_style = f"QFrame#VolumePanel, QFrame#NavPanel {{ background-color: {panel_bg}; border-radius: 20px; border: 1px solid {shadow_light if self.is_dark_mode else '#ffffff'}; border-bottom: 5px solid {shadow_dark}; border-right: 2px solid {shadow_dark}; }} QFrame#LCDContainer {{ background-color: #000; border-radius: 15px; border: 4px solid {color}; }}"
        self.centralWidget().setStyleSheet(panel_style)
        btn_base = f"QPushButton {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, {btn_grad}); border: 1px solid {shadow_light}; color: {text_color}; font-weight: bold; border-bottom: 4px solid {shadow_dark}; outline: none; }} QPushButton:hover {{ border-color: {color}; }} QPushButton:pressed {{ background: {shadow_dark if self.is_dark_mode else shadow_dark}; border-bottom: 4px solid {shadow_dark}; }}"
        for b in [self.btn_vol_down, self.btn_vol_up, self.btn_back5, self.btn_prev, self.btn_next, self.btn_fwd5]: b.setStyleSheet(btn_base.replace("QPushButton {", "QPushButton { border-radius: 19px;"))
        self.btn_play.setStyleSheet(btn_base.replace("QPushButton {", "QPushButton { border-radius: 32px;"))
        self.btn_play.setText("❚❚" if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState else "▶")
        rect_base = btn_base.replace("QPushButton {", "QPushButton { border-radius: 8px;")
        for b in [self.btn_add, self.btn_theme, self.btn_mode, self.btn_list_toggle, self.btn_shuffle, self.btn_repeat]: b.setStyleSheet(rect_base)
        if self.is_shuffled: self.btn_shuffle.setStyleSheet(rect_base + f"QPushButton {{ color: {color}; border-color: {color}; }}")
        if self.is_repeated: self.btn_repeat.setStyleSheet(rect_base + f"QPushButton {{ color: {color}; border-color: {color}; }}")
        self.search_bar.setStyleSheet(f"background: {panel_bg}; color: {text_color}; border: 2px solid {shadow_dark}; border-radius: 10px; padding: 5px;")
        self.list.setStyleSheet(f"QListWidget {{ background: {panel_bg}; color: {text_color}; border-radius: 15px; border: 2px solid {shadow_dark}; selection-background-color: {color}; padding: 5px; }} QScrollBar:vertical {{ border: none; background: transparent; width: 8px; }} QScrollBar::handle:vertical {{ background: {scroll_color}; border-radius: 4px; }}")
        self.progress_bar.setStyleSheet(f"QSlider::groove:horizontal {{ background: #111; height: 6px; border-radius: 3px; }} QSlider::handle:horizontal {{ background: {color}; width: 16px; margin: -5px 0; border-radius: 8px; border: 1px solid #000; }}")
        self.time_lbl.setStyleSheet(f"color: {color}; font-family: 'Monospace'; font-size: 13px; font-weight: bold;")

    def setup_logic(self):
        self.btn_add.clicked.connect(self.manual_add); self.btn_theme.clicked.connect(self.change_theme); self.btn_mode.clicked.connect(self.toggle_mode)
        self.btn_list_toggle.clicked.connect(lambda: self.toggle_list()); self.btn_shuffle.clicked.connect(self.toggle_shuffle)
        self.btn_repeat.clicked.connect(self.toggle_repeat)
        self.btn_vol_up.clicked.connect(lambda: self.change_volume(5)); self.btn_vol_down.clicked.connect(lambda: self.change_volume(-5))
        self.list.itemDoubleClicked.connect(self.play_file); self.btn_play.clicked.connect(self.toggle_play)
        self.btn_next.clicked.connect(self.next_track); self.btn_prev.clicked.connect(self.prev_track)
        self.btn_back5.clicked.connect(lambda: self.player.setPosition(max(0, self.player.position() - 5000)))
        self.btn_fwd5.clicked.connect(lambda: self.player.setPosition(min(self.player.duration(), self.player.position() + 5000)))
        self.knob.valueChanged.connect(self.update_volume); self.player.positionChanged.connect(self.update_pos); self.player.durationChanged.connect(self.update_dur)
        self.progress_bar.sliderMoved.connect(self.player.setPosition); self.player.playbackStateChanged.connect(self.apply_theme_styles)
        self.player.mediaStatusChanged.connect(self.handle_media_end); self.list.fileDropped.connect(self.handle_dropped_files)
        self.list.deleteRequested.connect(self.remove_selected_item); self.list.clearRequested.connect(self.clear_playlist); self.search_bar.textChanged.connect(self.filter_playlist)
        self.vumeter.modeChanged.connect(lambda: self.save_settings())

    def toggle_shuffle(self): self.is_shuffled = not self.is_shuffled; self.apply_theme_styles(); self.save_settings()
    def toggle_repeat(self): self.is_repeated = not self.is_repeated; self.apply_theme_styles(); self.save_settings()

    def filter_playlist(self, text):
        for i in range(self.list.count()): item = self.list.item(i); item.setHidden(text.lower() not in item.text().lower())

    def handle_media_end(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.is_repeated: self.player.play()
            else: self.next_track()

    def remove_selected_item(self):
        row = self.list.currentRow()
        if row >= 0: self.list.takeItem(row); self.save_settings()

    def clear_playlist(self): self.list.clear(); self.save_settings()

    def manual_add(self):
      files, _ = QFileDialog.getOpenFileNames(self, "Müzik Seç", "", "Ses Dosyaları (*.mp3 *.wav *.flac *.m4a *.mpga *.aac *.ogg *.opus *.wma *.m4b *.aiff *.mid *.amr)")
      if files: 
            for f in files: self.add_to_list(f)
            self.save_settings()

    def handle_dropped_files(self, paths):
        for path in paths:
            if os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for f in sorted(files):
                        if f.lower().endswith(SUPPORTED_FORMATS): self.add_to_list(os.path.join(root, f))
            else:
                if path.lower().endswith(SUPPORTED_FORMATS): self.add_to_list(path)
        self.save_settings()

    def change_theme(self): 
        self.current_theme_idx = (self.current_theme_idx + 1) % len(self.themes)
        self.apply_theme_styles(); self.save_settings()

    def toggle_mode(self):
        self.is_dark_mode = not self.is_dark_mode
        self.btn_mode.setText("☾" if self.is_dark_mode else "☼"); self.apply_theme_styles(); self.save_settings()

    def add_to_list(self, path): 
        item = QListWidgetItem(os.path.basename(path)); item.setData(Qt.ItemDataRole.UserRole, path); self.list.addItem(item)
    def update_volume(self, v): self.audio.setVolume(v/100); self.save_settings()
    def change_volume(self, delta): v = max(0, min(100, self.knob.value + delta)); self.knob.setValue(v); self.update_volume(v)
    
    def play_file(self, item):
        if not item: return
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and os.path.exists(path): 
            self.player.setSource(QUrl.fromLocalFile(path)); self.player.play(); self.title_lbl.setText(os.path.basename(path))
            self.save_settings()

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState: self.player.pause()
        else:
            if not self.player.source().isValid() and self.list.count() > 0:
                if self.list.currentRow() < 0: self.list.setCurrentRow(0)
                self.play_file(self.list.currentItem())
            else: self.player.play()

    def next_track(self):
        if self.list.count() == 0: return
        if self.is_shuffled: idx = random.randint(0, self.list.count() - 1)
        else: idx = (self.list.currentRow() + 1) % self.list.count()
        self.list.setCurrentRow(idx); self.play_file(self.list.currentItem())

    def prev_track(self):
        if self.list.count() == 0: return
        idx = (self.list.currentRow() - 1) % self.list.count()
        self.list.setCurrentRow(idx); self.play_file(self.list.currentItem())

    def update_pos(self, p):
        self.progress_bar.setValue(p); m, s = divmod(p // 1000, 60); td = self.player.duration(); dm, ds = divmod(td // 1000, 60)
        self.time_lbl.setText(f"{m:02}:{s:02} / {dm:02}:{ds:02}")

    def update_dur(self, d): self.progress_bar.setRange(0, d)
    
    def save_settings(self):
        playlist = [self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count())]
        data = {
            "theme_index": self.current_theme_idx, "volume": self.knob.value, "playlist": playlist, 
            "is_dark": self.is_dark_mode, "is_shuffled": self.is_shuffled, "is_repeated": self.is_repeated,
            "is_list_visible": self.is_list_visible, "current_index": self.list.currentRow(), "spectrum_mode": self.vumeter.mode
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)
        except: pass

    def load_settings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.current_theme_idx = data.get("theme_index", 0); self.is_dark_mode = data.get("is_dark", True)
                    self.is_shuffled = data.get("is_shuffled", False); self.is_repeated = data.get("is_repeated", False)
                    self.is_list_visible = data.get("is_list_visible", False)
                    v = data.get("volume", 75); self.knob.setValue(v); self.audio.setVolume(v/100)
                    self.vumeter.mode = data.get("spectrum_mode", 0); self.btn_mode.setText("☾" if self.is_dark_mode else "☼")
                    for path in data.get("playlist", []):
                        if os.path.exists(path): self.add_to_list(path)
                    last_idx = data.get("current_index", -1)
                    if 0 <= last_idx < self.list.count(): self.list.setCurrentRow(last_idx)
            except: pass

    def closeEvent(self, event): self.save_settings(); event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv); QGuiApplication.setDesktopFileName("turkamp.desktop"); app.setStyle("Fusion")
    ex = TurkaPlayer(); ex.show(); sys.exit(app.exec())
