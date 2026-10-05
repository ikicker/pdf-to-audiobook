# PDF to Audiobook Converter
Support development of this project: [ko-fi.com/michael2281](https://ko-fi.com/michael2281)

This project is an Open Source Eleven Labs alternative made to help disabled or older people with reading text. Anyone can use it, including for study. Convert your PDF, Epub, and Text files into mp3 and wav.

![pdf to audiobook](pdf-to-audiobook.png)

**The front end currently works on Windows, Linux, and Newer Macs. The back end can also be used directly from the terminal on Windows, macOS, and Linux.**

Notes from upstream:

- Successfully its been run on Windows, Linux and Mac OS. The installation is slightly different on each.
- I've added Epub and text conversion as well.

Convert PDF documents into high-quality MP3 or WAV audiobooks using the **Kokoro TTS** model (recommended) or **Parler-TTS** model.

Linux notes:
- Build scripts are in linux/.
- Start the scripts from the main folder, like
- ```bash linux/mint.sh```
- Currently requires ffmpeg to be installed on system
- Front-end can be tested with ```npm run preview```

**About**
This tool extracts text from PDFs, splits it into natural chunks, generates speech with modern open-source TTS models, adds natural pauses, and combines everything into a single audio file — perfect for books, articles, lectures, and long-form reading.

## Features

- High-quality narration with Kokoro-82M (lightweight, strong prosody for audiobooks)
- Optional Parler-TTS support (voice and style via a text description)
- Smart sentence-based chunking using NLTK
- Settings stored in standard `pyproject.toml`
- Command-line overrides for input PDF and output file
- MP3 (compressed) or WAV (lossless) output
- Optional ffmpeg path configuration for reliable Windows export

## Requirements (all platforms)

- **Python** 3.11 or 3.12 (64-bit)
- **ffmpeg** — required for MP3 export
- **espeak-ng** — required for Kokoro phonemization
- Disk space: several GB for PyTorch plus models on first run
- Internet for the first install and first model download

Available Kokoro voices (from `pyproject.toml`):

`af_heart` `af_bella` `af_nicole` `af_sarah` `af_sky` `af_jessica`  
`am_adam` `am_michael` `bf_emma` `bf_isabella` `bm_george` `bm_lewis`

Default voice is `af_heart` unless you pass `--voice`.

---

## How to use the product

### Terminal (any OS, after install)

```bash
pdf-to-audiobook /path/to/book.pdf /path/to/book.mp3 --voice am_adam
```

With no arguments the program prompts for paths.

Device flag (CPU is the default):

```bash
pdf-to-audiobook book.pdf book.mp3 --voice af_heart --device cpu
```

Use `--device cuda` only if you installed a CUDA build of PyTorch and have a supported NVIDIA GPU.

Output format follows the file extension: `.mp3` or `.wav`.

### Graphical front end (Windows and Linux)

After a full install that includes Electron:

- Windows: run `release/win-unpacked/PDF to Audiobook.exe`, or the desktop shortcut if you packaged with NSIS.
- Linux: run the AppImage, for example `./release/PDF\ to\ Audiobook-2.0.0.AppImage`.
- For development: from the cloned repo, `npm run dev`.

The Electron UI does **not** run on older macOS. Use the terminal backend on those machines.

### Python API

```python
from pdf_to_audiobook import AudiobookConverter

converter = AudiobookConverter()

converter.pdf_to_audio(
    pdf_path="Biblical-Healing.pdf",
    output_path="my_audiobook.mp3",
    voice="am_adam",  # optional; uses pyproject.toml default if omitted
)
```

Settings live under `[tool.pdf-to-audiobook]` in `pyproject.toml` (engine, voice, chunk size, pause length, ffmpeg paths).

---

## Installation — Windows

The front end and back end both work on Windows.

### Prerequisites

1. Install **Python 3.12** from [python.org](https://www.python.org/downloads/). During setup, check **Add python.exe to PATH**.
2. Install **Git** (includes Git Bash): [https://git-scm.com/download/win](https://git-scm.com/download/win)
3. Install **Node.js** (LTS) if you want the Electron GUI: [https://nodejs.org](https://nodejs.org)
4. **ffmpeg** — download [ffmpeg-release-essentials.zip](https://www.gyan.dev/ffmpeg/builds/), extract it, and either:
   - add the `bin` folder to your user PATH, or
   - copy `ffmpeg.exe` and `ffprobe.exe` into `./ffmpeg/bin/` inside the project
5. **espeak-ng** — download a Windows build from [espeak-ng releases](https://github.com/espeak-ng/espeak-ng/releases) and add it to PATH (or set the path in `pyproject.toml` under `[tool.pdf-to-audiobook.external_tools]`).

### Backend (terminal) install

In **PowerShell** or **Command Prompt**, from a folder of your choice:

```powershell
git clone https://github.com/ikicker/pdf-to-audiobook.git
cd pdf-to-audiobook

py -3.12 -m venv audiobook_env
audiobook_env\Scripts\activate

python -m pip install --upgrade pip setuptools wheel
pip install .
pip install torch torchaudio
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"
```

NVIDIA GPU (optional, much faster): check `nvidia-smi`, then install a matching wheel instead of the CPU `torch` line, for example:

```powershell
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

Other common indexes: `cu124`, `cu128`.

### GUI / packaging install (Git Bash)

The repo includes `win/gitbash.sh`. From **Git Bash** in the cloned repo:

```bash
bash win/gitbash.sh
```

That script creates `audiobook_env`, installs Python deps and CPU PyTorch, downloads NLTK data, installs npm packages, runs `npm run dev`, then builds and launches:

`release/win-unpacked/PDF to Audiobook.exe`

There is also `win/cygwin.sh` for Cygwin (it hard-codes a local Python path; edit it before use).

### How to run on Windows

**CLI (after the venv is activated):**

```powershell
audiobook_env\Scripts\activate
python PDF_to_Audiobook.py "C:\Users\You\Documents\book.pdf" "C:\Users\You\Desktop\book.mp3" --voice am_adam
```

If the project console script is on PATH after `pip install .`:

```powershell
pdf-to-audiobook "C:\Users\You\Documents\book.pdf" "C:\Users\You\Desktop\book.mp3" --voice am_adam
```

**GUI:**

```powershell
npm run dev
```

or double-click `release\win-unpacked\PDF to Audiobook.exe` after packaging.

---

## Installation — macOS (OSX)

The **Python backend works**. The Electron UI does not run on older Intel macOS (Electron 41 needs a much newer OS than a Late 2014 Mac mini / Monterey).

A dedicated installer lives in the `macos/` folder of the repo (and in this project’s `macos/` copy).

### What you need

- Intel Mac or Apple Silicon Mac
- macOS Catalina 10.15 or newer (Monterey is fine for the CLI installer)
- Admin password (Homebrew / Xcode Command Line Tools)
- About 3–4 GB free for PyTorch CPU and models
- Internet

On 8 GB RAM machines, close other apps. Long books are slow on older CPUs.

### Install with the official script

1. Clone the repo or copy the `macos` folder onto the Mac.
2. Open **Terminal**:

```bash
git clone https://github.com/ikicker/pdf-to-audiobook.git
cd pdf-to-audiobook/macos
chmod +x install.sh uninstall.sh
./install.sh
```

The script will:

- Install [Homebrew](https://brew.sh) if it is missing
- `brew install python@3.12 ffmpeg espeak-ng git`
- Clone the project into `~/Applications/PDF-to-Audiobook` (default)
- Create `audiobook_env` and install the project plus **CPU** PyTorch
- Download NLTK tokenizer data
- Put `pdf-to-audiobook` on `~/.local/bin`
- Add `~/Applications/PDF to Audiobook.command` for double-click use

Override the install location:

```bash
INSTALL_ROOT="$HOME/src/pdf-to-audiobook" ./install.sh
```

To attempt the GUI on a **newer** Mac:

```bash
SKIP_GUI=0 ./install.sh
```

Expect that to fail on Monterey.

### Manual backend install (any Mac)

```bash
brew install python@3.12 ffmpeg espeak-ng git
git clone https://github.com/ikicker/pdf-to-audiobook.git
cd pdf-to-audiobook
python3.12 -m venv audiobook_env
source audiobook_env/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install .
pip install torch torchaudio
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"
```

### How to run on macOS

Open a **new** Terminal after install so PATH updates apply:

```bash
pdf-to-audiobook ~/Documents/book.pdf ~/Desktop/book.mp3 --voice am_adam
```

With no arguments the program prompts for paths.

Or double-click **PDF to Audiobook** in your user Applications folder (`~/Applications/PDF to Audiobook.command`).

From a manual venv:

```bash
source audiobook_env/bin/activate
python PDF_to_Audiobook.py ~/Documents/book.pdf ~/Desktop/book.mp3 --voice am_adam
```

### Uninstall (script install)

```bash
cd /path/to/macos
./uninstall.sh
```

Homebrew, `python@3.12`, `ffmpeg`, and `espeak-ng` stay installed unless you remove them with `brew uninstall`.

---

## Installation — Linux

The front end is intended to work on Linux (AppImage). Distro helper scripts live in `linux/`.

### Common packages

You need Python 3.12, ffmpeg, espeak-ng, Node.js/npm (for the GUI), git, and a venv.

**Debian / Ubuntu / Linux Mint**

```bash
sudo apt update
sudo apt install -y git python3.12 python3.12-venv ffmpeg espeak-ng npm \
  fuse libfuse2 libnspr4 libnss3 xkb-data fontconfig dbus-x11
```

**Fedora / Bazzite / similar**

```bash
sudo dnf install -y git python3.12 ffmpeg espeak-ng \
  fuse fuse-libs nss nspr fontconfig dbus-x11
```

Also install Node.js/npm from your distro or [nodejs.org](https://nodejs.org) if `npm` is not already present.

### Backend (terminal) install

```bash
git clone https://github.com/ikicker/pdf-to-audiobook.git
cd pdf-to-audiobook

python3.12 -m venv audiobook_env
source audiobook_env/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install .
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"
```

CUDA (optional):

```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Distro helper scripts (GUI + package)

From the cloned repo root:

**Linux Mint / Debian-based**

```bash
bash linux/mint.sh
```

**Bazzite / Fedora-based**

```bash
bash linux/bazzite.sh
```

These scripts install packages, recreate `audiobook_env`, install the project and CPU PyTorch, download NLTK data, install npm deps, run `npm run dev`, then package an AppImage and launch:

`release/PDF to Audiobook-2.0.0.AppImage`

Review the scripts before running them: they use `sudo`, recreate the venv, and start the GUI.

### How to run on Linux

**CLI:**

```bash
source audiobook_env/bin/activate
python PDF_to_Audiobook.py ~/Documents/book.pdf ~/Desktop/book.mp3 --voice am_adam
```

or, if the console script is on PATH:

```bash
pdf-to-audiobook ~/Documents/book.pdf ~/Desktop/book.mp3 --voice am_adam
```

**GUI (development):**

```bash
npm run dev
```

**GUI (packaged):**

```bash
chmod +x "release/PDF to Audiobook-2.0.0.AppImage"
./release/PDF\ to\ Audiobook-2.0.0.AppImage
```

If the AppImage fails to start, install FUSE (`libfuse2` on Debian/Ubuntu, `fuse` on Fedora).

---

## Installation — developer (all platforms)

1. Clone or download the project folder.

2. Create and activate a virtual environment.

   Windows:

   ```powershell
   py -3.12 -m venv audiobook_env
   audiobook_env\Scripts\activate
   ```

   macOS / Linux:

   ```bash
   python3.12 -m venv audiobook_env
   source audiobook_env/bin/activate
   ```

3. Upgrade pip and install the project:

   ```bash
   python -m pip install --upgrade pip setuptools wheel
   pip install .
   ```

4. Install PyTorch separately (CPU or CUDA — see the OS sections above). Torch is not pinned in `pyproject.toml` so you can choose CPU vs GPU.

5. Download NLTK data once:

   ```bash
   python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"
   ```

6. Point ffmpeg / ffprobe / espeak-ng at working binaries. Either put them on PATH or set `[tool.pdf-to-audiobook.external_tools]` in `pyproject.toml`.

7. Optional GUI:

   ```bash
   npm ci
   npm run dev
   ```

   Package:

   ```bash
   npm run package
   ```

   Platform-specific package scripts: `package:win`, `package:mac`, `package:linux`.

Optional extra: Parler-TTS (`pip install ".[parler]"`) and switch `engine` in `pyproject.toml`.

---

## License

MIT (see the project metadata in `pyproject.toml`).
