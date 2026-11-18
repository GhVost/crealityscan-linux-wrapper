#!/usr/bin/env bash
# One-command setup from an unpacked pack (or a checkout with built helpers).
# Put CrealityScan_win_4.3.3.exe in Downloads first, or pass --installer PATH.
set -euo pipefail
cd -- "$(dirname -- "$(readlink -f -- "$0")")"

if [[ -f SHA256SUMS ]]; then
  echo "Checking pack contents..."
  sha256sum --quiet -c SHA256SUMS || { echo "Pack is damaged or modified; download it again." >&2; exit 1; }
fi

missing=()
for cmd in bwrap python3 pgrep fuser timeout; do command -v "$cmd" >/dev/null || missing+=("$cmd"); done
if ((${#missing[@]})); then
  echo "Missing commands: ${missing[*]}" >&2
  echo "  Arch/CachyOS: sudo pacman -S --needed bubblewrap python psmisc procps-ng" >&2
  echo "  Ubuntu/Debian: sudo apt install bubblewrap python3 psmisc procps" >&2
  exit 1
fi

# The pinned Wine build runs 32-bit installer code and needs the 32-bit loader.
if [[ ! -e /lib/ld-linux.so.2 ]]; then
  echo "Wine needs 32-bit libraries, which are not installed. On Ubuntu/Debian:" >&2
  echo "  sudo dpkg --add-architecture i386 && sudo apt update && sudo apt install libc6:i386 libfreetype6:i386 libx11-6:i386 libxext6:i386 libxcursor1:i386 libxrandr2:i386 libxi6:i386 libxfixes3:i386 libxrender1:i386 libxcomposite1:i386 libxinerama1:i386 libxkbcommon0:i386 libfontconfig1:i386 libudev1:i386 libusb-1.0-0:i386 libasound2t64:i386 libpulse0:i386 libgl1:i386 libvulkan1:i386 libwayland-client0:i386 libglib2.0-0t64:i386" >&2
  echo "  Arch/CachyOS: enable [multilib] and install lib32-glibc lib32-freetype2 lib32-libx11 lib32-vulkan-icd-loader" >&2
  exit 1
fi

exec python3 scripts/creality.py setup "$@"
