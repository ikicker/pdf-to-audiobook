#!/usr/bin/env bash
# Safe execution environment for bash
set -euo pipefail
IFS=$'\n\t'
VENV=audiobook_env
PYBIN=bin
PYTHON="$VENV/$PYBIN/python3.12"
PIP="$VENV/$PYBIN/pip3.12"

# Node.js setup
unset NODE_OPTIONS
echo Removing Node.js modules...
rm -rf node_modules
echo Installing Node.js package-lock.json ...
npm install --package-lock-only
echo Auditing Node.js modules...
npm audit
npm audit fix
echo Installing Node.js modules --ignore scripts...
npm ci --ignore-scripts
echo "Running electron install script"
node node_modules/electron/install.js

sudo apt install -y xkb-data fontconfig dbus-x11
fc-cache -f

# Python setup
sudo apt install python3.12

# Node setup
sudo apt install npm

# ffmpeg setup
sudo apt install libsmbclient0
sudo ldconfig
sudo apt install ffmpeg

# FUSE setup
sudo apt install fuse libfuse2   # if it's a Debian/Ubuntu-based distrobox

# NSPR/NSS setup
sudo apt install libnspr4 libnss3

echo Removing virtual environment and recreating...
sudo apt install python3.12-venv

rm -rf "$VENV"
python3.12 -m venv "$VENV"
source "$VENV/$PYBIN/activate"

echo setting up uv
$PIP install uv

echo Installing needed Python packages...
$PYTHON -m pip install --upgrade pip setuptools wheel
$PYTHON -m spacy download en_core_web_sm || echo "Couldn't find spacy"

uv pip install .
uv pip install pyinstaller
uv pip uninstall torch torchvision torchaudio -y
# uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

export NLTK_DISABLE_IMPORT_SECURITY=1
$PYTHON -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"
uv pip install pip-audit
echo Doing Python security audit...
pip-audit || echo "========  Audit failed!  Check results"

echo Running graphical user interface
npm run dev

npm run build       # compile TypeScript + bundle Vite
echo Packaging TypeScript into release .exe
npm run package     # wrap with electron-builder (auto-detects platform)
#npm run package:win
#npm run package:mac
#npm run package:linux
"release/PDF to Audiobook-2.0.0.AppImage"
