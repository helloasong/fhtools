#!/usr/bin/env bash
# FHBinningTool macOS Build Script
# Supports: macOS 11+ (Intel and Apple Silicon)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "FHBinningTool macOS Build Script"
echo "=========================================="
echo "Project root: $ROOT_DIR"

# Detect architecture
ARCH=$(uname -m)
echo "Detected architecture: $ARCH"

# Set target architecture
if [ "$ARCH" = "arm64" ]; then
    TARGET_ARCH="arm64"
    echo "Building for Apple Silicon (arm64)..."
elif [ "$ARCH" = "x86_64" ]; then
    TARGET_ARCH="x86_64"
    echo "Building for Intel (x86_64)..."
else
    echo "[WARNING] Unknown architecture: $ARCH, using native"
    TARGET_ARCH="native"
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found. Please install Python 3.9+."
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Using Python: $PYTHON_VERSION"

cd "$ROOT_DIR"

# Create virtual environment
if [ ! -d venv ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install PyInstaller
echo "Installing PyInstaller..."
pip install pyinstaller

# Install requirements
echo "Installing dependencies..."
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
fi

# Set icon path
ICON_PATH="assets/AppIcon.icns"
EXTRA_ICON_ARGS=""
if [ -f "$ICON_PATH" ]; then
    EXTRA_ICON_ARGS="--icon $ICON_PATH"
    echo "Using icon: $ICON_PATH"
else
    echo "No icon found, using default."
fi

# Set bundle ID
OSX_BUNDLE_ID="${OSX_BUNDLE_ID:-com.fhtools.fhbinningtool}"

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist build

# Build with PyInstaller
echo "Building macOS app..."
pyinstaller \
    --windowed \
    --noconfirm \
    --target-arch "$TARGET_ARCH" \
    --name FHBinningTool \
    --add-data "config.json:." \
    --add-data "style.qss:." \
    --osx-bundle-identifier "$OSX_BUNDLE_ID" \
    $EXTRA_ICON_ARGS \
    src/ui/main_window.py

echo ""
echo "=========================================="
echo "Build completed successfully!"
echo "Output: $ROOT_DIR/dist/FHBinningTool.app"
echo "=========================================="

# Create DMG (optional, if create-dmg is installed)
if command -v create-dmg &> /dev/null; then
    echo "Creating DMG package..."
    create-dmg \
        --volname "FHBinningTool Installer" \
        --window-pos 200 120 \
        --window-size 600 400 \
        --icon-size 100 \
        --app-drop-link 450 185 \
        "dist/FHBinningTool.dmg" \
        "dist/FHBinningTool.app" || echo "DMG creation skipped."
else
    echo "Tip: Install create-dmg to generate DMG package."
    echo "  brew install create-dmg"
fi
