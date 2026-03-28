import sys
import subprocess
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLabel, QLineEdit, QTableWidget,
                               QTableWidgetItem, QFileDialog, QComboBox,
                               QProgressBar, QStatusBar, QMessageBox, QTabWidget,
                               QAbstractItemView, QHeaderView, QMenuBar, QMenu)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction

from PDF_to_Audiobook import AudiobookConverter
import tomllib
from pathlib import Path
from typing import Dict, Any

# Mock list of voices and languages (replace with actual dynamic population later)
# AVAILABLE_VOICES =["Default Voice", "am_adam", "am_echo", "am_onyx", "am_nova"]
AVAILABLE_LANGUAGES =["en-US", "en-GB", "es-ES", "fr-FR", "de-DE"]

class ConversionWorker(QThread):
    """
    Worker thread to handle PDF conversion in the background.
    """
    progress_update = Signal(int)  # Signal for progress updates (0-100)
    finished_signal = Signal()     # Signal when finished
    error_signal = Signal(str)     # Signal for errors

    def __init__(self, input_path, output_path, voice, language, is_batch=False):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.voice = voice
        self.language = language
        self.is_batch = is_batch
        self.converter = AudiobookConverter()

    def run(self):
        try:
            # --- MOCK CONVERSION PROCESS ---
            # Replace the sleep and loop with actual library calls
            #import time
            #for i in range(1, 101, 20):
            #    time.sleep(0.5) # Simulate work
            #    self.progress_update.emit(i)
            
            if self.is_batch:
                # Logic to iterate over folder and convert all pdfs
                pass
            else:
                self.converter.pdf_to_audio(pdf_path=self.input_path, output_path=self.output_path, voice=self.voice)
            
            self.finished_signal.emit() # Signal completion
        except Exception as e:
            self.error_signal.emit(str(e))
            self.progress_update.emit(-1)  # Indicate error with -1


class PathSelectionWidget(QWidget):
    """
    Custom widget combining a read-only QLineEdit and a Browse QPushButton.
    """
    path_changed = Signal(str)

    def __init__(self, mode="file_open", filter_string="", parent=None):
        super().__init__(parent)
        self.mode = mode
        self.filter_string = filter_string

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.line_edit = QLineEdit()
        self.line_edit.setReadOnly(True)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse)

        layout.addWidget(self.line_edit)
        layout.addWidget(self.browse_btn)
        self.setLayout(layout)

    def browse(self):
        path = ""
        if self.mode == "file_open":
            path, _ = QFileDialog.getOpenFileName(self, "Select Input", "", self.filter_string)
        elif self.mode == "file_save":
            path, _ = QFileDialog.getSaveFileName(self, "Select Output", "", self.filter_string)
        elif self.mode == "directory":
            path = QFileDialog.getExistingDirectory(self, "Select Directory")

        if path:
            self.line_edit.setText(path)
            self.path_changed.emit(path)

    def text(self):
        return self.line_edit.text()


class BaseConversionTable(QWidget):
    """
    Base class containing common logic for both Single File and Batch tables.
    """
    def __init__(self, main_window):
        super().__init__()
        self.converter = AudiobookConverter()
        self.main_window = main_window

        self.tableWidget = QTableWidget()
        self.tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        add_row_button = QPushButton("Add Row")
        remove_row_button = QPushButton("Remove Row")

        add_row_button.clicked.connect(self.add_row)
        remove_row_button.clicked.connect(self.remove_row)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.tableWidget)

        button_layout = QHBoxLayout()
        button_layout.addWidget(add_row_button)
        button_layout.addWidget(remove_row_button)
        self.layout.addLayout(button_layout)

        self.setLayout(self.layout)

    def remove_row(self):
        selected_rows = self.tableWidget.selectionModel().getSelectedRows()
        for row in reversed(selected_rows):  # Remove from bottom to avoid index issues
            self.tableWidget.removeRow(row.row())

    def get_widget_row(self, widget):
        """Helper to find which row a widget belongs to."""
        for row in range(self.tableWidget.rowCount()):
            for col in range(self.tableWidget.columnCount()):
                if self.tableWidget.cellWidget(row, col) == widget:
                    return row
        return -1


class SingleFileConversionTable(BaseConversionTable):
    def __init__(self, main_window):
        super().__init__(main_window)
        
        self.tableWidget.setColumnCount(5)
        self.tableWidget.setHorizontalHeaderLabels(["Input PDF", "Voice Choice", "Output Sound", "Launch Conversion", "Launch Sound"]
        )
        self.converter = AudiobookConverter()

    def add_row(self):
        row_count = self.tableWidget.rowCount()
        self.tableWidget.insertRow(row_count)

        # 1. Input PDF (PathSelectionWidget)
        input_widget = PathSelectionWidget("file_open", "PDF Files (*.pdf)")
        
        # 2. Voice Choice (QComboBox)
        self.cfg = load_config(config_path="pyproject.toml")
        voices = self.cfg["voices"]
        print(voices)

        voice_combo = QComboBox()
        voice_combo.addItems(voices)
        
        # 3. Output Sound (PathSelectionWidget)
        output_widget = PathSelectionWidget("file_save", "Audio Files (*.mp3 *.wav)")
        
        # 4 & 5. Buttons
        launch_conversion_btn = QPushButton("Launch")
        launch_conversion_btn.setEnabled(False) # Disabled initially
        
        launch_sound_btn = QPushButton("Play")
        launch_sound_btn.setEnabled(False) # Disabled initially

        # Insert widgets into table
        self.tableWidget.setCellWidget(row_count, 0, input_widget)
        self.tableWidget.setCellWidget(row_count, 1, voice_combo)
        self.tableWidget.setCellWidget(row_count, 2, output_widget)
        self.tableWidget.setCellWidget(row_count, 3, launch_conversion_btn)
        self.tableWidget.setCellWidget(row_count, 4, launch_sound_btn)

        # Connect Validation Signals
        input_widget.path_changed.connect(lambda: self.validate_row(input_widget))
        voice_combo.currentTextChanged.connect(lambda: self.validate_row(voice_combo))
        output_widget.path_changed.connect(lambda: self.validate_row(output_widget))

        # Connect Action Signals
        launch_conversion_btn.clicked.connect(lambda: self.launch_conversion(launch_conversion_btn))
        launch_sound_btn.clicked.connect(lambda: self.launch_sound(launch_sound_btn))

    def validate_row(self, sender_widget):
        row = self.get_widget_row(sender_widget)
        if row == -1: return

        input_path = self.tableWidget.cellWidget(row, 0).text()
        voice = self.tableWidget.cellWidget(row, 1).currentText()
        output_path = self.tableWidget.cellWidget(row, 2).text()
        
        launch_btn = self.tableWidget.cellWidget(row, 3)
        
        # Enable if Input and Voice are valid (we also mandate Output here to be safe)
        is_ready = bool(input_path) and bool(voice) and bool(output_path)
        launch_btn.setEnabled(is_ready)

    def launch_conversion(self, button):
        row = self.get_widget_row(button)
        if row == -1: return

        input_pdf = self.tableWidget.cellWidget(row, 0).text()
        voice = self.tableWidget.cellWidget(row, 1).currentText()
        output_sound = self.tableWidget.cellWidget(row, 2).text()

        self.main_window.statusBar().showMessage(f"Conversion started for {os.path.basename(input_pdf)}...")
        self.tableWidget.cellWidget(row, 3).setEnabled(False) # Disable launch button during conversion

        # Start conversion thread
        self.worker = ConversionWorker(input_pdf, output_sound, voice, self.main_window.get_selected_language())
        self.worker.progress_update.connect(self.main_window.update_progress)
        self.worker.error_signal.connect(self.main_window.show_error)
        self.worker.finished_signal.connect(lambda r=row: self.conversion_completed(r))
        self.worker.start()

    def conversion_completed(self, row):
        self.main_window.statusBar().showMessage("Conversion completed successfully!")
        self.main_window.progress_bar.setValue(100)
        QMessageBox.information(self.main_window, "Success", "Single file conversion completed successfully!")
        
        # Re-enable Launch button, enable Play button
        self.tableWidget.cellWidget(row, 3).setEnabled(True)
        self.tableWidget.cellWidget(row, 4).setEnabled(True)

    def launch_sound(self, button):
        row = self.get_widget_row(button)
        if row == -1: return

        output_sound = self.tableWidget.cellWidget(row, 2).text()
        if not output_sound: # Mock file check bypass for demo: or not os.path.exists(output_sound):
            QMessageBox.warning(self.main_window, "Warning", "Invalid output file path or file does not exist.")
            return

        try:
            if sys.platform == "win32":
                os.startfile(output_sound)
            elif sys.platform == "darwin":
                subprocess.call(["open", output_sound])
            else:
                subprocess.call(["xdg-open", output_sound])
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Could not play sound file: {e}")

        # Play the sound file using ffplay after conversion
        #cfg = self.converter._load_config(config_path="pyproject.toml")
        #ffplay_cfg = cfg.get("external_tools", {})
        #if ffplay_path := ffplay_cfg.get("ffplay"):
        #    if os.path.isfile(ffplay_path):
        #        try:
        #            print([ffplay_path, "-i", output_sound])
        #            print(f"Playing audio with ffplay: {output_sound}")
        #            subprocess.run([ffplay_path, "-i", output_sound], check=True) #Play the file and exit when done
        #            print(f"Done playing audio with ffplay: {output_sound}")
        #        except subprocess.CalledProcessError as e:
        #            self.main_window.statusBar().showMessage(f"Error playing audio with ffplay: {e}")
        #    else:
        #        self.main_window.statusBar().showMessage(f"Warning: ffplay path not found in config: {ffplay_path}")

def load_config(config_path: str = "pyproject.toml") -> Dict[str, Any]:
    """Load configuration from pyproject.toml under [tool.pdf-to-audiobook]"""
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path, "rb") as f:
        data = tomllib.load(f)

    # Navigate safely to the custom tool section
    app_config = data.get("tool", {}).get("pdf-to-audiobook", {})
    dropdowns_config = data.get("dropdowns", {})

    # Extract different sections
    tts_config = app_config.get("tts", {})
    paths_config = app_config.get("paths", {})
    processing_config = app_config.get("processing", {})
    external_tools = app_config.get("external_tools", {})

    config = {
        "voices": dropdowns_config.get("voices", []),
        "engine": tts_config.get("engine", "kokoro"),
        "default_voice": tts_config.get("voice", "af_heart"),
        "lang_code": tts_config.get("lang_code", "a"),

        "output_path": paths_config.get("output", "audiobook.mp3"),

        "max_words_per_chunk": processing_config.get("max_words_per_chunk", 350),
        "pause_between_chunks_sec": processing_config.get("pause_between_chunks_sec", 0.6),

        # ffmpeg paths
        "ffmpeg": external_tools.get("ffmpeg", "./ffmpeg/bin/ffmpeg.exe"),
        "ffprobe": external_tools.get("ffprobe", "./ffmpeg/bin/ffprobe.exe"),
        "ffplay": external_tools.get("ffplay", "./ffmpeg/bin/ffplay.exe"),

        # You can add more sections here later
    }

    return config

class BatchConversionTable(BaseConversionTable):
    def __init__(self, main_window):
        super().__init__(main_window)
        
        self.tableWidget.setColumnCount(5)
        self.tableWidget.setHorizontalHeaderLabels(["Input Folder", "Voice Chosen", "Launch Conversions", "Output Folder", "Launch Sounds"]
        )


    def add_row(self):
        row_count = self.tableWidget.rowCount()
        self.tableWidget.insertRow(row_count)

        # 1. Input Folder
        input_widget = PathSelectionWidget("directory")
        
        # 2. Voice Choice
        self.cfg = load_config(config_path="pyproject.toml")
        voices = self.cfg["voices"]
        print(voices)

        voice_combo = QComboBox()
        voice_combo.addItems(voices)
        
        # 3. Launch Conversions Button
        launch_conversion_btn = QPushButton("Launch All")
        launch_conversion_btn.setEnabled(False) 
        
        # 4. Output Folder
        output_widget = PathSelectionWidget("directory")
        
        # 5. Launch Sounds Button (Play folder contents)
        launch_sound_btn = QPushButton("Open Folder")
        launch_sound_btn.setEnabled(False) 

        # Insert widgets
        self.tableWidget.setCellWidget(row_count, 0, input_widget)
        self.tableWidget.setCellWidget(row_count, 1, voice_combo)
        self.tableWidget.setCellWidget(row_count, 2, launch_conversion_btn)
        self.tableWidget.setCellWidget(row_count, 3, output_widget)
        self.tableWidget.setCellWidget(row_count, 4, launch_sound_btn)

        # Connections
        input_widget.path_changed.connect(lambda: self.validate_row(input_widget))
        voice_combo.currentTextChanged.connect(lambda: self.validate_row(voice_combo))
        output_widget.path_changed.connect(lambda: self.validate_row(output_widget))
        
        launch_conversion_btn.clicked.connect(lambda: self.launch_batch_conversion(launch_conversion_btn))
        launch_sound_btn.clicked.connect(lambda: self.open_output_folder(launch_sound_btn))

    def validate_row(self, sender_widget):
        row = self.get_widget_row(sender_widget)
        if row == -1: return

        input_path = self.tableWidget.cellWidget(row, 0).text()
        voice = self.tableWidget.cellWidget(row, 1).currentText()
        output_path = self.tableWidget.cellWidget(row, 3).text()
        
        launch_btn = self.tableWidget.cellWidget(row, 2)
        
        is_ready = bool(input_path) and bool(voice) and bool(output_path)
        launch_btn.setEnabled(is_ready)

    def launch_batch_conversion(self, button):
        row = self.get_widget_row(button)
        if row == -1: return

        input_folder = self.tableWidget.cellWidget(row, 0).text()
        voice = self.tableWidget.cellWidget(row, 1).currentText()
        output_folder = self.tableWidget.cellWidget(row, 3).text()

        self.main_window.statusBar().showMessage(f"Batch conversion started for folder...")
        self.tableWidget.cellWidget(row, 2).setEnabled(False)

        # Start thread
        self.worker = ConversionWorker(input_folder, output_folder, voice, self.main_window.get_selected_language(), is_batch=True)
        self.worker.progress_update.connect(self.main_window.update_progress)
        self.worker.error_signal.connect(self.main_window.show_error)
        self.worker.finished_signal.connect(lambda r=row: self.conversion_completed(r))
        self.worker.start()

    def conversion_completed(self, row):
        self.main_window.statusBar().showMessage("Batch conversion completed!")
        self.main_window.progress_bar.setValue(100)
        QMessageBox.information(self.main_window, "Success", "Folder batch conversion completed successfully!")
        
        self.tableWidget.cellWidget(row, 2).setEnabled(True)
        self.tableWidget.cellWidget(row, 4).setEnabled(True)

    def open_output_folder(self, button):
        row = self.get_widget_row(button)
        if row == -1: return

        output_folder = self.tableWidget.cellWidget(row, 3).text()
        try:
            if sys.platform == "win32":
                os.startfile(output_folder)
            elif sys.platform == "darwin":
                subprocess.call(["open", output_folder])
            else:
                subprocess.call(["xdg-open", output_folder])
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Could not open folder: {e}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PDF to Audiobook Converter")
        self.setGeometry(100, 100, 950, 600)  # Adjusted size

        self.setup_menu()
        
        # --- Top controls (Language Selection) ---
        top_controls_layout = QHBoxLayout()
        top_controls_layout.addWidget(QLabel("Global TTS Language:"))
        self.language_combo = QComboBox()
        self.language_combo.addItems(AVAILABLE_LANGUAGES)
        top_controls_layout.addWidget(self.language_combo)
        top_controls_layout.addStretch()

        # --- Tabs Setup ---
        self.tab_widget = QTabWidget() 
        
        self.single_file_tab = SingleFileConversionTable(self)
        self.batch_file_tab = BatchConversionTable(self)

        self.tab_widget.addTab(self.single_file_tab, "Single File Conversion")
        self.tab_widget.addTab(self.batch_file_tab, "Batch Conversion")

        # --- Central Layout ---
        central_layout = QVBoxLayout()
        central_layout.addLayout(top_controls_layout)
        central_layout.addWidget(self.tab_widget)
        
        central_widget = QWidget()
        central_widget.setLayout(central_layout)
        self.setCentralWidget(central_widget)

        # --- Status Bar & Progress ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setValue(0)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
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
        return self.language_combo.currentText()

    def update_progress(self, value):
        if value >= 0:
            self.progress_bar.setValue(value)
        else:
            self.progress_bar.setValue(0)

    def show_error(self, message):
        self.statusBar().showMessage("Error occurred during conversion.")
        QMessageBox.critical(self, "Conversion Error", f"An error occurred:\n{message}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
