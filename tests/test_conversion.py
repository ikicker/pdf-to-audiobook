import pytest
import unittest
from unittest.mock import MagicMock, patch  # For mocking
from pathlib import Path
from typing import Dict, Any
import tomllib # Import the toml library
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frm_Main import BatchConversionTable # Assuming the class is in this module
from frm_Main import load_config
from PDF_to_Audiobook import AudiobookConverter


class TestBatchConversionTable(unittest.TestCase):

    def setUp(self):
        """Set up for test methods."""
        self.main_window = MagicMock() # Mock the main window object
        self.table = BatchConversionTable(self.main_window)
        self.cfg = {"voices": ["voice1", "voice2"]}  # Example config

    def test_init(self):
        """Test that the table is initialized correctly."""
        self.assertEqual(self.table.tableWidget.getColumnCount(), 5)
        expected_headers = ["Input Folder", "Voice Chosen", "Launch Conversions", "Output Folder", "Launch Sounds"]
        self.assertEqual(list(self.table.tableWidget.horizontalHeaderLabels()), expected_headers)

    def test_add_row_creates_widgets(self):
        """Test that add_row creates the correct widgets and sets them in the table."""
        row_count = self.table.rowCount()
        self.table.add_row()
        next_row_count = self.table.rowCount()

        self.assertEqual(next_row_count, row_count + 1)

        # Verify widget types and placement (using asserts)
        input_widget = self.table.tableWidget.cellWidget(next_row_count, 0)
        self.assertIsNotNone(input_widget)  # Check it's not None
        # Add more assertions to check the type of input_widget if needed

        voice_combo = self.table.tableWidget.cellWidget(next_row_count, 1)
        self.assertIsNotNone(voice_combo)
        self.assertEqual(voice_combo.count(), len(self.cfg["voices"])) # Check number of voices in combo box

    @patch('your_module.load_config')  # Mock load_config function
    def test_add_row_loads_config(self, mock_load_config):
        """Test that add_row calls load_config and uses the returned config."""
        mock_load_config.return_value = self.cfg
        self.table.add_row()
        # Assert that load_config was called (important!)
        mock_load_config.assert_called_once()

class TestAudiobookConverter(unittest.TestCase):

    def setUp(self):
        """Set up for test methods."""
        self.converter = AudiobookConverter()
        self.progress_update_signal = MagicMock()  # Mock the signal
        self.error_signal = MagicMock() # Mock error signal
        self.converter.progress_update = self.progress_update_signal
        self.converter.error_signal = self.error_signal

    def test_run_batch_success(self):
        """Test run method with batch conversion and successful PDF processing."""
        # Mock os.listdir to return a list of PDF files
        with patch('os.listdir') as mock_listdir:
            mock_listdir.return_value = ["file1.pdf", "file2.pdf"]

            # Mock pdf_to_audio (important!)
            self.converter.input_path = "/test/input"
            self.converter.output_path = "/test/output"
            self.converter.voice = "en"
            self.converter.is_batch = True
            mock_pdf_to_audio = MagicMock()
            self.converter.converter.pdf_to_audio = mock_pdf_to_audio

            self.converter.run()

            # Assert that pdf_to_audio was called for each file
            self.assertEqual(mock_pdf_to_audio.call_count, 2)  # Called twice (file1 and file2)

    def test_run_batch_file_not_found(self):
        """Test run method with batch conversion when the input folder is missing."""
        with patch('os.listdir') as mock_listdir:
            mock_listdir.side_effect = FileNotFoundError("Input folder not found")

            self.converter.input_path = "/nonexistent/folder"
            self.converter.output_path = "/test/output"
            self.converter.voice = "en"
            self.converter.is_batch = True

            self.converter.run()

            # Assert that the error signal was emitted with the correct message
            self.error_signal.assert_called_once_with("Input folder not found: /nonexistent/folder")
            self.progress_update_signal.assert_called_once_with(-1)  # Check progress update

    def test_run_batch_pdf_to_audio_exception(self):
        """Test run method with batch conversion when pdf_to_audio raises an exception."""
        with patch('os.listdir') as mock_listdir:
            mock_listdir.return_value = ["file1.pdf"]

            # Mock pdf_to_audio to raise an exception
            self.converter.input_path = "/test/input"
            self.converter.output_path = "/test/output"
            self.converter.voice = "en"
            self.converter.is_batch = True
            mock_pdf_to_audio = MagicMock()
            mock_pdf_to_audio.side_

