#!/usr/bin/env bash
# FHBinningTool Linux Build Script
# Supports: Debian/Ubuntu based systems (统信UOS, 银河麒麟V10)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "FHBinningTool Linux Build Script"
echo "=========================================="
echo "Project root: $ROOT_DIR"

# Detect Linux distribution
 detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    else
        echo "unknown"
    fi
}

DISTRO=$(detect_distro)
echo "Detected distribution: $DISTRO"

# Check Python version
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        echo "Found Python: $PYTHON_VERSION"
        
        # Check if version is >= 3.9
        MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
        MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
        
        if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 9 ]); then
            echo "[ERROR] Python 3.9+ is required"
            exit 1
        fi
    else
        echo "[ERROR] Python3 not found. Please install Python 3.9+."
        exit 1
    fi
}

check_python

# Install system dependencies for Linux (统信UOS/麒麟V10)
install_system_deps() {
    echo "Installing system dependencies..."
    
    case "$DISTRO" in
        uos|kylin|debian|ubuntu|deepin)
            echo "Installing dependencies for Debian/Ubuntu based system..."
            sudo apt-get update || true
            sudo apt-get install -y \
                python3-dev \
                python3-pip \
                python3-venv \
                libgl1-mesa-glx \
                libglib2.0-0 \
                libsm6 \
                libxext6 \
                libxrender-dev \
                libgomp1 \
                libqt6gui6 \
                libqt6network6 \
                libqt6widgets6 \
                libqt6core6 || {
                echo "[WARNING] Some system packages may not be available, continuing..."
            }
            ;;
        centos|rhel|fedora|rocky|almalinux)
            echo "Installing dependencies for RHEL/CentOS based system..."
            sudo yum install -y \
                python3-devel \
                mesa-libGL \
                glib2 \
                libSM \
                libXext \
                libXrender \
                libgomp || {
                echo "[WARNING] Some system packages may not be available, continuing..."
            }
            ;;
        *)
            echo "[WARNING] Unknown distribution. Please install system dependencies manually."
            ;;
    esac
}

# Ask for system dependencies installation
if [ "${INSTALL_DEPS:-0}" == "1" ]; then
    install_system_deps
else
    echo "Tip: Run with INSTALL_DEPS=1 to install system dependencies automatically."
    echo "Example: INSTALL_DEPS=1 bash scripts/build_linux.sh"
fi

# Create virtual environment
cd "$ROOT_DIR"

if [ ! -d venv ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install PyInstaller
echo "Installing PyInstaller..."
pip install pyinstaller

# Install requirements
echo "Installing Python dependencies..."
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
fi

# Set icon path
ICON_PATH="assets/AppIcon.png"
EXTRA_ICON_ARGS=""
if [ -f "$ICON_PATH" ]; then
    EXTRA_ICON_ARGS="--icon $ICON_PATH"
    echo "Using icon: $ICON_PATH"
else
    echo "No icon found, using default."
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist build

# Determine architecture
ARCH=$(uname -m)
echo "Target architecture: $ARCH"

# Build with PyInstaller
echo "Building Linux executable..."
pyinstaller \
    --windowed \
    --noconfirm \
    --name FHBinningTool \
    --add-data "config.json:." \
    --add-data "style.qss:." \
    --hidden-import PyQt6.sip \
    --hidden-import sklearn.tree._utils \
    --hidden-import scipy.special.cython_special \
    $EXTRA_ICON_ARGS \
    src/ui/main_window.py

# Create desktop entry
echo "Creating desktop entry..."
cat > "dist/FHBinningTool/FHBinningTool.desktop" << EOF
[Desktop Entry]
Name=FHBinningTool
Name[zh_CN]=风控数据分箱工具
Comment=Risk Control Binning Tool
Comment[zh_CN]=风险数据分箱分析工具
Exec=\$(dirname \%k)/FHBinningTool
Icon=\$(dirname \%k)/FHBinningTool
Type=Application
Categories=Office;Finance;
Terminal=false
StartupNotify=true
EOF

chmod +x "dist/FHBinningTool/FHBinningTool"
chmod +x "dist/FHBinningTool/FHBinningTool.desktop"

echo ""
echo "=========================================="
echo "Build completed successfully!"
echo "Output: $ROOT_DIR/dist/FHBinningTool"
echo "Executable: $ROOT_DIR/dist/FHBinningTool/FHBinningTool"
echo "=========================================="

# Create distribution package
echo "Creating distribution package..."
mkdir -p "dist/package"
cp -r "dist/FHBinningTool/"* "dist/package/"

# Create install script
cat > "dist/package/install.sh" << 'INSTALL_EOF'
#!/bin/bash
# FHBinningTool Linux Installer

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/opt/FHBinningTool}"

echo "Installing FHBinningTool to $INSTALL_DIR..."

mkdir -p "$INSTALL_DIR"
cp -r "$SCRIPT_DIR/"* "$INSTALL_DIR/"

# Create bin directory
mkdir -p "$HOME/.local/bin"
ln -sf "$INSTALL_DIR/FHBinningTool" "$HOME/.local/bin/fhbinningtool"

# Create desktop entry
mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/fhbinningtool.desktop" << EOF
[Desktop Entry]
Name=FHBinningTool
Name[zh_CN]=风控数据分箱工具
Comment=Risk Control Binning Tool
Exec=$INSTALL_DIR/FHBinningTool
Icon=$INSTALL_DIR/FHBinningTool
Type=Application
Categories=Office;Finance;
Terminal=false
EOF

echo "Installation completed!"
echo "Run: $HOME/.local/bin/fhbinningtool"
echo "Or use the desktop entry in your applications menu."
INSTALL_EOF

chmod +x "dist/package/install.sh"

echo ""
echo "Package created at: $ROOT_DIR/dist/package"
echo "Run 'dist/package/install.sh' to install system-wide."
