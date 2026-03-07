#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "$0")"/.. && pwd)"
APP_PATH="${1:-$ROOT_DIR/dist/FHBinningTool.app}"
DMG_PATH="${2:-$ROOT_DIR/dist/FHBinningTool.dmg}"

red() { printf "\033[31m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }

section() {
  printf "\n== %s ==\n" "$1"
}

cmd() {
  printf "\n$ %s\n" "$*"
  eval "$@"
}

ok=1

section "Paths"
echo "APP_PATH=$APP_PATH"
echo "DMG_PATH=$DMG_PATH"

if [ ! -d "$APP_PATH" ]; then
  red "App not found: $APP_PATH"
  ok=0
fi

if [ ! -f "$DMG_PATH" ]; then
  yellow "DMG not found: $DMG_PATH"
fi

if [ "$ok" -eq 1 ]; then
  section "App Bundle Sanity"
  if [ -f "$APP_PATH/Contents/Info.plist" ]; then
    cmd "/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' '$APP_PATH/Contents/Info.plist' 2>/dev/null || true"
    cmd "/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' '$APP_PATH/Contents/Info.plist' 2>/dev/null || true"
  else
    red "Missing Info.plist"
    ok=0
  fi

  if [ -d "$APP_PATH/Contents/MacOS" ]; then
    cmd "ls -la '$APP_PATH/Contents/MacOS' || true"
  else
    red "Missing Contents/MacOS"
    ok=0
  fi
fi

if [ "$ok" -eq 1 ]; then
  section "Extended Attributes (Gatekeeper)"
  cmd "xattr -lr '$APP_PATH' 2>/dev/null | egrep -n 'com.apple.(quarantine|provenance)' || true"

  section "codesign"
  cmd "codesign --verify --deep --strict --verbose=2 '$APP_PATH' || true"
  cmd "codesign -dv --verbose=4 '$APP_PATH' 2>&1 | head -n 80"

  section "spctl (Gatekeeper)"
  cmd "spctl --assess --type execute --verbose=4 '$APP_PATH' || true"
  if [ -f "$DMG_PATH" ]; then
    cmd "spctl --assess --type open --verbose=4 '$DMG_PATH' || true"
  fi

  section "Notarization Ticket (stapler)"
  if command -v xcrun >/dev/null 2>&1; then
    if [ -f "$DMG_PATH" ]; then
      cmd "xcrun stapler validate '$DMG_PATH' || true"
    fi
    cmd "xcrun stapler validate '$APP_PATH' || true"
  else
    yellow "xcrun not found"
  fi
fi

section "Hints"
echo "1) If spctl shows 'rejected' and codesign shows 'Signature=adhoc', you need Developer ID signing + notarization for double-click launches."
echo "2) If xattr shows com.apple.quarantine/provenance, try: xattr -dr com.apple.quarantine <App> ; xattr -dr com.apple.provenance <App>"
echo "3) For signing/notary, see scripts/package_dmg.sh environment variables."

if [ "$ok" -eq 1 ]; then
  green "Diagnostics finished."
  exit 0
fi
red "Diagnostics finished with missing files."
exit 2

