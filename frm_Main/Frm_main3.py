import sys
import os
import pyttsx3
import PyPDF2

from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
from PySide6.QtCore import QFile, QThread, Signal, Slot
from PySide6.QtUiTools import QUiLoader

class WorkerThread(QThread):
    """
    Worker thread to handle the heavy lifting of reading the PDF and
    generating the audio so the UI doesn't freeze.
    """
    progress_update = Signal(int)
    log_update = Signal(str)
    finished_conversion = Signal()
    error_occurred = Signal(str)

    def __init__(self, pdf_path, audio_path, voice_id, speed, volume):
        super().__init__()
        self.pdf_path = pdf_path
        self.audio_path = audio_path
        self.voice_id = voice_id
        self.speed = speed
        self.volume = volume

    def run(self):
        try:
            self.log_update.emit("Extracting text from PDF...")
            
            # Read PDF
            text = ""
            with open(self.pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)
                
                for i in range(total_pages):
                    page = pdf_reader.pages[i]
                    text += page.extract_text() + "\n"
                    # Update progress for extraction (0 to 50%)
                    self.progress_update.emit(int((i / total_pages) * 50))
            
            # Clean up text formatting slightly
            text = text.replace('\n', ' ')

            self.log_update.emit("Generating Audio... This may take a while depending on file size.")
            self.progress_update.emit(50)

            # Initialize pyttsx3 INSIDE the thread (required for thread safety on Windows)
            engine = pyttsx3.init()
            engine.setProperty('voice', self.voice_id)
            engine.setProperty('rate', self.speed)
            engine.setProperty('volume', self.volume / 100.0)

            # Generate and save audio
            engine.save_to_file(text, self.audio_path)
            engine.runAndWait()

            self.progress_update.emit(100)
            self.log_update.emit(f"Success! Audio saved to: {self.audio_path}")
            self.finished_conversion.emit()

        except Exception as e:
            self.error_occurred.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Load the UI file dynamically
        loader = QUiLoader()
        ui_file = QFile("mainwindow.ui")
        if not ui_file.open(QFile.ReadOnly):
            print("Cannot open mainwindow.ui. Make sure it's in the same folder.")
            sys.exit(-1)
        self.ui = loader.load(ui_file, self)
        ui_file.close()

        # Init TTS Engine just to get voices for the dropdown
        self.engine = pyttsx3.init()
        self.voices = self.engine.getProperty('voices')
        
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        # Populate Voices
        for voice in self.voices:
            name = voice.name
            if 'english' in name.lower() or 'en' in voice.languages:
                name += " (English)"
            self.ui.cb_voice.addItem(name, voice.id) # Store voice.id as user data
            
        # Reset progress
        self.ui.progress_bar.setValue(0)
        self.ui.txt_log.append("Ready.")

    def connect_signals(self):
        self.ui.btn_browse_pdf.clicked.connect(self.browse_pdf)
        self.ui.btn_browse_audio.clicked.connect(self.browse_audio)
        self.ui.slider_speed.valueChanged.connect(self.update_speed_lbl)
        self.ui.slider_volume.valueChanged.connect(self.update_volume_lbl)
        self.ui.btn_convert.clicked.connect(self.start_conversion)

    @Slot()
    def browse_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF File", "", "PDF Files (*.pdf)")
        if file_path:
            self.ui.le_pdf.setText(file_path)
            # Auto-fill output file name
            audio_path = os.path.splitext(file_path)[0] + ".mp3"
            self.ui.le_audio.setText(audio_path)

    @Slot()
    def browse_audio(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Audio File", "", "Audio Files (*.mp3 *.wav)")
        if file_path:
            self.ui.le_audio.setText(file_path)

    @Slot(int)
    def update_speed_lbl(self, value):
        self.ui.lbl_speed_val.setText(str(value))

    @Slot(int)
    def update_volume_lbl(self, value):
        self.ui.lbl_volume_val.setText(f"{value}%")

    @Slot()
    def start_conversion(self):
        pdf_path = self.ui.le_pdf.text()
        audio_path = self.ui.le_audio.text()

        if not os.path.exists(pdf_path):
            QMessageBox.warning(self, "Error", "Please select a valid PDF file.")
            return
        if not audio_path:
            QMessageBox.warning(self, "Error", "Please select an output audio path.")
            return

        # Disable UI elements during conversion
        self.ui.btn_convert.setEnabled(False)
        self.ui.progress_bar.setValue(0)
        self.ui.txt_log.clear()

        # Get settings
        voice_id = self.ui.cb_voice.currentData()
        speed = self.ui.slider_speed.value()
        volume = self.ui.slider_volume.value()

        # Setup Thread
        self.worker = WorkerThread(pdf_path, audio_path, voice_id, speed, volume)
        self.worker.progress_update.connect(self.ui.progress_bar.setValue)
        self.worker.log_update.connect(self.ui.txt_log.append)
        self.worker.error_occurred.connect(self.handle_error)
        self.worker.finished_conversion.connect(self.conversion_done)
        
        # Start Thread
        self.worker.start()

    @Slot(str)
    def handle_error(self, error_msg):
        self.ui.txt_log.append(f"ERROR: {error_msg}")
        QMessageBox.critical(self, "Conversion Error", f"An error occurred:\n{error_msg}")
        self.conversion_done()

    @Slot()
    def conversion_done(self):
        self.ui.btn_convert.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Optional: Apply a modern style if available
    app.setStyle("Fusion") 
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())