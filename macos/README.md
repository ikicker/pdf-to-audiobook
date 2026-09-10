# PDF to Audiobook — macOS installer (Intel / Mac mini 2014)

The upstream project ships Windows and Linux packaging and an Electron UI. A **Late 2014 Mac mini** is Intel Haswell and officially tops out at **macOS Monterey 12**. Current Electron in this repo will not run there.

This folder installs the **Python backend + Kokoro TTS on CPU**, which is what the README already says works from the terminal.

## What you need

- Mac mini Late 2014 (or any Intel Mac)
- macOS Catalina 10.15 or newer (Monterey is fine)
- An admin password (Homebrew / Xcode CLT)
- Disk space: ~3–4 GB (PyTorch CPU + models on first run)
- Internet

8 GB RAM machines should close other apps. Long books will take a long time on this CPU.

## Install

1. Copy the whole `macos` folder onto the Mac (or clone this tree).
2. Open Terminal and run:

```bash
chmod +x install.sh uninstall.sh
./install.sh
```

The script will:

- Install [Homebrew](https://brew.sh) if it is missing
- `brew install python@3.12 ffmpeg espeak-ng git`
- Clone [ikicker/pdf-to-audiobook](https://github.com/ikicker/pdf-to-audiobook) into `~/Applications/PDF-to-Audiobook`
- Create `audiobook_env` and install the project + **CPU** PyTorch
- Download NLTK tokenizer data
- Put `pdf-to-audiobook` on `~/.local/bin`
- Add `~/Applications/PDF to Audiobook.command` for double-click use

Override the install location:

```bash
INSTALL_ROOT="$HOME/src/pdf-to-audiobook" ./install.sh
```

## Use

Open a **new** Terminal after install:

```bash
pdf-to-audiobook ~/Documents/book.pdf ~/Desktop/book.mp3 --voice am_adam
```

With no arguments the program prompts for paths.

Voices (from the project `pyproject.toml`):

`af_heart` `af_bella` `af_nicole` `af_sarah` `af_sky` `af_jessica`  
`am_adam` `am_michael` `bf_emma` `bf_isabella` `bm_george` `bm_lewis`

Or double-click **PDF to Audiobook** in your user Applications folder.

## What is not installed

- Electron / `.dmg` GUI — Electron 41 needs a far newer macOS than a 2014 mini can run.
- CUDA / MPS — this Mac has neither a supported NVIDIA GPU nor Apple Silicon.

To try the GUI on a newer Mac, set `SKIP_GUI=0` before running `install.sh`. Expect it to fail on Monterey.

## Uninstall

```bash
./uninstall.sh
```

Homebrew itself and `python@3.12` / `ffmpeg` / `espeak-ng` stay unless you remove them with `brew uninstall`.
