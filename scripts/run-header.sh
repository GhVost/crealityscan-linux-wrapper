#!/bin/sh
# CrealityScan for Linux: self-installing package.
#   sh crealityscan-linux.run              install or update, then add it to the app menu
#   sh crealityscan-linux.run --uninstall  remove it (your scans in Documents stay)
#   sh crealityscan-linux.run --extract DIR  only unpack
# Extra options are passed to setup, e.g. --installer PATH, --gpu-name NAME, --allow-untested.
set -eu
PAYLOAD_LINE=@PAYLOAD_LINE@
PAYLOAD_SHA256=@PAYLOAD_SHA256@
BASE="${XDG_DATA_HOME:-$HOME/.local/share}/crealityscan-linux"
APP="$BASE/app"
SELF="$0"
die() { echo "$*" >&2; exit 1; }

payload() { tail -n +"$PAYLOAD_LINE" "$SELF"; }

check() {
  command -v sha256sum >/dev/null || die "sha256sum is required"
  [ "$(payload | sha256sum | cut -d' ' -f1)" = "$PAYLOAD_SHA256" ] \
    || die "This package is damaged or incomplete; download it again."
}

case "${1:-}" in
  --uninstall)
    shift
    [ -x "$APP/uninstall.sh" ] || die "CrealityScan for Linux is not installed in $APP"
    exec "$APP/uninstall.sh" "$@" ;;
  --extract)
    [ $# -ge 2 ] || die "usage: $SELF --extract DIR"
    check; mkdir -p "$2"; payload | tar -xzf - -C "$2" --strip-components=1
    echo "Unpacked to $2"; exit 0 ;;
  -h|--help)
    sed -n '2,7p' "$SELF" | sed 's/^# \{0,1\}//'; exit 0 ;;
esac

check
echo "Installing CrealityScan for Linux into $APP"
mkdir -p "$BASE"
NEW="$BASE/app.new.$$"
rm -rf "$NEW"; mkdir -p "$NEW"
trap 'rm -rf "$NEW"' EXIT
payload | tar -xzf - -C "$NEW" --strip-components=1
# Keep the existing configuration across updates.
if [ -f "$APP/config.local.json" ]; then cp -p "$APP/config.local.json" "$NEW/"; fi
if [ -d "$APP" ]; then
  OLD="$BASE/app.old.$$"; mv "$APP" "$OLD"; mv "$NEW" "$APP"; rm -rf "$OLD"
else
  mv "$NEW" "$APP"
fi
trap - EXIT
exec "$APP/install.sh" "$@"
exit 0
