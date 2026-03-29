import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock # For mocking library calls
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frm_Main import load_config
from PDF_to_Audiobook import AudiobookConverter

# Fixtures (setup/teardown for tests)

@pytest.fixture
def sample_pdf_file(tmpdir):
    """Creates a dummy PDF file for testing."""
    pdf_path = tmpdir.join("sample.pdf")
    with open(pdf_path, "w") as f:  # Create an empty pdf file
        f.write("This is a test PDF.")
    return str(pdf_path)

@pytest.fixture
def sample_config_file(tmpdir):
    """Creates a dummy pyproject.toml for testing."""
    config_path = tmpdir.join("pyproject.toml")
    config_content = """
[tool.pdf-to-audiobook]
voices = ["voice1", "voice2"]
engine = "kokoro"
default_voice = "af_heart"
lang_code = "a"

[dropdowns]
voices = ["voice3", "voice4"]

[paths]
output = "test_audio.mp3"

[processing]
max_words_per_chunk = 100
pause_between_chunks_sec = 0.5
"""
    config_path.write(config_content)
    return str(config_path)


# Tests

def test_load_config_success(sample_config_file):
    """Test loading config from a valid file."""
    config = load_config(sample_config_file)
    assert isinstance(config, dict)
    assert config.get("voices") == ["voice1", "voice2"]
    assert config.get("engine") == "kokoro"

def test_load_config_file_not_found():
    """Test loading config when the file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent_config.toml")


def test_audiobook_converter_init_loads_config(sample_config_file):
    """Test that the AudiobookConverter loads the configuration on initialization."""
    converter = AudiobookConverter(config_path=sample_config_file)
    assert isinstance(converter.config, dict)

def test_batch_conversion_success(sample_pdf_file, tmpdir):
    """Test batch conversion with multiple PDF files."""
    input_folder = str(tmpdir.mkdir("input_pdfs"))
    output_path = str(tmpdir.mkdir("output_audio"))

    # Create some dummy pdfs in the input folder
    for i in range(2):
        pdf_file = tmpdir.join(f"input_pdfs/sample_{i}.pdf")
        with open(pdf_file, "w") as f:
            f.write("Test PDF content.")

    converter = AudiobookConverter() # Uses default config
    converter.is_batch = True
    converter.input_path = input_folder
    converter.output_path = output_path

    # Mock the pdf_to_audio function to avoid actual conversion
    with patch('PDF_to_Audiobook.AudiobookConverter.pdf_to_audio') as mock_pdf_to_audio:
        converter.run()

    assert mock_pdf_to_audio.call_count == 2  # Verify it was called for each PDF


def test_batch_conversion_input_folder_not_found(sample_pdf_file):
    """Test batch conversion when the input folder doesn't exist."""
    converter = AudiobookConverter()
    converter.is_batch = True
    converter.input_path = "nonexistent_folder"

    # Mock error signal emission
    with patch('PDF_to_Audiobook.AudiobookConverter.error_signal') as mock_error_signal:
        converter.run()
    mock_error_signal.assert_called_once_with("Input folder not found: nonexistent_folder")


def test_single_file_conversion(sample_pdf_file, tmpdir):
    """Test single file conversion."""
    output_path = str(tmpdir) + "/test_audio.mp3"

    converter = AudiobookConverter()
    converter.input_path = sample_pdf_file
    converter.output_path = output_path
    converter.voice = "en-us-amy" #Example voice

    # Mock the pdf_to_audio function
    with patch('PDF_to_Audiobook.AudiobookConverter.pdf_to_audio') as mock_pdf_to_audio:
        converter.run()

    mock_pdf_to_audio.assert_called_once_with(pdf_path=sample_pdf_file, output_path=output_path, voice="en-us-amy")
