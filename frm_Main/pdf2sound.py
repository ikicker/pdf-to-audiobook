import subprocess
import sys
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QPushButton, QFileDialog, QComboBox,
                               QRadioButton, QCheckBox, QProgressBar,
                               QLineEdit)
from PySide6.QtCore import Qt
import os
import argparse  # For parsing command-line arguments if needed
import tomllib #For loading config file
from PDF_to_Audiobook import load_config
from PDF_to_Audiobook import extract_text_from_pdf

# Import your existing PDF processing functions (extract_text_from_pdf, etc.)
# from pdf_to_audiobook import extract_text_from_pdf, ...


class MainWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PDF to Audiobook Converter")
        self.output_path_edit = QLineEdit() # Create the text edit field
        # Add it to a layout (e.g., QVBoxLayout) so it's visible in your window
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.output_path_edit)
        self.setLayout(self.layout)
        self.cfg = load_config(config_path="pyproject.toml")
        default_output_path = self.cfg.get("paths", {}).get("output", "audiobook.mp3")
        self.output_path_edit.setText(default_output_path) # Set default value
        self.setup_ui()

    def setup_ui(self):
        """Sets up the user interface elements."""

        # 1. Input Controls
        self.voice_label = QLabel("Voice:")
        tts_section = self.cfg.get("tool", {}).get("pdf-to-audiobook", {}).get("tts", {}) # Navigate to the tts section safely
        voices = tts_section.get("voices", ["af_heart"])  # Default voices list
        self.voice_combo = QComboBox()
        self.voice_combo.addItems(voices)

        # Add more UI elements here (e.g., file selection, output path, etc.)
        self.layout.addWidget(self.voice_label)
        self.layout.addWidget(self.voice_combo)


        selected_voice = tts_section.get("voice", "af_heart") #Default voice
        try:
            index = self.voice_combo.findText(selected_voice)
            if index != -1:
                self.voice_combo.setCurrentIndex(index)
            else:
                print(f"Warning: Voice '{selected_voice}' not found in the list of available voices.") #Handle missing voice
        except Exception as e:
            print(f"Error setting initial voice selection: {e}")

        self.language_label = QLabel("Language:")
        lang_code = tts_section.get("lang_code", "a")  # Default language code
        languages = ["a"] #Default list, you can expand this if needed from config
        self.language_combo = QComboBox()
        self.language_combo.addItems(languages)
        try:
            index = self.language_combo.findText(lang_code)
            if index != -1:
                self.language_combo.setCurrentIndex(index)
            else:
                print(f"Warning: Language code '{lang_code}' not found in the list of available languages.") #Handle missing language
        except Exception as e:
            print(f"Error setting initial language selection: {e}")

        # Gender (assuming you want to represent it with radio buttons)
        gender = tts_section.get("gender", "male")  # Default gender
        self.gender_radio_male = QRadioButton("Male")
        self.gender_radio_female = QRadioButton("Female")

        if gender == "male":
            self.gender_radio_male.setChecked(True)
        elif gender == "female":
            self.gender_radio_female.setChecked(True)
        else:
            print(f"Warning: Invalid gender '{gender}' specified in config.  Defaulting to male.") #Handle invalid gender

        self.nationality_label = QLabel("Nationality:")
        nationalities = ["American"] # Default list, expand from config if needed
        self.nationality_combo = QComboBox()
        self.nationality_combo.addItems(nationalities)

        # 2. File Input
        self.add_pdfs_button = QPushButton("Add PDFs")
        self.pdf_list = []  # Store PDF paths
        self.add_pdfs_button.clicked.connect(self.select_pdfs)

        # 3. Output Controls
        self.create_folder_checkbox = QCheckBox("Create Folder")
        self.save_file_button = QPushButton("Save File")
        self.output_path = "" #Store output path
        self.save_file_button.clicked.connect(self.select_output_file)

        # 4. Start Button & Progress Bar
        self.start_button = QPushButton("Start Conversion")
        self.progress_bar = QProgressBar()
        self.status_label = QLabel("")

        # Layout arrangement (using horizontal and vertical layouts)
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.voice_label)
        input_layout.addWidget(self.voice_combo)
        input_layout.addWidget(self.language_label)
        input_layout.addWidget(self.language_combo)

        gender_layout = QHBoxLayout()
        gender_layout.addWidget(self.gender_radio_male)
        gender_layout.addWidget(self.gender_radio_female)

        file_layout = QHBoxLayout()
        file_layout.addWidget(self.add_pdfs_button)

        output_layout = QHBoxLayout()
        output_layout.addWidget(self.create_folder_checkbox)
        output_layout.addWidget(self.save_file_button)

        self.layout.addLayout(input_layout)
        self.layout.addLayout(gender_layout)
        self.layout.addLayout(file_layout)
        self.layout.addLayout(output_layout)
        self.layout.addWidget(self.start_button)
        self.layout.addWidget(self.progress_bar)
        self.layout.addWidget(self.status_label)

        # Connect the start button to the conversion function
        self.start_button.clicked.connect(self.start_conversion)


    def select_pdfs(self):
        file_dialog = QFileDialog()
        files, _ = file_dialog.getOpenFileNames(self, "Select PDF Files", "", "PDF Files (*.pdf)")
        if files:
            self.pdf_list = files
            self.status_label.setText(f"Selected {len(files)} PDFs.")

    def select_output_file(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(self, "Save Audio File", "", "Audio Files (*.mp3 *.wav)")
        if file_path:
            self.output_path = file_path
            self.output_path_edit.setText(self.output_path) # Set default value
            self.status_label.setText(f"Output file set to: {file_path}")

    def start_conversion(self):
        # Get selected options from the GUI
        voice = self.voice_combo.currentText()
        language = self.language_combo.currentText()
        gender = "Male" if self.gender_radio_male.isChecked() else "Female" #Or get from config
        nationality = self.nationality_combo.currentText()
        output_path = self.output_path_edit.text()  # Get output path from the edit field

        # Call your PDF processing function with the selected options and file list
        try:
            self.convert_pdfs(self.pdf_list, voice, language, gender, nationality, output_path)
        except Exception as e:
            self.status_label.setText(f"Error during conversion: {e}")

    def convert_pdfs(self, pdf_files, voice, language, gender, nationality, output_path):
        # Implement your PDF processing logic here
        # This is where you would call extract_text_from_pdf and other functions.
        # Use tqdm for the progress bar.  Update self.progress_bar.setValue()
        command = [
                "python",
                "pdf_to_audiobook.py",
                pdf_files[0],
                output_path,
                ]
        print(command)

        self.status_label.setText("Converting...")
#       for i, pdf_file in enumerate(pdf_files):
#           try:
#               raw_text = extract_text_from_pdf(pdf_file) #Your function call
#               # ... process the text using your TTS engine ...
#
#               self.progress_bar.setValue((i + 1) * (100 / len(pdf_files)))  # Update progress bar
#           except Exception as e:
#               self.status_label.setText(f"Error processing {pdf_file}: {e}")
#               return #Stop if an error occurs

        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            print(result.stdout)  # Print the output from pdf-to-audiobook.py
        except subprocess.CalledProcessError as e:
            print(f"Error running pdf-to-audiobook.py: {e.stderr}")

        self.status_label.setText("Conversion finished!")

        # Play the sound file using ffmpeg after conversion
        cfg = load_config()  # Load config again (or pass it to convert_pdfs)
        ffmpeg_cfg = cfg.get("external_tools", {})
        if ffmpeg_path := ffmpeg_cfg.get("ffmpeg"):
            if os.path.isfile(ffmpeg_path):
                try:
                    subprocess.run([ffmpeg_path, "-i", output_path], check=True) #Play the file and exit when done
                    print(f"Playing audio with ffmpeg: {output_path}")
                except subprocess.CalledProcessError as e:
                    self.status_label.setText(f"Error playing audio with ffmpeg: {e}")
            else:
                self.status_label.setText(f"Warning: ffmpeg path not found in config: {ffmpeg_path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()  # Pass the parsed arguments
    window.show()
    sys.exit(app.exec())
