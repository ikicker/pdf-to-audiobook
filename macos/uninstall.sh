#!/usr/bin/env bash
# Remove the PDF to Audiobook CLI install created by macos/install.sh
set -euo pipefail

INSTALL_ROOT="${INSTALL_ROOT:-$HOME/Applications/PDF-to-Audiobook}"

echo "This will remove:"
echo "  $INSTALL_ROOT"
echo "  $HOME/.local/bin/pdf-to-audiobook"
echo "  $HOME/Applications/PDF to Audiobook.command"
echo
read -r -p "Continue? [y/N] " ans
case "$ans" in
  y|Y|yes|YES) ;;
  *) echo "Aborted."; exit 0 ;;
esac

rm -rf "$INSTALL_ROOT"
rm -f "$HOME/.local/bin/pdf-to-audiobook"
rm -f "$HOME/Applications/PDF to Audiobook.command"
echo "Removed. Homebrew packages (python@3.12, ffmpeg, espeak-ng, git) were left installed."
echo "To remove those as well:  brew uninstall python@3.12 ffmpeg espeak-ng"
