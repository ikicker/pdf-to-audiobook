#!/usr/bin/env bash
# PDF to Audiobook — macOS installer
# Targeted at Intel Macs such as Mac mini (Late 2014) running macOS Catalina–Monterey.
# Installs Homebrew tools, clones the repo, sets up a Python 3.12 venv with Kokoro TTS
# (CPU), and installs a command-line launcher. The Electron desktop UI in this
# project requires a much newer macOS / Electron runtime and is skipped by default.
set -euo pipefail
IFS=$'\n\t'

REPO_URL="${REPO_URL:-https://github.com/ikicker/pdf-to-audiobook.git}"
INSTALL_ROOT="${INSTALL_ROOT:-$HOME/Applications/PDF-to-Audiobook}"
VENV_NAME="audiobook_env"
SKIP_GUI="${SKIP_GUI:-1}"

red()    { printf '\033[31m%s\033[0m\n' "$*"; }
green()  { printf '\033[32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }
step()   { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1
}

os_version() {
  sw_vers -productVersion 2>/dev/null || echo "unknown"
}

arch_name() {
  uname -m
}

check_platform() {
  if [[ "$(uname -s)" != "Darwin" ]]; then
    red "This installer is for macOS only."
    exit 1
  fi

  local ver arch
  ver="$(os_version)"
  arch="$(arch_name)"
  step "Detected macOS ${ver} (${arch})"

  if [[ "$arch" != "x86_64" ]]; then
    yellow "This machine is ${arch}. The script still works, but a 2014 Mac mini is Intel (x86_64)."
  else
    green "Intel Mac detected — correct architecture for a 2014 Mac mini."
  fi

  # Monterey is 12.x; later Electron builds will not run here.
  local major
  major="${ver%%.*}"
  if [[ "$major" =~ ^[0-9]+$ ]] && (( major < 10 )); then
    red "macOS ${ver} is too old. Catalina (10.15) or newer is required."
    exit 1
  fi
  if [[ "$major" =~ ^[0-9]+$ ]] && (( major <= 12 )); then
    yellow "macOS ${ver}: the Electron GUI from this repo will not run. Installing the Python CLI only."
    SKIP_GUI=1
  fi
}

install_homebrew() {
  if need_cmd brew; then
    green "Homebrew already installed: $(brew --prefix)"
    return
  fi
  step "Installing Homebrew (you will be prompted for your password)"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

  if [[ -x /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
  elif [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  fi

  if ! need_cmd brew; then
    red "Homebrew installed but brew is not on PATH. Open a new Terminal and re-run this script."
    exit 1
  fi
}

ensure_brew_on_path() {
  if need_cmd brew; then
    return
  fi
  if [[ -x /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
  elif [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  fi
}

brew_pkgs() {
  step "Installing Python 3.12, ffmpeg, espeak-ng, git"
  # Intel Homebrew prefix is /usr/local
  brew update || true
  brew install python@3.12 ffmpeg espeak git || true
  # espeak-ng formula name
  brew install espeak-ng || brew install espeak || true

  if ! need_cmd python3.12; then
    # brew python may live under the cellar only
    local p
    p="$(brew --prefix python@3.12 2>/dev/null)/bin/python3.12"
    if [[ -x "$p" ]]; then
      export PATH="$(dirname "$p"):$PATH"
    fi
  fi

  if ! need_cmd python3.12; then
    red "python3.12 not found after Homebrew install."
    exit 1
  fi
  green "python3.12: $(command -v python3.12) ($(python3.12 --version))"
  green "ffmpeg:     $(command -v ffmpeg || echo missing)"
  green "espeak-ng:  $(command -v espeak-ng || command -v espeak || echo missing)"
}

clone_or_update_repo() {
  step "Project directory: ${INSTALL_ROOT}"
  mkdir -p "$(dirname "$INSTALL_ROOT")"
  if [[ -d "$INSTALL_ROOT/.git" ]]; then
    yellow "Repo already present — pulling latest"
    git -C "$INSTALL_ROOT" pull --ff-only || yellow "git pull failed; using existing tree"
  elif [[ -d "$INSTALL_ROOT" ]] && [[ -f "$INSTALL_ROOT/PDF_to_Audiobook.py" ]]; then
    yellow "Existing source tree found (not a git clone). Leaving it in place."
  else
    git clone "$REPO_URL" "$INSTALL_ROOT"
  fi
}

setup_venv() {
  step "Creating Python virtual environment"
  cd "$INSTALL_ROOT"
  rm -rf "$VENV_NAME"
  python3.12 -m venv "$VENV_NAME"
  # shellcheck disable=SC1090
  source "$VENV_NAME/bin/activate"
  python -m pip install --upgrade pip setuptools wheel
  python -m pip install .
  python -m pip install pyinstaller || true
  python -m pip uninstall -y torch torchvision torchaudio >/dev/null 2>&1 || true
  # CPU wheels only — 2014 mini has no usable NVIDIA GPU and no Apple Neural Engine
  python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
  export NLTK_DISABLE_IMPORT_SECURITY=1
  python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"
  python - <<'PY'
import importlib
for m in ("pypdf", "nltk", "soundfile", "pydub", "torch", "kokoro"):
    try:
        importlib.import_module(m)
        print(f"  ok  {m}")
    except Exception as e:
        print(f"  FAIL {m}: {e}")
        raise SystemExit(1)
print("Python stack looks good.")
PY
}

write_wrappers() {
  step "Installing launchers"
  local bin_dir="$HOME/.local/bin"
  mkdir -p "$bin_dir"

  cat > "$bin_dir/pdf-to-audiobook" <<EOF
#!/usr/bin/env bash
set -euo pipefail
ROOT="${INSTALL_ROOT}"
export PATH="\$(brew --prefix 2>/dev/null)/bin:/usr/local/bin:/opt/homebrew/bin:\$PATH"
cd "\$ROOT"
exec "\$ROOT/${VENV_NAME}/bin/python" "\$ROOT/PDF_to_Audiobook.py" "\$@"
EOF
  chmod +x "$bin_dir/pdf-to-audiobook"

  # Double-clickable launcher
  cat > "$INSTALL_ROOT/PDF to Audiobook.command" <<EOF
#!/bin/bash
cd "${INSTALL_ROOT}"
export PATH="\$(/usr/local/bin/brew --prefix 2>/dev/null)/bin:/opt/homebrew/bin:/usr/local/bin:\$PATH"
echo "PDF to Audiobook"
echo "Usage: drag a PDF onto this window after the prompt, or type a path."
echo
exec "${INSTALL_ROOT}/${VENV_NAME}/bin/python" "${INSTALL_ROOT}/PDF_to_Audiobook.py"
EOF
  chmod +x "$INSTALL_ROOT/PDF to Audiobook.command"

  mkdir -p "$HOME/Applications"
  ln -sfn "$INSTALL_ROOT/PDF to Audiobook.command" "$HOME/Applications/PDF to Audiobook.command"

  if ! echo "$PATH" | tr ':' '\n' | grep -qx "$bin_dir"; then
    local rc
    for rc in "$HOME/.zprofile" "$HOME/.zshrc" "$HOME/.bash_profile" "$HOME/.profile"; do
      if [[ -f "$rc" ]] || [[ "$rc" == "$HOME/.zprofile" ]]; then
        if ! grep -q '.local/bin' "$rc" 2>/dev/null; then
          printf '\n# PDF to Audiobook\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$rc"
        fi
        break
      fi
    done
  fi
}

optional_gui() {
  if [[ "$SKIP_GUI" == "1" ]]; then
    yellow "Skipping Electron GUI (not supported on a 2014 Mac mini / macOS ≤ 12)."
    return
  fi
  step "Attempting Electron GUI build (newer Macs only)"
  if ! need_cmd npm; then
    brew install node || true
  fi
  if need_cmd npm; then
    cd "$INSTALL_ROOT"
    npm ci --ignore-scripts || npm install --ignore-scripts || true
    npm run package:mac || yellow "GUI package failed — CLI is still installed."
  fi
}

print_done() {
  cat <<EOF

$(green "Install finished.")

App files:     ${INSTALL_ROOT}
CLI command:   pdf-to-audiobook
Double-click:  ~/Applications/PDF to Audiobook.command
               (or ${INSTALL_ROOT}/PDF to Audiobook.command)

Open a new Terminal window so PATH picks up ~/.local/bin, then:

  pdf-to-audiobook /path/to/book.pdf ~/Desktop/book.mp3 --voice am_adam

Voices include: af_heart af_bella af_nicole af_sarah af_sky af_jessica
                am_adam am_michael bf_emma bf_isabella bm_george bm_lewis

Notes for a 2014 Mac mini
  • Synthesis is CPU-only and will be slow on long books. Start with a short PDF.
  • 8 GB machines may struggle; close other apps.
  • The Windows/Linux Electron front end is not packaged for this Mac.

Uninstall:
  bash ${INSTALL_ROOT}/../macos/uninstall.sh
  or:  bash "$(cd "$(dirname "$0")" && pwd)/uninstall.sh"
EOF
}

main() {
  check_platform
  install_homebrew
  ensure_brew_on_path
  brew_pkgs
  clone_or_update_repo
  setup_venv
  write_wrappers
  # Copy uninstall next to the app if we were run from a downloaded folder
  local here
  here="$(cd "$(dirname "$0")" && pwd)"
  if [[ -f "$here/uninstall.sh" ]]; then
    mkdir -p "$(dirname "$INSTALL_ROOT")/macos"
    cp "$here/uninstall.sh" "$(dirname "$INSTALL_ROOT")/macos/uninstall.sh" 2>/dev/null || true
    cp "$here/uninstall.sh" "$INSTALL_ROOT/uninstall.sh" 2>/dev/null || true
  fi
  optional_gui
  print_done
}

main "$@"
