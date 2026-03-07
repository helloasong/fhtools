#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")"/.. && pwd)"
cd "$ROOT_DIR"
APP_NAME="FHBinningTool"
APP_PATH="dist/$APP_NAME.app"
DMG_PATH="dist/$APP_NAME.dmg"
if [ ! -d "$APP_PATH" ]; then
  bash scripts/build_mac.sh
fi
if [ -n "${CODESIGN_IDENTITY:-}" ]; then
  ENTITLEMENTS="assets/entitlements.plist"
  if [ -f "$ENTITLEMENTS" ]; then
    codesign -f -s "$CODESIGN_IDENTITY" --deep --options runtime --entitlements "$ENTITLEMENTS" "$APP_PATH"
  else
    codesign -f -s "$CODESIGN_IDENTITY" --deep --options runtime "$APP_PATH"
  fi
  codesign --verify --deep --strict "$APP_PATH"
fi
rm -f "$DMG_PATH"
hdiutil create -volname "$APP_NAME" -srcfolder "$APP_PATH" -ov -format UDZO "$DMG_PATH"
if [ -n "${NOTARY_KEYCHAIN_PROFILE:-}" ]; then
  xcrun notarytool submit "$DMG_PATH" --keychain-profile "$NOTARY_KEYCHAIN_PROFILE" --wait
  xcrun stapler staple "$DMG_PATH"
  if [ -d "$APP_PATH" ]; then
    xcrun stapler staple "$APP_PATH" || true
  fi
elif [ -n "${NOTARY_APPLE_ID:-}" ] && [ -n "${NOTARY_PASSWORD:-}" ] && [ -n "${NOTARY_TEAM_ID:-}" ]; then
  xcrun notarytool submit "$DMG_PATH" --apple-id "$NOTARY_APPLE_ID" --team-id "$NOTARY_TEAM_ID" --password "$NOTARY_PASSWORD" --wait
  xcrun stapler staple "$DMG_PATH"
  if [ -d "$APP_PATH" ]; then
    xcrun stapler staple "$APP_PATH" || true
  fi
fi
echo "DMG generated at $DMG_PATH"
