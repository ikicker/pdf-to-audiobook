#!/usr/bin/env python3
"""
Python translation of bazzite.sh

Behavior preserved from the original bash script:
- set -euo pipefail  -> run() aborts the whole script on any non-zero exit
                        (unless a step is explicitly marked check=False)
- set -x             -> each command is printed before it runs
- $PYTHON / $PIP     -> resolved to the venv's interpreter/pip paths
- `cmd || echo ...`  -> steps that used `||` in bash use check=False here
                        and print the fallback message on failure
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Config (equivalent to the bash variables)
# ---------------------------------------------------------------------------
VENV = "audiobook_env"
PYBIN = "bin"  # on Windows this would be "Scripts" instead
VENV_DIR = Path(VENV)
PYTHON = VENV_DIR / PYBIN / "python3.12"
PIP = VENV_DIR / PYBIN / "pip3.12"


def run(cmd, check=True, env=None, shell=False):
    """
    Run a command, echoing it first (like `bash -x`), and raising on
    failure by default (like `set -e`). Pass check=False to emulate a
    bash `cmd || fallback` pattern.
    """
    printable = cmd if isinstance(cmd, str) else " ".join(str(c) for c in cmd)
    print(f"+ {printable}", file=sys.stderr)
    result = subprocess.run(cmd, env=env, shell=shell)
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd)
    return result.returncode


def main():
    # -------------------------------------------------------------------
    # Node.js setup
    # -------------------------------------------------------------------
    env = os.environ.copy()
    env.pop("NODE_OPTIONS", None)  # unset NODE_OPTIONS

    print("Removing Node.js modules...")
    shutil.rmtree("node_modules", ignore_errors=True)  # rm -rf node_modules

    print("Installing Node.js package-lock.json ...")
    run(["npm", "install", "--package-lock-only"], env=env)

    print("Auditing Node.js modules...")
    run(["npm", "audit"], env=env)
    run(["npm", "audit", "fix"], env=env)

    print("Installing Node.js modules --ignore scripts...")
    run(["npm", "ci", "--ignore-scripts"], env=env)

    print("Running electron install script")
    run(["node", "node_modules/electron/install.js"], env=env)

    # -------------------------------------------------------------------
    # System packages (dnf)
    # -------------------------------------------------------------------
    run(["sudo", "dnf", "install", "-y",
         "xkeyboard-config", "fontconfig", "dbus-x11"])
    run(["fc-cache", "-f"])

    # Python setup
    run(["sudo", "dnf", "install", "python312"])

    # ffmpeg setup
    run(["sudo", "dnf", "install",
         "samba-client-libs", "samba-common-libs", "libsmbclient"])
    run(["sudo", "ldconfig"])
    run(["sudo", "dnf", "install", "ffmpeg"])

    # pyinstaller setup
    run(["sudo", "dnf", "install", "objdump"])

    # FUSE setup (Fedora-based distrobox)
    run(["sudo", "dnf", "install", "fuse", "fuse-libs"])

    # NSPR/NSS setup
    run(["sudo", "dnf", "install",
         "nss", "nspr", "atk", "at-spi2-atk", "cups-libs",
         "libdrm", "libxkbcommon", "mesa-libgbm", "alsa-lib"])

    # -------------------------------------------------------------------
    # Python virtual environment
    # -------------------------------------------------------------------
    print("Removing virtual environment and recreating...")
    shutil.rmtree(VENV_DIR, ignore_errors=True)  # rm -rf "$VENV"
    run(["python3.12", "-m", "venv", VENV])

    # NOTE: `source $VENV/bin/activate` only affects the current shell's
    # env; in Python we get the same effect by calling the venv's
    # python/pip binaries directly (PYTHON / PIP below), which is what
    # the rest of the original script does anyway via $PYTHON / $PIP.

    print("Installing needed Python packages...")
    run([str(PYTHON), "-m", "pip", "install", "--upgrade",
         "pip", "setuptools", "wheel"])

    # `$PYTHON -m spacy download en_core_web_sm || echo "Couldn't find spacy"`
    if run([str(PYTHON), "-m", "spacy", "download", "en_core_web_sm"],
           check=False) != 0:
        print("Couldn't find spacy")

    run([str(PIP), "install", "."])
    run([str(PIP), "install", "pyinstaller"])
    run([str(PIP), "uninstall", "torch", "torchvision", "torchaudio", "-y"])

    # (commented out in original — CUDA build, left out here too)
    # run([str(PIP), "install", "torch", "torchaudio",
    #      "--index-url", "https://download.pytorch.org/whl/cu121"])

    run([str(PIP), "install", "torch", "torchvision", "torchaudio",
         "--index-url", "https://download.pytorch.org/whl/cpu"])

    # NLTK download
    nltk_env = os.environ.copy()
    nltk_env["NLTK_DISABLE_IMPORT_SECURITY"] = "1"
    run([str(PYTHON), "-c",
         "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"],
        env=nltk_env)

    run([str(PIP), "install", "pip-audit"])

    print("Doing Python security audit...")
    # `pip-audit || echo "========  Audit failed!  Check results"`
    if run([str(VENV_DIR / PYBIN / "pip-audit")], check=False) != 0:
        print("========  Audit failed!  Check results")

    # -------------------------------------------------------------------
    # Build / package the Electron app
    # -------------------------------------------------------------------
    print("Running graphical user interface")
    run(["npm", "run", "dev"], env=env)

    run(["npm", "run", "build"], env=env)  # compile TypeScript + bundle Vite

    print("Packaging TypeScript into release .exe")
    run(["npm", "run", "package"], env=env)  # electron-builder, auto-detects platform
    # run(["npm", "run", "package:win"], env=env)
    # run(["npm", "run", "package:mac"], env=env)
    # run(["npm", "run", "package:linux"], env=env)

    # Original script just referenced this path as a bare string (no-op in
    # bash unless executed); kept here for parity/documentation only.
    _ = "release/PDF to Audiobook-2.0.0.AppImage"


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}: {e.cmd}",
              file=sys.stderr)
        sys.exit(e.returncode)
