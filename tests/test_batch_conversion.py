import unittest
from unittest.mock import patch, MagicMock
from PySide6.QtWidgets import QComboBox  # Import necessary Qt widgets
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frm_Main import BatchConversionTable # Assuming the class is in this module
from frm_Main import PathSelectionWidget # Mock this as well

class TestBatchConversionTable(unittest.TestCase):

    def test_init(self):
        # Arrange
        main_window = MagicMock()  # Mock the main window object
        table = BatchConversionTable(main_window)

        # Assert
        self.assertEqual(table.tableWidget.columnCount(), 5)
        self.assertEqual(table.tableWidget.horizontalHeaderLabels(), ["Input Folder", "Voice Chosen", "Launch Conversions", "Output Folder", "Launch Sounds"])

    @patch('batch_conversion_table.load_config') # Mock the config loading function
    def test_add_row(self, mock_load_config):
        # Arrange
        main_window = MagicMock()
        table = BatchConversionTable(main_window)
        mock_cfg = {"voices": ["voice1", "voice2"]} # Mock the config data
        mock_load_config.return_value = mock_cfg

        row_count_before = table.tableWidget.rowCount()

        # Act
        table.add_row()

        row_count_after = table.tableWidget.rowCount()

        # Assert
        self.assertEqual(row_count_after, row_count_before + 1) # Check that a new row was added

        # Verify widgets were inserted correctly (check types and positions)
        input_widget = table.tableWidget.cellWidget(row_count_after - 1, 0)
        self.assertIsInstance(input_widget, PathSelectionWidget)
        voice_combo = table.tableWidget.cellWidget(row_count_after - 1, 1)
        self.assertIsInstance(voice_combo, QComboBox)

