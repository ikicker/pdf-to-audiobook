import sys
import subprocess
import os
import tomllib
from pathlib import Path
from typing import Dict, Any

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLabel, QFileDialog, QComboBox,
                               QProgressBar, QStatusBar, QMessageBox, QTabWidget,
                               QScrollArea, QFrame)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction

# --- MOCK IMPORTS (Keep your actual logic) ---
try:
    from Queue import add_to_queue
except ImportError:
    def add_to_queue(input_file, output_file, voice): pass

try:
    from PDF_to_Audiobook import AudiobookConverter
except ImportError:
    class AudiobookConverter:
        def pdf_to_audio(self, pdf_path, output_path, voice): pass

AVAILABLE_LANGUAGES =["en-US", "en-GB", "es-ES", "fr-FR", "de-DE"]

# --- STYLESHEET TO MATCH VIDEO ---
DARK_THEME_QSS = """
QMainWindow {
    background-color: #111111;
}
QWidget {
    font-family: "Segoe UI", sans-serif;
    color: #e0e0e0;
}
QTabWidget::pane {
    border-top: 1px solid #333333;
    background-color: #111111;
}
QTabBar::tab {
    background: #111111;
    color: #888888;
    padding: 10px 20px;
    font-weight: bold;
    border: none;
}
QTabBar::tab:selected {
    color: #ffb000;
    border-bottom: 2px solid #ffb000;
}
QScrollArea {
    border: none;
    background-color: #111111;
}
QScrollArea > QWidget > QWidget {
    background-color: #111111;
}
QPushButton {
    background-color: #2b2b2b;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    padding: 6px 15px;
    color: #ffffff;
}
QPushButton:hover {
    background-color: #3b3b3b;
}
QPushButton:disabled {
    background-color: #1e1e1e;
    color: #555555;
    border: 1px solid #2b2b2b;
}
QPushButton#actionBtn {
    background-color: #ffb000;
    color: #000000;
    font-weight: bold;
    border: none;
}
QPushButton#actionBtn:hover {
    background-color: #ffc233;
}
QPushButton#actionBtn:disabled {
    background-color: #554011;
    color: #888888;
}
QPushButton#iconBtn {
    background-color: transparent;
    border: none;
    font-size: 16px;
    color: #888888;
}
QPushButton#iconBtn:hover {
    color: #ffffff;
}
QComboBox {
    background-color: #1e1e1e;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    padding: 5px 10px;
    color: #ffffff;
}
QProgressBar {
    border: none;
    background-color: #2b2b2b;
    border-radius: 2px;
    height: 6px;
    text-align: right;
    color: transparent;
}
QProgressBar::chunk {
    background-color: #2ecc71;
    border-radius: 2px;
}
QFrame#queuePanel {
    background-color: #171717;
    border: 1px solid #2b2b2b;
    border-radius: 6px;
}
QFrame#rowFrame {
    border-bottom: 1px solid #2b2b2b;
}
QLabel#headerLabel {
    color: #888888;
    font-weight: bold;
    font-size: 11px;
}
"""

# --- UTILITIES ---
def file_open(file, action, main_window):
    try:
        if sys.platform == "win32":
            os.startfile(file)
        elif sys.platform == "darwin":
            subprocess.call(["open", file])
        else:
            subprocess.call(["xdg-open", file])
    except Exception as e:
        QMessageBox.critical(main_window, "Error", f"Couldn't {action}: {e}")

def file_play(output_sound, action, main_window):
    if action == "open folder":
        file_open(output_sound, action, main_window)
        return
    cfg = load_config()
    ffplay_path = cfg.get("ffplay", "ffplay")
    if os.path.isfile(ffplay_path) or ffplay_path == "ffplay":
        try:
            main_window.statusBar().showMessage(f"Playing audio: {output_sound}")
            subprocess.run([ffplay_path, "-i", output_sound], check=True) 
            main_window.statusBar().showMessage("Done playing audio.")
        except subprocess.CalledProcessError as e:
            main_window.statusBar().showMessage(f"Error playing: {e}")
    else:
        main_window.statusBar().showMessage(f"Warning: ffplay not found.")

AVAILABLE_OPENERS = {"OPEN": file_open, "FFPLAY": file_play}
OPENER = "FFPLAY"

def process_backend(input_file_path, output_file_path, voice):
    subprocess.run(['./audiobook_env/Scripts/python.exe', 'PDF_to_Audiobook.py', input_file_path, output_file_path, '--voice', voice], capture_output=False, text=True)

def library_backend(input_file_path, output_file_path, voice):
    converter = AudiobookConverter()
    converter.pdf_to_audio(pdf_path=input_file_path, output_path=output_file_path, voice=voice)

def queue_backend(input_file_path, output_file_path, voice):
    add_to_queue(input_file_path, output_file_path, voice)

AVAILABLE_BACKENDS = {"PROCESS": process_backend, "LIBRARY": library_backend, "QUEUE": queue_backend}
BACKEND = "QUEUE"

def load_config(config_path: str = "pyproject.toml") -> Dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        data = tomllib.load(f)
    app_config = data.get("tool", {}).get("pdf-to-audiobook", {})
    dropdowns_config = data.get("dropdowns", {})
    external_tools = app_config.get("external_tools", {})
    return {
        "voices": dropdowns_config.get("voices",["af_heart", "am_adam", "am_echo", "am_onyx", "am_nova"]),
        "ffplay": external_tools.get("ffplay", "./ffmpeg/bin/ffplay.exe"),
    }

def get_voices():
    try:
        cfg = load_config()
        return cfg.get("voices",["af_heart", "am_adam", "am_echo", "am_onyx", "am_nova"])
    except:
        return["af_heart", "am_adam", "am_echo", "am_onyx", "am_nova"]


# --- CORE UI WORKERS & MANAGERS ---
class ConversionWorker(QThread):
    progress_update = Signal(int)
    finished_signal = Signal()
    error_signal = Signal(str)

    def __init__(self, input_path, output_path, voice, language, main_window):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.voice = voice
        self.language = language
        self.main_window = main_window

    def run(self):
        try:
            # Replaced with individual sequential handling, is_batch removed to allow the UI to enqueue files individually
            AVAILABLE_BACKENDS[BACKEND](self.input_path, self.output_path, self.voice)
            self.finished_signal.emit()
        except Exception as e:
            self.error_signal.emit(str(e))
            self.progress_update.emit(-1)

class TabQueueManager:
    """Manages sequential execution and visualization of queue items."""
    def __init__(self, layout, empty_label):
        self.queue =[]
        self.layout = layout
        self.empty_label = empty_label
        self.current_running = None

    def add_item(self, item):
        self.empty_label.hide()
        self.layout.addWidget(item)
        self.queue.append(item)
        if not self.current_running:
            self.run_next()

    def run_next(self):
        pending =[i for i in self.queue if i.status == "PENDING"]
        if pending:
            self.current_running = pending[0]
            self.current_running.worker.finished_signal.connect(self.on_item_finished)
            self.current_running.start()
        else:
            self.current_running = None

    def on_item_finished(self):
        self.run_next()

    def clear_all(self):
        items_to_remove = [item for item in self.queue if item.status != "RUNNING"]
        for item in items_to_remove:
            self.queue.remove(item)
            item.setParent(None)
            item.deleteLater()
        if not self.queue:
            self.empty_label.show()


class QueueItem(QFrame):
    def __init__(self, input_path, output_path, voice, main_window, is_folder_output=False):
        super().__init__()
        self.main_window = main_window
        self.output_path = output_path
        self.is_folder_output = is_folder_output
        self.status = "PENDING"
        self.setObjectName("rowFrame")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)

        self.lbl_in = QLabel(os.path.basename(input_path))
        self.lbl_out = QLabel(os.path.basename(output_path))
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        
        self.lbl_status = QLabel()
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.set_status_style("PENDING")
        
        self.btn_remove = QPushButton("✖")
        self.btn_remove.setObjectName("iconBtn")
        self.btn_remove.clicked.connect(self.remove_self)

        layout.addWidget(self.lbl_in, 3)
        layout.addWidget(self.lbl_out, 3)
        layout.addWidget(self.progress_bar, 3)
        layout.addWidget(self.lbl_status, 1)
        layout.addWidget(self.btn_remove, 1)

        self.worker = ConversionWorker(input_path, output_path, voice, main_window.get_selected_language(), main_window)
        self.worker.progress_update.connect(self.update_progress)
        self.worker.finished_signal.connect(self.finished)

    def set_status_style(self, status):
        self.status = status
        self.lbl_status.setText(status)
        if status == "PENDING":
            self.lbl_status.setStyleSheet("background-color: #333333; color: #aaaaaa; padding: 4px; border-radius: 4px; font-weight: bold; font-size: 10px;")
        elif status == "RUNNING":
            self.lbl_status.setStyleSheet("background-color: #554011; color: #ffb000; padding: 4px; border-radius: 4px; font-weight: bold; font-size: 10px;")
        elif status == "DONE":
            self.lbl_status.setStyleSheet("background-color: #113311; color: #2ecc71; padding: 4px; border-radius: 4px; font-weight: bold; font-size: 10px;")

    def start(self):
        self.set_status_style("RUNNING")
        self.btn_remove.setEnabled(False)
        self.worker.start()

    def update_progress(self, val):
        if val >= 0:
            self.progress_bar.setValue(val)

    def finished(self):
        self.progress_bar.setValue(100)
        self.set_status_style("DONE")
        self.btn_remove.setText("📂" if self.is_folder_output else "🎵")
        self.btn_remove.clicked.disconnect()
        self.btn_remove.clicked.connect(self.play_or_open)
        self.btn_remove.setEnabled(True)

    def remove_self(self):
        self.status = "REMOVED"
        self.setParent(None)
        self.deleteLater()

    def play_or_open(self):
        action = "open folder" if self.is_folder_output else "play sound file"
        opener_target = os.path.dirname(self.output_path) if self.is_folder_output else self.output_path
        AVAILABLE_OPENERS["OPEN" if self.is_folder_output else OPENER](opener_target, action, self.main_window)


# --- TAB VIEWS & ROWS ---
class SingleFileRow(QFrame):
    def __init__(self, main_window, parent_tab):
        super().__init__()
        self.main_window = main_window
        self.parent_tab = parent_tab
        self.setObjectName("rowFrame")
        self.input_path = ""
        self.output_path = ""
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        
        self.btn_input = QPushButton("Select PDF...")
        self.btn_input.setStyleSheet("text-align: left;")
        self.btn_input.clicked.connect(self.select_input)
        
        self.combo_voice = QComboBox()
        self.combo_voice.addItems(get_voices())
        self.combo_voice.currentTextChanged.connect(self.validate)
        
        self.btn_output = QPushButton("Save as...")
        self.btn_output.setStyleSheet("text-align: left;")
        self.btn_output.clicked.connect(self.select_output)
        
        progress_layout = QHBoxLayout()
        progress_layout.setContentsMargins(0, 0, 0, 0)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        self.lbl_progress = QLabel("-")
        self.lbl_progress.setStyleSheet("color: #888888;")
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.lbl_progress)
        progress_widget = QWidget()
        progress_widget.setLayout(progress_layout)
        
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_action = QPushButton("▶")
        self.btn_action.setObjectName("actionBtn")
        self.btn_action.setFixedSize(32, 32)
        self.btn_action.setEnabled(False)
        self.btn_action.clicked.connect(self.do_action)
        
        self.btn_remove = QPushButton("✖")
        self.btn_remove.setObjectName("iconBtn")
        self.btn_remove.clicked.connect(self.remove_self)
        
        actions_layout.addWidget(self.btn_action)
        actions_layout.addWidget(self.btn_remove)
        actions_widget = QWidget()
        actions_widget.setLayout(actions_layout)

        layout.addWidget(self.btn_input, 3)
        layout.addWidget(self.combo_voice, 2)
        layout.addWidget(self.btn_output, 3)
        layout.addWidget(progress_widget, 2)
        layout.addWidget(actions_widget, 1)

    def select_input(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Input", "", "PDF Files (*.pdf)")
        if path:
            self.input_path = path
            self.btn_input.setText(os.path.basename(path))
            self.validate()

    def select_output(self):
        path, _ = QFileDialog.getSaveFileName(self, "Select Output", "", "Audio Files (*.mp3 *.wav)")
        if path:
            self.output_path = path
            self.btn_output.setText(os.path.basename(path))
            self.validate()

    def validate(self):
        is_ready = bool(self.input_path and self.output_path)
        self.btn_action.setEnabled(is_ready)

    def do_action(self):
        if self.btn_action.text() == "▶":
            self.start_conversion()
        else:
            AVAILABLE_OPENERS[OPENER](self.output_path, "play sound file", self.main_window)

    def start_conversion(self):
        self.btn_action.setEnabled(False)
        self.btn_input.setEnabled(False)
        self.combo_voice.setEnabled(False)
        self.btn_output.setEnabled(False)
        self.lbl_progress.setText("Queued...")
        self.progress_bar.show()
        
        queue_item = QueueItem(self.input_path, self.output_path, self.combo_voice.currentText(), self.main_window)
        queue_item.worker.progress_update.connect(self.update_progress)
        queue_item.worker.finished_signal.connect(self.conversion_done)
        self.parent_tab.queue_manager.add_item(queue_item)

    def update_progress(self, val):
        if val >= 0:
            self.progress_bar.setValue(val)
            self.lbl_progress.setText(f"{val}%")

    def conversion_done(self):
        self.progress_bar.setValue(100)
        self.lbl_progress.setText("100% DONE")
        self.lbl_progress.setStyleSheet("color: #2ecc71;")
        self.btn_action.setText("🎵")
        self.btn_action.setEnabled(True)

    def remove_self(self):
        self.setParent(None)
        self.deleteLater()

class BatchFileRow(QFrame):
    def __init__(self, main_window, parent_tab):
        super().__init__()
        self.main_window = main_window
        self.parent_tab = parent_tab
        self.setObjectName("rowFrame")
        self.input_path = ""
        self.output_path = ""
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        
        self.btn_input = QPushButton("Select input folder...")
        self.btn_input.setStyleSheet("text-align: left;")
        self.btn_input.clicked.connect(self.select_input)
        
        self.combo_voice = QComboBox()
        self.combo_voice.addItems(get_voices())
        self.combo_voice.currentTextChanged.connect(self.validate)
        
        self.btn_output = QPushButton("Select output folder...")
        self.btn_output.setStyleSheet("text-align: left;")
        self.btn_output.clicked.connect(self.select_output)
        
        progress_layout = QHBoxLayout()
        progress_layout.setContentsMargins(0, 0, 0, 0)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        self.lbl_progress = QLabel("-")
        self.lbl_progress.setStyleSheet("color: #888888;")
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.lbl_progress)
        progress_widget = QWidget()
        progress_widget.setLayout(progress_layout)
        
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_action = QPushButton("▶ ALL")
        self.btn_action.setObjectName("actionBtn")
        self.btn_action.setFixedHeight(32)
        self.btn_action.setFixedWidth(60)
        self.btn_action.setEnabled(False)
        self.btn_action.clicked.connect(self.do_action)
        
        self.btn_remove = QPushButton("✖")
        self.btn_remove.setObjectName("iconBtn")
        self.btn_remove.clicked.connect(self.remove_self)
        
        actions_layout.addWidget(self.btn_action)
        actions_layout.addWidget(self.btn_remove)
        actions_widget = QWidget()
        actions_widget.setLayout(actions_layout)

        layout.addWidget(self.btn_input, 3)
        layout.addWidget(self.combo_voice, 2)
        layout.addWidget(self.btn_output, 3)
        layout.addWidget(progress_widget, 2)
        layout.addWidget(actions_widget, 1)

    def select_input(self):
        path = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if path:
            self.input_path = path
            self.btn_input.setText(os.path.basename(path) or path)
            self.validate()

    def select_output(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if path:
            self.output_path = path
            self.btn_output.setText(os.path.basename(path) or path)
            self.validate()

    def validate(self):
        self.btn_action.setEnabled(bool(self.input_path and self.output_path))

    def do_action(self):
        if "ALL" in self.btn_action.text():
            self.start_conversion()
        else:
            AVAILABLE_OPENERS["OPEN"](self.output_path, "open folder", self.main_window)

    def start_conversion(self):
        self.btn_action.setEnabled(False)
        self.btn_input.setEnabled(False)
        self.combo_voice.setEnabled(False)
        self.btn_output.setEnabled(False)
        self.lbl_progress.setText("Queued...")
        self.progress_bar.show()
        
        try:
            filenames =[f for f in os.listdir(self.input_path) if f.lower().endswith('.pdf')]
        except Exception:
            filenames =[]

        if not filenames:
            self.lbl_progress.setText("No PDFs found")
            return

        self.total_files = len(filenames)
        self.files_done = 0

        for filename in filenames:
            in_file = os.path.join(self.input_path, filename)
            base_name = os.path.splitext(filename)[0]
            out_file = os.path.join(self.output_path, base_name + ".mp3")
            
            queue_item = QueueItem(in_file, out_file, self.combo_voice.currentText(), self.main_window, is_folder_output=True)
            queue_item.worker.finished_signal.connect(self.one_file_done)
            self.parent_tab.queue_manager.add_item(queue_item)

    def one_file_done(self):
        self.files_done += 1
        pct = int((self.files_done / self.total_files) * 100)
        self.progress_bar.setValue(pct)
        self.lbl_progress.setText(f"{pct}%")
        if self.files_done >= self.total_files:
            self.lbl_progress.setText("100% DONE")
            self.lbl_progress.setStyleSheet("color: #2ecc71;")
            self.btn_action.setText("📂")
            self.btn_action.setEnabled(True)

    def remove_self(self):
        self.setParent(None)
        self.deleteLater()

class BaseConversionTab(QWidget):
    def __init__(self, main_window, row_class, row_headers):
        super().__init__()
        self.main_window = main_window
        self.row_class = row_class
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(10)

        # Header Row
        header_layout = QHBoxLayout()
        widths = [3, 2, 3, 2, 1]
        for h, w in zip(row_headers, widths):
            lbl = QLabel(h)
            lbl.setObjectName("headerLabel")
            header_layout.addWidget(lbl, w)
        self.layout.addLayout(header_layout)

        # Rows layout
        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(0)
        self.layout.addLayout(self.rows_layout)
        self.add_row()

        # Add Row Button
        self.btn_add = QPushButton("➕ Add conversion")
        self.btn_add.setObjectName("iconBtn")
        self.btn_add.clicked.connect(self.add_row)
        add_layout = QHBoxLayout()
        add_layout.addWidget(self.btn_add)
        add_layout.addStretch()
        self.layout.addLayout(add_layout)

        self.layout.addSpacing(20)

        # Queue Header
        queue_header_layout = QHBoxLayout()
        queue_header = QLabel("QUEUE")
        queue_header.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
        btn_clear = QPushButton("CLEAR ALL")
        btn_clear.setObjectName("iconBtn")
        
        queue_header_layout.addWidget(queue_header)
        queue_header_layout.addStretch()
        queue_header_layout.addWidget(btn_clear)
        self.layout.addLayout(queue_header_layout)

        # Queue Panel
        self.queue_panel = QFrame()
        self.queue_panel.setObjectName("queuePanel")
        queue_container_layout = QVBoxLayout(self.queue_panel)

        self.queue_scroll = QScrollArea()
        self.queue_scroll.setWidgetResizable(True)
        self.queue_content = QWidget()
        self.queue_layout = QVBoxLayout(self.queue_content)
        self.queue_layout.setAlignment(Qt.AlignTop)
        
        self.empty_queue_label = QLabel("No jobs queued")
        self.empty_queue_label.setStyleSheet("color: #555555;")
        self.empty_queue_label.setAlignment(Qt.AlignCenter)
        self.queue_layout.addWidget(self.empty_queue_label)
        
        self.queue_scroll.setWidget(self.queue_content)
        queue_container_layout.addWidget(self.queue_scroll)
        self.layout.addWidget(self.queue_panel, stretch=1)

        self.queue_manager = TabQueueManager(self.queue_layout, self.empty_queue_label)
        btn_clear.clicked.connect(self.queue_manager.clear_all)

    def add_row(self):
        row = self.row_class(self.main_window, self)
        self.rows_layout.addWidget(row)


# --- MAIN WINDOW ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF to Audiobook Converter")
        self.setGeometry(100, 100, 1050, 700)
        self.setStyleSheet(DARK_THEME_QSS)

        self.setup_menu()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(20)

        # Header Title Area
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(10, 5, 10, 0)
        title_label = QLabel("🎧 PDF TO AUDIOBOOK")
        title_label.setStyleSheet("color: #ffb000; font-size: 18px; font-weight: bold;")
        subtitle_label = QLabel("KOKORO TTS : KOKORO")
        subtitle_label.setStyleSheet("color: #888888; font-size: 11px;")
        
        header_layout.addWidget(title_label)
        header_layout.addSpacing(10)
        header_layout.addWidget(subtitle_label)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # Tabs Setup
        self.tab_widget = QTabWidget() 
        self.single_file_tab = BaseConversionTab(self, SingleFileRow,["INPUT PDF", "VOICE", "OUTPUT FILE", "PROGRESS", "ACTIONS"])
        self.batch_file_tab = BaseConversionTab(self, BatchFileRow,["INPUT FOLDER", "VOICE", "OUTPUT FOLDER", "PROGRESS", "ACTIONS"])

        self.tab_widget.addTab(self.single_file_tab, "SINGLE FILE")
        self.tab_widget.addTab(self.batch_file_tab, "BATCH")
        main_layout.addWidget(self.tab_widget)

        # Status Bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("background-color: #111111; color: #888888; border-top: 1px solid #222222;")
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        help_menu = menubar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def show_about(self):
        QMessageBox.about(self, "About", "PDF to Sounds Conversion Application\nVersion 1.0")

    def get_selected_language(self):
        return "en-US"

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
