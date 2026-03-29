import unittest
from unittest.mock import patch, MagicMock  # Import necessary mocks
import os # needed for path manipulation in tests
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PDF_to_Audiobook import AudiobookConverter

class TestAudiobookConverter(unittest.TestCase):

    @patch('converter_module.os') # Mock the os module
    def test_run_batch_success(self, mock_os):
        # Arrange
        mock_os.listdir.return_value = ["file1.pdf", "file2.txt", "file3.pdf"]  # Simulate files in a directory
        mock_converter = MagicMock() # Mock the converter object itself
        converter = AudiobookConverter(input_path="test_folder", output_path="output_folder", voice="en", language="en")
        converter.converter = mock_converter

        # Act
        converter.run()

        # Assert
        mock_os.listdir.assert_called_once_with("test_folder")
        self.assertEqual(converter.is_batch, True) # Check the is_batch attribute
        mock_converter.pdf_to_audio.assert_any_call(pdf_path="test_folder/file1.pdf", output_path="output_folder/file1.mp3", voice="en")
        mock_converter.pdf_to_audio.assert_any_call(pdf_path="test_folder/file3.pdf", output_path="output_folder/file3.mp3", voice="en")

    @patch('converter_module.os') # Mock the os module
    def test_run_batch_no_pdfs(self, mock_os):
        # Arrange
        mock_os.listdir.return_value = ["file1.txt", "file2.jpg"]  # Simulate no PDFs in directory
        converter = AudiobookConverter(input_path="test_folder", output_path="output_folder", voice="en", language="en")

        # Act
        converter.run()

        # Assert
        mock_os.listdir.assert_called_once_with("test_folder")
        self.assertEqual(converter.is_batch, True) # Check the is_batch attribute
        # Ensure pdf_to_audio isn't called if no PDFs are found


    @patch('converter_module.os')  # Mock os module
    def test_run_batch_folder_not_found(self, mock_os):
        # Arrange
        mock_os.listdir.side_effect = FileNotFoundError("Folder not found") # Simulate folder missing
        converter = AudiobookConverter(input_path="test_folder", output_path="output_folder", voice="en", language="en")

        # Act
        converter.run()

        # Assert
        mock_os.listdir.assert_called_once_with("test_folder")
        self.assertEqual(converter.progress_update.emit(-1).call_count, 1) # Check error signal emitted
        # Add assertion to check if the function returns after error

    def test_run_non_batch(self):
        # Arrange
        converter = AudiobookConverter(input_path="test_file", output_path="output_folder", voice="en", language="en")
        converter.is_batch = False # Set is_batch to false for this test

        # Act
        converter.run()

        # Assert
        self.assertEqual(converter.is_batch, False)
        # Add assertions based on what the non-batch run should do (e.g., call pdf_to_audio with a single file path).  You'll need to mock converter.pdf_to_audio in this case as well.
