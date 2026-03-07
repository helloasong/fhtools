#!/usr/bin/env bash
# FHBinningTool Linux Static Build Script
# 尽可能静态链接依赖，减少目标系统的依赖要求

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "FHBinningTool Linux Static Build"
echo "(最小化系统依赖要求)"
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

# Check Python
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        echo "Found Python: $PYTHON_VERSION"
        
        MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
        MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
        
        if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 9 ]); then
            echo "[ERROR] Python 3.9+ is required"
            exit 1
        fi
    else
        echo "[ERROR] Python3 not found"
        exit 1
    fi
}

check_python

# Function to check if we can build truly static binary
can_build_static() {
    # Check for staticx or similar tools
    if command -v staticx &> /dev/null; then
        return 0
    fi
    return 1
}

cd "$ROOT_DIR"

# Create virtual environment
if [ ! -d venv ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade build tools
echo "Upgrading build tools..."
pip install --upgrade pip setuptools wheel

# Install PyInstaller
echo "Installing PyInstaller..."
pip install pyinstaller

# Try to install staticx for truly static builds
if can_build_static; then
    echo "Found staticx - will build fully static binary"
else
    echo "Note: Install 'staticx' for fully static builds: pip install staticx"
    echo "Current build will still require some system libraries"
fi

# Install requirements with specific options for Linux
echo "Installing project dependencies..."
pip install -r requirements.txt

# Additional dependencies that might be needed on Linux
echo "Installing Linux-specific dependencies..."
pip install -U PyQt6-Qt6 2>/dev/null || echo "Using system PyQt6"

# Set icon
ICON_PATH="assets/AppIcon.png"
EXTRA_ICON_ARGS=""
if [ -f "$ICON_PATH" ]; then
    EXTRA_ICON_ARGS="--icon $ICON_PATH"
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist build

# Get architecture
ARCH=$(uname -m)
echo "Target architecture: $ARCH"

# Determine if we're on a musl-based system (Alpine)
LIBC_TYPE=$(ldd --version 2>&1 | head -1 | grep -i musl > /dev/null && echo "musl" || echo "glibc")
echo "C Library type: $LIBC_TYPE"

# Build with PyInstaller
echo "Building Linux executable..."
pyinstaller \
    --windowed \
    --noconfirm \
    --name FHBinningTool \
    --add-data "config.json:." \
    --add-data "style.qss:." \
    --hidden-import PyQt6.sip \
    --hidden-import PyQt6.QtCore \
    --hidden-import PyQt6.QtGui \
    --hidden-import PyQt6.QtWidgets \
    --hidden-import sklearn.tree._utils \
    --hidden-import sklearn.utils._typedefs \
    --hidden-import sklearn.utils._heap \
    --hidden-import sklearn.utils._sorting \
    --hidden-import sklearn.utils._vector_sentinel \
    --hidden-import scipy.special.cython_special \
    --hidden-import scipy.special._ufuncs_cxx \
    --hidden-import pandas._libs.tslibs.base \
    --hidden-import pandas._libs.tslibs.np_datetime \
    --hidden-import pandas._libs.tslibs.nattype \
    --hidden-import openpyxl \
    --hidden-import qt_material \
    --hidden-import pyqtgraph \
    --collect-all PyQt6 \
    --collect-all qt_material \
    --collect-all pyqtgraph \
    $EXTRA_ICON_ARGS \
    src/ui/main_window.py

# If staticx is available, create a truly static binary
if can_build_static; then
    echo "Creating static binary with staticx..."
    staticx "dist/FHBinningTool/FHBinningTool" "dist/FHBinningTool/FHBinningTool_static" 2>/dev/null || {
        echo "Staticx build failed, using regular build"
    }
fi

# Copy Qt plugins
echo "Setting up Qt plugins..."
QT_PLUGIN_PATH=$(python3 -c "import PyQt6; import os; print(os.path.join(os.path.dirname(PyQt6.__file__), 'Qt6', 'plugins'))" 2>/dev/null || echo "")
if [ -n "$QT_PLUGIN_PATH" ] && [ -d "$QT_PLUGIN_PATH" ]; then
    mkdir -p "dist/FHBinningTool/PyQt6/Qt6/plugins"
    cp -r "$QT_PLUGIN_PATH"/* "dist/FHBinningTool/PyQt6/Qt6/plugins/" 2>/dev/null || true
fi

# Create wrapper script that sets up environment
cat > "dist/FHBinningTool/run.sh" << 'EOF'
#!/bin/bash
# FHBinningTool Launcher Script

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export QT_QPA_PLATFORM_PLUGIN_PATH="$SCRIPT_DIR/PyQt6/Qt6/plugins"
export QT_QPA_PLATFORM=xcb

# Check for required libraries
missing_libs=()
for lib in libGL.so.1 libglib-2.0.so.0; do
    if ! ldconfig -p | grep -q "$lib"; then
        missing_libs+=("$lib")
    fi
done

if [ ${#missing_libs[@]} -ne 0 ]; then
    echo "警告: 缺少以下系统库，程序可能无法正常运行:"
    for lib in "${missing_libs[@]}"; do
        echo "  - $lib"
    done
    echo ""
    echo "请安装系统依赖:"
    echo "  Debian/Ubuntu/统信UOS/麒麟: sudo apt-get install libgl1-mesa-glx libglib2.0-0"
    echo "  RHEL/CentOS/Rocky: sudo yum install mesa-libGL glib2"
    echo ""
    read -p "是否继续运行? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

exec "$SCRIPT_DIR/FHBinningTool" "$@"
EOF
chmod +x "dist/FHBinningTool/run.sh"

# Create desktop entry
cat > "dist/FHBinningTool/FHBinningTool.desktop" << EOF
[Desktop Entry]
Name=FHBinningTool
Name[zh_CN]=风控数据分箱工具
Comment=Risk Control Binning Tool
Comment[zh_CN]=风险数据分箱分析工具
Exec=\$(dirname \%k)/run.sh
Icon=\$(dirname \%k)/FHBinningTool
Type=Application
Categories=Office;Finance;
Terminal=false
StartupNotify=true
EOF
chmod +x "dist/FHBinningTool/FHBinningTool.desktop"

# Create dependency check script
cat > "dist/FHBinningTool/check_deps.sh" << 'EOF'
#!/bin/bash
# Check system dependencies

echo "检查系统依赖..."
echo "================"

missing=()

# Check for common libraries
check_lib() {
    if ldconfig -p | grep -q "$1"; then
        echo "✓ $1"
    else
        echo "✗ $1 - 缺失"
        missing+=("$1")
    fi
}

echo "检查图形库..."
check_lib "libGL.so.1"
check_lib "libglib-2.0.so.0"
check_lib "libX11.so.6"
check_lib "libXext.so.6"

echo ""
echo "检查字体渲染..."
check_lib "libfontconfig.so.1"
check_lib "libfreetype.so.6"

if [ ${#missing[@]} -ne 0 ]; then
    echo ""
    echo "缺失的依赖:"
    for lib in "${missing[@]}"; do
        echo "  - $lib"
    done
    echo ""
    echo "安装命令:"
    echo "  Debian/Ubuntu/统信UOS/麒麟:"
    echo "    sudo apt-get install libgl1-mesa-glx libglib2.0-0 libsm6 libxext6"
    echo ""
    echo "  RHEL/CentOS/Rocky:"
    echo "    sudo yum install mesa-libGL glib2 libSM libXext"
    exit 1
else
    echo ""
    echo "✓ 所有系统依赖已满足"
fi
EOF
chmod +x "dist/FHBinningTool/check_deps.sh"

# Create comprehensive README
cat > "dist/FHBinningTool/README.txt" << 'EOF'
FHBinningTool 风控数据分箱工具
===============================

系统要求
--------
- 操作系统: Linux (glibc 2.17+ 或 musl)
- 推荐发行版: Ubuntu 20.04+, Debian 10+, 统信UOS 20+, 银河麒麟V10
- 内存: 4GB+
- 磁盘: 500MB 可用空间

启动方式
--------
1. 双击 FHBinningTool （需要文件管理器支持）
2. 或运行: ./run.sh
3. 或运行: ./FHBinningTool

系统依赖检查
------------
运行以下命令检查系统依赖:
    ./check_deps.sh

如果缺少依赖，请安装:

  Debian/Ubuntu/统信UOS/银河麒麟:
    sudo apt-get install libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender1

  RHEL/CentOS/Rocky/AlmaLinux:
    sudo yum install mesa-libGL glib2 libSM libXext libXrender

  Arch Linux:
    sudo pacman -S mesa glib2 libsm libxext libxrender

故障排查
--------

1. 程序无法启动，报错关于 Qt 平台插件:
   运行: QT_QPA_PLATFORM=xcb ./FHBinningTool
   或直接使用: ./run.sh

2. 界面显示异常:
   检查显卡驱动是否安装正确
   尝试: QT_QPA_PLATFORM=offscreen ./FHBinningTool

3. 字体显示问题:
   安装字体: sudo apt-get install fonts-wqy-zenhei (中文)

数据存储
--------
项目数据默认保存在: ~/.local/share/FHBinningTool/projects
可通过环境变量修改: export FHBINNINGTOOL_PROJECT_ROOT=/your/path

技术支持
--------
如有问题，请联系技术支持团队。
EOF

# Create install script
cat > "dist/FHBinningTool/install.sh" << 'EOF'
#!/bin/bash
# FHBinningTool Linux Installer

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/opt/FHBinningTool}"

echo "Installing FHBinningTool to $INSTALL_DIR..."

# Check dependencies first
if [ -f "$SCRIPT_DIR/check_deps.sh" ]; then
    echo "Checking dependencies..."
    bash "$SCRIPT_DIR/check_deps.sh" || {
        echo ""
        echo "依赖检查失败，是否继续安装? (y/N)"
        read -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    }
fi

# Create install directory
mkdir -p "$INSTALL_DIR"
cp -r "$SCRIPT_DIR/"* "$INSTALL_DIR/"

# Create bin directory and symlink
mkdir -p "$HOME/.local/bin"
ln -sf "$INSTALL_DIR/run.sh" "$HOME/.local/bin/fhbinningtool"

# Create desktop entry
mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/fhbinningtool.desktop" << DESKTOP_EOF
[Desktop Entry]
Name=FHBinningTool
Name[zh_CN]=风控数据分箱工具
Comment=Risk Control Binning Tool
Exec=$INSTALL_DIR/run.sh
Icon=$INSTALL_DIR/FHBinningTool
Type=Application
Categories=Office;Finance;
Terminal=false
DESKTOP_EOF

echo ""
echo "Installation completed!"
echo ""
echo "启动方式:"
echo "  命令行: $HOME/.local/bin/fhbinningtool"
echo "  或: $INSTALL_DIR/run.sh"
echo "  或在应用菜单中查找 'FHBinningTool'"
echo ""
echo "确保 ~/.local/bin 在 PATH 中:"
echo '  export PATH="$HOME/.local/bin:$PATH"'
EOF
chmod +x "dist/FHBinningTool/install.sh"

echo ""
echo "=========================================="
echo "Build completed successfully!"
echo "Output: $ROOT_DIR/dist/FHBinningTool"
echo "=========================================="
echo ""
echo "重要说明:"
echo "1. 此构建已包含所有 Python 依赖和 Qt 库"
echo "2. 目标系统仍需要基本的图形库 (OpenGL, X11)"
echo "3. 运行 ./check_deps.sh 检查系统依赖"
echo "4. 运行 ./install.sh 安装到系统"
echo ""

# Show what libraries are still needed
echo "检查目标系统可能需要的库..."
ldd "dist/FHBinningTool/FHBinningTool" 2>/dev/null | grep "not found" | head -10 || echo "✓ 所有库已找到或已打包"
