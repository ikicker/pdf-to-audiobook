# PDF to Audiobook Converter
Support development of this project: ko-fi.com/michael2281

Convert PDF documents into high-quality MP3 or WAV audiobooks using **Kokoro TTS** (recommended) or **Parler-TTS**.

This tool extracts text from PDFs, splits it into natural chunks, generates speech with modern open-source TTS models, adds natural pauses, and combines everything into a single audio file — perfect for books, articles, lectures, and long-form reading.

## Features

- High-quality narration with Kokoro-82M (lightweight, excellent prosody for audiobooks)
- Optional Parler-TTS support (highly controllable voice/style via text description)
- Smart sentence-based chunking using NLTK
- All settings stored in standard `pyproject.toml`
- Command-line overrides for input PDF and output file
- Supports MP3 (compressed) or WAV (lossless) output
- Optional ffmpeg path configuration for reliable Windows export

## Requirements

- **Python** 3.11 or 3.12 (64-bit recommended)
- **ffmpeg** — for MP3 export  
  Download from: https://www.gyan.dev/ffmpeg/builds/ (ffmpeg-release-essentials.zip)  
  Extract and add the `bin` folder to your system PATH (or place in `./ffmpeg/bin/` in the project)
- **espeak-ng** — for Kokoro phonemization  
  Download Windows binary from: https://github.com/espeak-ng/espeak-ng/releases  
  Add to PATH (or configure in `pyproject.toml`)

## Installation

1. Clone or download the project folder

2. Create and activate a virtual environment (recommended):

   ```powershell
   py -3.12 -m venv audiobook_env
   audiobook_env\Scripts\activate

3. Upgrade pip and install dependencies from pyproject.toml
    ```powershell
    python -m pip install --upgrade pip setuptools wheel
    pip install .

4. Install PyTorch separately (choose one option):

    ```powershell
    # CPU-only version (simplest – works on any computer)
    pip install torch torchaudio

    ```powershell
    # GPU version (NVIDIA only – much faster TTS generation)
    # First check your CUDA version with: nvidia-smi
     Then install the matching version:
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
    # Common alternatives:
    # CUDA 12.4 → --index-url https://download.pytorch.org/whl/cu124
    # CUDA 12.8 → --index-url https://download.pytorch.org/whl/cu128

6. Download NLTK data (one-time):PowerShell

    ```powershell
    python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"

7. Set up ffmpeg & espeak-ng:
Recommended: create ./ffmpeg/bin/ in the project root and place ffmpeg.exe + ffprobe.exe there
Or add them to your system PATH
Update the paths in pyproject.toml if needed (under [tool.pdf-to-audiobook.external_tools])

##How do you run it?
```python
from pdf_to_audiobook import AudiobookConverter

converter = AudiobookConverter()

# Call the method directly with parameters
converter.pdf_to_audio(
    pdf_path="Biblical-Healing.pdf",
    output_path="my_audiobook.mp3",
    voice="am_adam"          # optional - will use default from toml if None
)