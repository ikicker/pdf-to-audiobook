import pytest
from unittest.mock import MagicMock, patch  # For mocking
from pathlib import Path
from typing import Dict, Any
import tomllib  # Import the toml library
import sys
import os

# We no longer need to import QApplication manually
# We no longer need unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frm_Main import BatchConversionTable  # Assuming the class is in this module
from frm_Main import PathSelectionWidget  # Mock this as well
from frm_Main import load_config
from PDF_to_Audiobook import AudiobookConverter


class TestBatchConversionTable:
    # Removed inheritance from unittest.TestCase

    @pytest.fixture(autouse=True)
    def setup_table(self, qapp):
        """
        Setup method using Pytest fixture.
        The 'qapp' argument automatically triggers pytest-qt to provide a valid QApplication.
        'autouse=True' ensures this runs before every test in this class.
        """
        self.main_window = MagicMock()  # Mock the main window object
        self.table = BatchConversionTable(self.main_window)
        self.cfg = {"voices":["voice1", "voice2"]}  # Example config

    def test_init(self):
        """Test that the table is initialized correctly."""
        # Note: Standard PySide6 uses columnCount(), changed from getColumnCount()
        assert self.table.tableWidget.columnCount() == 5

        expected_headers =["Input Folder", "Voice Chosen", "Launch Conversions", "Output Folder", "Launch Sounds"]

        # If horizontalHeaderLabels is a custom property/method you added, this works.
        # If you are using standard QTableWidget, you might need to iterate through horizontalHeaderItem(i).text() instead.
        assert list(self.table.tableWidget.horizontalHeaderLabels()) == expected_headers

    def test_add_row_creates_widgets(self):
        """Test that add_row creates the correct widgets and sets them in the table."""
        row_count = self.table.rowCount()
        self.table.add_row()
        next_row_count = self.table.rowCount()

        assert next_row_count == row_count + 1

        # Verify widget types and placement (using native asserts)
        input_widget = self.table.tableWidget.cellWidget(next_row_count, 0)
        assert input_widget is not None

        voice_combo = self.table.tableWidget.cellWidget(next_row_count, 1)
        assert voice_combo is not None
        assert voice_combo.count() == len(self.cfg["voices"])

    @patch('frm_Main.load_config')  # Mock load_config function
    def test_add_row_loads_config(self, mock_load_config):
        """Test that add_row calls load_config and uses the returned config."""
        mock_load_config.return_value = self.cfg
        self.table.add_row()
        # Assert that load_config was called
        mock_load_config.assert_called_once()


class TestAudiobookConverter:
    # Removed inheritance from unittest.TestCase

    def setup_method(self):
        """
        In native Pytest, setup_method() runs automatically before every test method.
        No fixtures needed here since it doesn't involve Qt widgets.
        """
        self.converter = AudiobookConverter()
        self.progress_update_signal = MagicMock()  # Mock the signal
        self.error_signal = MagicMock()  # Mock error signal
        self.converter.progress_update = self.progress_update_signal
        self.converter.error_signal = self.error_signal

    def test_run_batch_success(self):
        """Test run method with batch conversion and successful PDF processing."""
        # Mock os.listdir to return a list of PDF files
        with patch('os.listdir') as mock_listdir:
            mock_listdir.return_value =["file1.pdf", "file2.pdf"]

            # Mock pdf_to_audio
            self.converter.input_path = "/test/input"
            self.converter.output_path = "/test/output"
            self.converter.voice = "en"
            self.converter.is_batch = True
            mock_pdf_to_audio = MagicMock()
            self.converter.converter.pdf_to_audio = mock_pdf_to_audio

            self.converter.run()

            # Assert that pdf_to_audio was called for each file
            assert mock_pdf_to_audio.call_count == 2
