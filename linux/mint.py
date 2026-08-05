#!/usr/bin/env python3
"""
Safe execution environment for the audiobook build/setup pipeline.

Python port of mint.sh. Mirrors the original script's behavior:
- `set -euo pipefail` semantics  -> every command's return code is checked;
  any failure aborts the script immediately (unless explicitly tolerated,
  matching the `|| echo ...` fallbacks in the original).
- `set -x` echo-before-run       -> every command is printed before it runs.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

VENV = "audiobook_env"
PYBIN = "bin"
PYTHON = str(Path(VENV) / PYBIN / "python3.12")
PIP = str(Path(VENV) / PYBIN / "pip3.12")


def run(cmd, *, check=True, env=None, shell=False):
    """Print the command (like `set -x`) and execute it."""
    printable = cmd if isinstance(cmd, str) else " ".join(cmd)
    print(f"+ {printable}", file=sys.stderr)
    result = subprocess.run(cmd, check=False, env=env, shell=shell)
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd)
    return result.returncode


def run_ok(cmd, *, fallback_msg=None, env=None, shell=False):
    """Run a command but tolerate failure, printing fallback_msg instead
    (mirrors `cmd || echo "..."` in the bash script)."""
    try:
        run(cmd, check=True, env=env, shell=shell)
        return True
    except subprocess.CalledProcessError:
        if fallback_msg:
            print(fallback_msg)
        return False


def step(msg):
    print(msg)


def main():
    # ---- Node.js setup ----
    os.environ.pop("NODE_OPTIONS", None)

    step("Removing Node.js modules...")
    shutil.rmtree("node_modules", ignore_errors=True)

    step("Installing Node.js package-lock.json ...")
    run(["npm", "install", "--package-lock-only"])

    step("Auditing Node.js modules...")
    run(["npm", "audit"])
    run(["npm", "audit", "fix"])

    step("Installing Node.js modules --ignore scripts...")
    run(["npm", "ci", "--ignore-scripts"])

    step("Running electron install script")
    run(["node", "node_modules/electron/install.js"])

    # ---- System packages ----
    run(["sudo", "apt", "install", "-y", "xkb-data", "fontconfig", "dbus-x11"])
    run(["fc-cache", "-f"])

    # Node setup
    run(["sudo", "apt", "install", "npm"])

    # Python setup
    run(["sudo", "apt", "install", "python3.12"])

    # ffmpeg setup
    run(["sudo", "apt", "install", "libsmbclient0"])
    run(["sudo", "ldconfig"])
    run(["sudo", "apt", "install", "ffmpeg"])

    # FUSE setup
    run(["sudo", "apt", "install", "fuse", "libfuse2"])  # Debian/Ubuntu-based distrobox

    # NSPR/NSS setup
    run(["sudo", "apt", "install", "libnspr4", "libnss3"])

    run(["sudo", "apt", "install", "python3.12-venv"])

    # ---- Python virtual environment ----
    step("Removing virtual environment and recreating...")
    shutil.rmtree(VENV, ignore_errors=True)
    run(["python3.12", "-m", "venv", VENV])

    # NOTE: `source venv/bin/activate` only affects a shell's own environment
    # and has no meaningful equivalent from within a Python subprocess model;
    # we instead invoke the venv's python/pip binaries directly everywhere
    # below, which is the standard way to achieve the same effect.

    step("Installing needed Python packages...")
    run([PYTHON, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])

    run_ok(
        [PYTHON, "-m", "spacy", "download", "en_core_web_sm"],
        fallback_msg="Couldn't find spacy",
    )

    run([PIP, "install", "."])
    run([PIP, "install", "pyinstaller"])
    run([PIP, "uninstall", "torch", "torchvision", "torchaudio", "-y"])
    # run([PIP, "install", "torch", "torchaudio",
    #      "--index-url", "https://download.pytorch.org/whl/cu121"])
    run([PIP, "install", "torch", "torchvision", "torchaudio",
         "--index-url", "https://download.pytorch.org/whl/cpu"])

    nltk_env = os.environ.copy()
    nltk_env["NLTK_DISABLE_IMPORT_SECURITY"] = "1"
    run(
        [PYTHON, "-c", "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"],
        env=nltk_env,
    )

    run([PIP, "install", "pip-audit"])

    step("Doing Python security audit...")
    pip_audit_bin = str(Path(VENV) / PYBIN / "pip-audit")
    run_ok([pip_audit_bin], fallback_msg="========  Audit failed!  Check results")

    # ---- Build / run ----
    step("Running graphical user interface")
    run(["npm", "run", "dev"])

    run(["npm", "run", "build"])  # compile TypeScript + bundle Vite

    step("Packaging TypeScript into release .exe")
    run(["npm", "run", "package"])  # wrap with electron-builder (auto-detects platform)
    # run(["npm", "run", "package:win"])
    # run(["npm", "run", "package:mac"])
    # run(["npm", "run", "package:linux"])

    run(["release/PDF to Audiobook-2.0.0.AppImage"], shell=False)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}: {e.cmd}", file=sys.stderr)
        sys.exit(e.returncode)
