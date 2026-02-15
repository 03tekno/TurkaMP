import sys
import os
import random
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFrame, QFileDialog, 
                             QListWidget, QSlider, QListWidgetItem, QMenu, QLineEdit) # QLineEdit eklendi
from PyQt6.QtCore import Qt, QRect, QPointF, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QAction, QPainter, QColor, QLinearGradient, QPen, QFont, QFontMetrics
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".turka_music_config.json")
SUPPORTED_FORMATS = ('.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.opus', '.wma', '.m4b', '.aiff', '.mid', '.amr')

class DragDropList(QListWidget):
    fileDropped = pyqtSignal(list)
    deleteRequested = pyqtSignal()
    clearRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
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
    def __init__(self, player):
        super().__init__(); self.player = player; self.color = QColor("#00e676")
        self.timer = QTimer(); self.timer.timeout.connect(self.update); self.timer.start(50)

    def paintEvent(self, event):
        painter = QPainter(self); painter.fillRect(self.rect(), QColor("#000000"))
        if self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState: return
        bars = 40; w = self.width() / bars
        for i in range(bars):
            h = random.randint(5, self.height() - 10)
            grad = QLinearGradient(QPointF(0, float(self.height())), QPointF(0, 0.0))
            grad.setColorAt(0, self.color); grad.setColorAt(1, QColor("#FFFFFF"))
            painter.setBrush(grad); painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(int(i*w), self.height()-h, int(w-2), h)

class TurkaPlayer(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("Turka Music Player")
        self.player = QMediaPlayer(); self.audio = QAudioOutput(); self.player.setAudioOutput(self.audio)
        self.is_dark_mode = True
        self.is_shuffled = False
        self.is_repeated = False
        self.themes = ["#00e676", "#00b0ff", "#ff3d00", "#d4af37", "#bd93f9", "#ff79c6", "#8be9fd", "#50fa7b", "#ffb86c", "#ff5555", "#f1fa8c", "#00d2ff", "#9c27b0", "#76ff03", "#ffffff"]
        self.current_theme_idx = 0
        screen = QApplication.primaryScreen().size(); self.setFixedSize(420, int(screen.height() * 0.70))
        self.init_ui(); self.load_settings(); self.setup_logic(); self.apply_theme_styles()

    def init_ui(self):
        main = QWidget(); self.setCentralWidget(main); layout = QVBoxLayout(main); layout.setSpacing(8)
        lcd = QFrame(); lcd.setObjectName("LCDContainer"); lcd.setFixedHeight(220) 
        lcd_lyt = QVBoxLayout(lcd); lcd_lyt.setContentsMargins(12, 10, 12, 10)
        self.title_lbl = ScrollingLabel("Turka Music Player - Hazır"); lcd_lyt.addWidget(self.title_lbl)
        self.vumeter = ModernSpectrum(self.player); lcd_lyt.addWidget(self.vumeter, stretch=4)
        self.time_lbl = QLabel("00:00 / 00:00"); self.time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); self.time_lbl.setFixedHeight(30)
        lcd_lyt.addWidget(self.time_lbl); self.progress_bar = QSlider(Qt.Orientation.Horizontal); lcd_lyt.addWidget(self.progress_bar)
        layout.addWidget(lcd)

        top_btn_layout = QHBoxLayout()
        self.btn_add = self.create_rect_btn("Liste +", 75, 30)
        self.btn_shuffle = self.create_rect_btn("Karıştır", 70, 30)
        self.btn_mode = self.create_rect_btn("☾", 40, 30)
        self.btn_repeat = self.create_rect_btn("Tekrarla", 70, 30)
        self.btn_theme = self.create_rect_btn("Tema", 65, 30)
        
        top_btn_layout.addWidget(self.btn_add)
        top_btn_layout.addStretch()
        top_btn_layout.addWidget(self.btn_shuffle)
        top_btn_layout.addWidget(self.btn_mode)
        top_btn_layout.addWidget(self.btn_repeat)
        top_btn_layout.addStretch()
        top_btn_layout.addWidget(self.btn_theme)
        layout.addLayout(top_btn_layout)

        # Arama Çubuğu Eklendi
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Parçalarda ara...")
        self.search_bar.setFixedHeight(30)
        layout.addWidget(self.search_bar)

        self.list = DragDropList(); layout.addWidget(self.list, stretch=5)
        
        volume_layout = QHBoxLayout(); volume_layout.setAlignment(Qt.AlignmentFlag.AlignCenter); volume_layout.setSpacing(12)
        self.btn_vol_down = self.create_circle_btn("-", 38); self.knob = ProVolumeKnob(); self.btn_vol_up = self.create_circle_btn("+", 38)
        volume_layout.addWidget(self.btn_vol_down); volume_layout.addWidget(self.knob); volume_layout.addWidget(self.btn_vol_up); layout.addLayout(volume_layout)
        
        nav_layout = QHBoxLayout(); nav_layout.setSpacing(12); nav_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_back5 = self.create_circle_btn("⟲", 40)
        self.btn_prev = self.create_circle_btn("◀", 48)
        self.btn_play = self.create_circle_btn("▶", 65)
        self.btn_next = self.create_circle_btn("▶", 48)
        self.btn_fwd5 = self.create_circle_btn("⟳", 40)
        for b in [self.btn_back5, self.btn_prev, self.btn_play, self.btn_next, self.btn_fwd5]: nav_layout.addWidget(b)
        layout.addLayout(nav_layout); layout.addStretch()

    def create_circle_btn(self, text, size): btn = QPushButton(text); btn.setFixedSize(size, size); return btn
    def create_rect_btn(self, text, w, h): btn = QPushButton(text); btn.setFixedSize(w, h); return btn

    def toggle_mode(self):
        self.is_dark_mode = not self.is_dark_mode
        self.btn_mode.setText("☾" if self.is_dark_mode else "☼")
        self.apply_theme_styles()

    def apply_theme_styles(self):
        color = self.themes[self.current_theme_idx]; qcolor = QColor(color)
        self.knob.is_dark = self.is_dark_mode; self.knob.color = qcolor; self.vumeter.color = qcolor

        if self.is_dark_mode:
            bg_style = "QMainWindow { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2c3e50, stop:0.5 #1a1a1a, stop:1 #000000); }"
            lcd_border = "#34495e"; list_bg = "#121212"; list_text = "#eceff1"; btn_grad = "stop:0 #455a64, stop:1 #263238"; btn_text = "#ffffff"
            scroll_handle_color = "#FFFFFF"; scroll_bg_color = "#1e1e1e"
            search_style = f"QLineEdit {{ background: #1a1a1a; color: white; border: 1px solid {lcd_border}; border-radius: 6px; padding-left: 8px; }}"
        else:
            bg_style = "QMainWindow { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #cfd8dc, stop:0.5 #ffffff, stop:1 #b0bec5); }"
            lcd_border = "#78909c"; list_bg = "#fdfdfd"; list_text = "#2d3436"; btn_grad = "stop:0 #eceff1, stop:1 #cfd8dc"; btn_text = "#37474f"
            scroll_handle_color = "#000000"; scroll_bg_color = "#e0e0e0"
            search_style = f"QLineEdit {{ background: #ffffff; color: black; border: 1px solid {lcd_border}; border-radius: 6px; padding-left: 8px; }}"

        self.setStyleSheet(bg_style)
        self.findChild(QFrame, "LCDContainer").setStyleSheet(f"background: #000; border-radius: 12px; border: 3px solid {lcd_border};")
        self.search_bar.setStyleSheet(search_style)
        
        scrollbar_style = f"QScrollBar:vertical {{ background: {scroll_bg_color}; width: 10px; margin: 0px; border-radius: 5px; }} QScrollBar::handle:vertical {{ background: {scroll_handle_color}; min-height: 20px; border-radius: 5px; }} QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}"
        
        self.list.setStyleSheet(f"QListWidget {{ background: {list_bg}; color: {list_text}; border: 1px solid {lcd_border}; border-radius: 12px; outline: none; }} QListWidget::item:selected {{ background: {color}; color: black; font-weight: bold; border-radius: 6px; }} {scrollbar_style}")
        
        circle_style = f"QPushButton {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, {btn_grad}); border: 1px solid #90a4ae; border-radius: 19px; color: {btn_text}; font-weight: bold; }} QPushButton:hover {{ background: {'#ffffff' if not self.is_dark_mode else '#37474f'}; }}"
        for b in [self.btn_vol_down, self.btn_vol_up, self.btn_back5, self.btn_prev, self.btn_next, self.btn_fwd5]: b.setStyleSheet(circle_style)
        self.btn_play.setStyleSheet(circle_style.replace("19px", "32px")); self.btn_play.setText("‖" if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState else "▶")

        rect_btn_style = f"QPushButton {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, {btn_grad}); border: 1px solid #adb5bd; border-radius: 6px; color: {btn_text}; font-weight: bold; font-size: 10px; }} QPushButton:hover {{ border-color: {color}; }}"
        for b in [self.btn_add, self.btn_theme, self.btn_mode]: b.setStyleSheet(rect_btn_style)
        
        shuf_s = rect_btn_style + (f"QPushButton {{ color: {color}; border: 2px solid {color}; }}" if self.is_shuffled else "")
        rep_s = rect_btn_style + (f"QPushButton {{ color: {color}; border: 2px solid {color}; }}" if self.is_repeated else "")
        self.btn_shuffle.setStyleSheet(shuf_s); self.btn_repeat.setStyleSheet(rep_s)

        self.progress_bar.setStyleSheet(f"QSlider::groove:horizontal {{ background: #111; height: 4px; }} QSlider::handle:horizontal {{ background: {color}; width: 14px; margin: -5px 0; border-radius: 7px; }}")
        self.time_lbl.setStyleSheet(f"color: {color}; font-family: 'Monospace'; font-size: 14px; font-weight: bold;")

    def setup_logic(self):
        self.btn_add.clicked.connect(self.manual_add); self.btn_theme.clicked.connect(self.change_theme); self.btn_mode.clicked.connect(self.toggle_mode)
        self.btn_shuffle.clicked.connect(self.toggle_shuffle); self.btn_repeat.clicked.connect(self.toggle_repeat)
        self.btn_vol_up.clicked.connect(lambda: self.change_volume(5)); self.btn_vol_down.clicked.connect(lambda: self.change_volume(-5))
        self.list.itemDoubleClicked.connect(self.play_file); self.btn_play.clicked.connect(self.toggle_play)
        self.btn_next.clicked.connect(self.next_track); self.btn_prev.clicked.connect(self.prev_track)
        self.btn_back5.clicked.connect(lambda: self.player.setPosition(max(0, self.player.position() - 5000)))
        self.btn_fwd5.clicked.connect(lambda: self.player.setPosition(min(self.player.duration(), self.player.position() + 5000)))
        self.knob.valueChanged.connect(lambda v: self.audio.setVolume(v/100))
        self.player.positionChanged.connect(self.update_pos); self.player.durationChanged.connect(self.update_dur)
        self.progress_bar.sliderMoved.connect(self.player.setPosition); self.player.playbackStateChanged.connect(self.apply_theme_styles)
        self.player.mediaStatusChanged.connect(self.handle_media_end)
        self.list.fileDropped.connect(self.handle_dropped_files)
        self.list.deleteRequested.connect(self.remove_selected_item); self.list.clearRequested.connect(self.clear_playlist)
        # Arama fonksiyonu bağlandı
        self.search_bar.textChanged.connect(self.filter_playlist)

    def filter_playlist(self, text):
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def toggle_shuffle(self): self.is_shuffled = not self.is_shuffled; self.apply_theme_styles()
    def toggle_repeat(self): self.is_repeated = not self.is_repeated; self.apply_theme_styles()
    def handle_media_end(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.is_repeated: self.player.play()
            else: self.next_track()

    def remove_selected_item(self):
        row = self.list.currentRow()
        if row >= 0: self.list.takeItem(row); self.save_settings()

    def clear_playlist(self): self.list.clear(); self.save_settings()

    def manual_add(self):
      files, _ = QFileDialog.getOpenFileNames(self, "Müzik Seç", "", "Ses Dosyaları (*.mp3 *.wav *.flac *.m4a *.aac *.ogg *.opus *.wma *.m4b *.aiff *.mid *.amr)")
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

    def change_theme(self): self.current_theme_idx = (self.current_theme_idx + 1) % len(self.themes); self.apply_theme_styles()
    def add_to_list(self, path): item = QListWidgetItem(os.path.basename(path)); item.setData(Qt.ItemDataRole.UserRole, path); self.list.addItem(item)
    def change_volume(self, delta): v = max(0, min(100, self.knob.value + delta)); self.knob.setValue(v); self.audio.setVolume(v/100)
    
    def play_file(self, item):
        if not item: return
        path = item.data(Qt.ItemDataRole.UserRole)
        if path: self.player.setSource(QUrl.fromLocalFile(path)); self.player.play(); self.title_lbl.setText(os.path.basename(path))

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState: self.player.pause()
        else:
            if not self.player.source().isValid() and self.list.count() > 0:
                self.list.setCurrentRow(0); self.play_file(self.list.currentItem())
            else: self.player.play()

    def next_track(self):
        if self.list.count() == 0: return
        # Sadece görünür (filtrelenmemiş) parçalar arasından seçim yapmak için mantık eklenebilir ancak basitlik için mevcut mantık korundu.
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
        data = {"theme_index": self.current_theme_idx, "volume": self.knob.value, "playlist": playlist, "is_dark": self.is_dark_mode}
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(data, f)
        except: pass

    def load_settings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f); self.current_theme_idx = data.get("theme_index", 0); self.is_dark_mode = data.get("is_dark", True)
                    v = data.get("volume", 75); self.knob.setValue(v); self.audio.setVolume(v/100)
                    self.btn_mode.setText("☾" if self.is_dark_mode else "☼")
                    for path in data.get("playlist", []):
                        if os.path.exists(path): self.add_to_list(path)
            except: pass

    def closeEvent(self, event): self.save_settings(); event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv); app.setStyle("Fusion"); ex = TurkaPlayer(); ex.show(); sys.exit(app.exec())
