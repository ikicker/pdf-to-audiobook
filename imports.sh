#!/bin/bash
# Safe execution environment for bash
set -euo pipefail
IFS=$'\n\t'

# Python setup

#if false
#then
echo Removing virtual environment and recreating...
rm -rf audiobook_env
~/AppData/Local/Programs/Python/Python312/python -m venv audiobook_env
#fi
source audiobook_env/Scripts/activate
#if false
#then
echo Installing needed Python packages...
audiobook_env/Scripts/python -m pip install --upgrade pip setuptools wheel
audiobook_env/Scripts/pip install .
audiobook_env/Scripts/pip install torch torchaudio
export NLTK_DISABLE_IMPORT_SECURITY=1
audiobook_env/Scripts/python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"
# audiobook_env/Scripts/pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install pip-audit
echo Doing Python security audit...
pip-audit

# Node.js setup
unset NODE_OPTIONS
echo Removing Node.js modules...
rm -r node_modules
echo Installing Node.js package-lock.json ...
npm install --package-lock-only
echo Auditing Node.js modules...
npm audit
npm audit fix
echo Installing Node.js modules --ignore scripts...
npm ci --ignore-scripts
echo "Running electron install script"
node node_modules/electron/install.js
echo Running graphical user interface
# fi
npm run dev

npm run build       # compile TypeScript + bundle Vite
echo Packaging TypeScript into release .exe
npm run package     # wrap with electron-builder (auto-detects platform)
#npm run package:win
#npm run package:mac
#npm run package:linux
"release/win-unpacked/PDF to Audiobook.exe"
