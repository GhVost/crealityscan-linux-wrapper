#!/usr/bin/env bash
# Remove CrealityScan for Linux installed by the self-installing package.
# Your scans and projects in ~/Documents/CrealityScan are kept.
set -euo pipefail
BASE="${XDG_DATA_HOME:-$HOME/.local/share}/crealityscan-linux"
ENTRY="${XDG_DATA_HOME:-$HOME/.local/share}/applications/crealityscan-linux.desktop"

if pgrep -x CrealityScan.ex >/dev/null; then
  echo "Close CrealityScan first." >&2; exit 1
fi
if [[ "${1:-}" != "--yes" ]]; then
  echo "This removes $BASE (the app, Wine runtime and settings, a few GB)"
  echo "and the app-menu entry. Scans in your Documents/CrealityScan folder are kept."
  read -r -p "Continue? [y/N] " answer
  [[ "$answer" == [yY]* ]] || { echo "Nothing removed."; exit 0; }
fi
rm -f "$ENTRY"
# Wine prefixes contain read-only files; make them removable first.
chmod -R u+w "$BASE" 2>/dev/null || true
rm -rf "$BASE"
command -v update-desktop-database >/dev/null && update-desktop-database "$(dirname "$ENTRY")" 2>/dev/null || true
echo "Removed. Scans in Documents/CrealityScan are still there."
if ls /etc/udev/rules.d/*creality* >/dev/null 2>&1; then
  echo "The scanner-access rule is still installed; to remove it:"
  echo "  sudo rm /etc/udev/rules.d/70-creality-pika.rules && sudo udevadm control --reload"
fi
