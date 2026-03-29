import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from unittest.mock import Mock
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frm_Main import MainWindow, ConversionWorker  # Assuming your main window is in this file
from PDF_to_Audiobook import AudiobookConverter # Import the class to mock

class TestMainWindow(QTest):

    def setUp(self):
        """Setup method to create a QApplication and MainWindow instance before each test."""
        self.app = QApplication.instance() or QApplication(sys.argv)  # Use existing app if running
        self.window = MainWindow()
        self.converter_mock = Mock(spec=AudiobookConverter) # Create mock object
        self.worker = ConversionWorker("input.pdf", "output.mp3", "en-US", "en-GB")
        self.worker.converter = self.converter_mock

    def tearDown(self):
        """Tear down method to clean up after each test."""
        self.window.close()  # Close the window after each test
        self.app = None # Clean up app instance


    def test_add_row_creates_widgets(self):
        initial_row_count = self.window.tableWidget.rowCount()
        self.window.add_row()
        new_row_count = self.window.tableWidget.rowCount()
        self.assertEqual(new_row_count, initial_row_count + 1)

    def test_add_row_populates_voice_combo(self):
        # Mock the config loading to return a specific list of voices
        config = {"voices": ["Voice1", "Voice2"]}
        self.converter_mock.load_config.return_value = config  # Configure mock

        self.window.add_row()
        voice_combo = self.window.tableWidget.cellWidget(0, 1) # Assuming row 0 is the newly added row
        self.assertIsInstance(voice_combo, QComboBox)
        self.assertEqual(voice_combo.count(), len(config["voices"]))

    def test_launch_conversion_emits_progress_signal(self):
        # Mock converter to simulate a conversion process
        self.converter_mock.pdf_to_audio.return_value = None  # Simulate successful conversion
        self.window.worker.converter = self.converter_mock

        # Find the launch button in the table (you might need to adjust this based on your layout)
        launch_button = self.window.tableWidget.cellWidget(0, 3) # Assuming row 0 is the newly added row
        self.assertIsNotNone(launch_button)

        # Connect a slot to the progress_update signal and verify it's called
        progress_values = []
        self.worker.progress_update.connect(lambda value: progress_values.append(value))

        # Simulate button click (you might need to adjust this based on your layout)
        launch_button.click()

        # Wait for the signal to be emitted (adjust timeout as needed)
        self.app.processEvents() # Process events so signals are emitted
        self.assertTrue(len(progress_values) > 0)  # Check that progress values were received


    def test_launch_conversion_emits_error_signal(self):
        # Mock converter to raise an exception during conversion
        self.converter_mock.pdf_to_audio.side_effect = Exception("Conversion failed")

        # Find the launch button in the table (you might need to adjust this based on your layout)
        launch_button = self.window.tableWidget.cellWidget(0, 3) # Assuming row 0 is the newly added row
        self.assertIsNotNone(launch_button)

        # Connect a slot to the error_signal and verify it's called
        error_message = None
        self.worker.error_signal.connect(lambda message: setattr(self, 'error_message', message))

        # Simulate button click
        launch_button.click()

        # Wait for the signal to be emitted (adjust timeout as needed)
        self.app.processEvents() # Process events so signals are emitted
        self.assertIsNotNone(self.error_message)  # Check that an error message was received
