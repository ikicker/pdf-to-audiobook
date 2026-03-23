# PDF to Audiobook Converter

Convert PDF documents into high-quality MP3 or WAV audiobooks using **Kokoro TTS** (recommended) or **Parler-TTS**.

This tool extracts text from PDFs, splits it into natural chunks, generates speech using modern open-source TTS models, adds natural pauses, and combines everything into a single audio file — perfect for long-form reading (books, articles, lectures, etc.).

## Features

- High-quality narration with Kokoro-82M (lightweight, excellent prosody for audiobooks)
- Optional Parler-TTS support (highly controllable voice/style via text description)
- Smart sentence-based chunking with NLTK to avoid unnatural breaks
- Configurable via standard `pyproject.toml` file
- Command-line overrides for input PDF and output file
- Supports MP3 (compressed) or WAV (lossless) output
- Optional ffmpeg path configuration for reliable audio export on Windows

## Requirements

- **Python** 3.11 or 3.12 (64-bit recommended)
- **ffmpeg** (for MP3 export) — download from https://www.gyan.dev/ffmpeg/builds/
- You need all of the .exe files from the bin folder for ffmpeg
- **espeak-ng** (for Kokoro phonemization) — download Windows binary from https://github.com/espeak-ng/espeak-ng/releases
- Both ffmpeg and espeak-ng must be in your system PATH (or configured in `pyproject.toml`)

## Installation

1. Clone or download the project folder

2. Create and activate a virtual environment (recommended):

   ```powershell
   py -3.12 -m venv audiobook_env
   audiobook_env\Scripts\activate

3. Install depedencies
    ```powershell
    python -m pip install --upgrade pip setuptools wheel
    pip install -r requirements.txt
    pip install kokoro>=0.9.4

    ```powershell
    #for gpu acceleration
    python -m pip install --upgrade pip setuptools wheel
    pip install -r requirements.txt
    pip install kokoro>=0.9.4

4. Download NLTK data (one-time):
    ```powershell
    python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"

5. set up config.toml

#How to run the program
    # Basic usage — output name comes from pyproject.toml
    python pdf_to_audiobook.py "Biblical-Healing.pdf"

    # Override output file
    python pdf_to_audiobook.py "Biblical-Healing.pdf" "my-book-narration.mp3"

    # Lossless WAV output
    python pdf_to_audiobook.py "Biblical-Healing.pdf" "my-book.wav"

#Voice Options (Kokoro)
af_heart - warm, expressive female
af_bella - clear, professional female
af_jessica - bright, youthful female
am_adam - calm, deep male narrator
bf_emma - soft, gentle british female

#Troubleshooting

ffmpeg not found
    → Verify ./ffmpeg/bin/ffmpeg.exe exists or is in PATH
Slow generation
    → Use GPU-enabled torch (CUDA) or reduce max_words_per_chunk to 200–250
No speech generated
    → Check espeak-ng is installed and accessible
Encoding errors on Windows
    → Open pyproject.toml in VS Code → File → Save with Encoding → UTF-8

[<image-card alt="Python 3.12" src="https://img.shields.io/badge/python-3.12-blue.svg" ></image-card>](https://www.python.org/)
[<image-card alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg" ></image-card>](https://opensource.org/licenses/MIT)