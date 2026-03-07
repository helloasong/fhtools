#!/usr/bin/env bash
# FHBinningTool 一键打包脚本（含自动压缩）
# 自动检测平台、执行打包、压缩输出

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "FHBinningTool 自动打包脚本"
echo "=========================================="

# 检测操作系统
OS="unknown"
ARCH="$(uname -m)"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
    OS="windows"
fi

echo "检测到操作系统: $OS ($ARCH)"

# 获取版本号（从代码或配置文件）
VERSION="1.0.0"
if [ -f "config.json" ]; then
    VERSION=$(grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' config.json 2>/dev/null | cut -d'"' -f4 || echo "1.0.0")
fi
echo "版本: $VERSION"

# 检查 Python
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo -e "${RED}错误: 未找到 Python，请先安装 Python 3.9+${NC}"
    exit 1
fi

PYTHON_CMD=$(command -v python3 || command -v python)
echo "使用 Python: $PYTHON_CMD"

# 创建虚拟环境
echo ""
echo "步骤 1/5: 创建虚拟环境..."
if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
fi

# 激活虚拟环境
if [ "$OS" == "windows" ]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# 安装依赖
echo ""
echo "步骤 2/5: 安装依赖..."
pip install --upgrade pip -q
pip install pyinstaller -q
pip install -r requirements.txt -q

# 清理旧的构建
echo ""
echo "步骤 3/5: 清理旧的构建..."
rm -rf dist build
mkdir -p release

# 执行打包
echo ""
echo "步骤 4/5: 开始打包..."

if [ "$OS" == "windows" ]; then
    echo "Windows 平台 - 使用目录模式打包..."
    pyinstaller \
        --windowed \
        --noconfirm \
        --name FHBinningTool \
        --add-data "config.json;." \
        --add-data "style.qss;." \
        --hidden-import PyQt6.sip \
        --hidden-import sklearn.tree._utils \
        --hidden-import scipy.special.cython_special \
        --hidden-import openpyxl \
        src/ui/main_window.py
    
    OUTPUT_DIR="dist/FHBinningTool"
    EXECUTABLE="FHBinningTool.exe"
    
elif [ "$OS" == "macos" ]; then
    echo "macOS 平台 - 构建 .app 包..."
    pyinstaller \
        --windowed \
        --noconfirm \
        --name FHBinningTool \
        --add-data "config.json:." \
        --add-data "style.qss:." \
        --osx-bundle-identifier "com.fhtools.fhbinningtool" \
        src/ui/main_window.py
    
    OUTPUT_DIR="dist/FHBinningTool.app"
    EXECUTABLE="FHBinningTool.app"
    
else
    echo "Linux 平台 - 构建可执行文件..."
    pyinstaller \
        --windowed \
        --noconfirm \
        --name FHBinningTool \
        --add-data "config.json:." \
        --add-data "style.qss:." \
        --hidden-import PyQt6.sip \
        --hidden-import sklearn.tree._utils \
        --hidden-import scipy.special.cython_special \
        --hidden-import openpyxl \
        src/ui/main_window.py
    
    # 创建启动脚本
    cat > dist/FHBinningTool/run.sh << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export QT_QPA_PLATFORM_PLUGIN_PATH="$SCRIPT_DIR/PyQt6/Qt6/plugins"
exec "$SCRIPT_DIR/FHBinningTool" "$@"
EOF
    chmod +x dist/FHBinningTool/run.sh
    
    # 创建 README
    cat > dist/FHBinningTool/README.txt << 'EOF'
FHBinningTool 风控数据分箱工具
===============================

启动方式:
  ./run.sh
  或
  ./FHBinningTool

系统要求:
  - Linux (glibc 2.17+)
  - 推荐: Ubuntu 20.04+, Debian 10+, 统信UOS 20+, 银河麒麟V10

云桌面说明:
  统信UOS/麒麟V10云桌面通常已包含所有依赖，可直接运行。

技术支持: 请联系您的系统管理员
EOF
    
    OUTPUT_DIR="dist/FHBinningTool"
    EXECUTABLE="FHBinningTool"
fi

# 检查构建结果
echo ""
echo "步骤 5/5: 验证并压缩..."

BUILD_SUCCESS=false
PACKAGE_NAME=""
PACKAGE_PATH=""

if [ "$OS" == "windows" ]; then
    if [ -f "dist/FHBinningTool/FHBinningTool.exe" ]; then
        BUILD_SUCCESS=true
        
        # 获取文件大小
        SIZE=$(du -sh dist/FHBinningTool 2>/dev/null | cut -f1 || echo "unknown")
        
        # Windows: 使用 PowerShell 压缩（如果在 Git Bash）或 zip
        PACKAGE_NAME="FHBinningTool-v${VERSION}-windows-${ARCH}.zip"
        PACKAGE_PATH="release/${PACKAGE_NAME}"
        
        echo "压缩为 zip 文件..."
        if command -v zip &> /dev/null; then
            cd dist && zip -r "../${PACKAGE_PATH}" FHBinningTool && cd ..
        else
            # 使用 PowerShell
            powershell -Command "Compress-Archive -Path 'dist\FHBinningTool\*' -DestinationPath '${PACKAGE_PATH}' -Force"
        fi
    fi
    
elif [ "$OS" == "macos" ]; then
    if [ -d "dist/FHBinningTool.app" ]; then
        BUILD_SUCCESS=true
        
        # macOS: 创建 dmg 或 zip
        SIZE=$(du -sh dist/FHBinningTool.app 2>/dev/null | cut -f1 || echo "unknown")
        
        # 先创建 zip（最通用）
        PACKAGE_NAME="FHBinningTool-v${VERSION}-macos-${ARCH}.zip"
        PACKAGE_PATH="release/${PACKAGE_NAME}"
        
        echo "压缩为 zip 文件..."
        # 使用 ditto 保持 macOS 扩展属性
        ditto -c -k --keepParent "dist/FHBinningTool.app" "$PACKAGE_PATH"
        
        # 尝试创建 DMG（如果 hdiutil 可用）
        if command -v hdiutil &> /dev/null; then
            DMG_NAME="FHBinningTool-v${VERSION}-macos-${ARCH}.dmg"
            DMG_PATH="release/${DMG_NAME}"
            echo "创建 DMG 镜像..."
            hdiutil create -volname "FHBinningTool" -srcfolder "dist/FHBinningTool.app" -ov -format UDZO "$DMG_PATH" 2>/dev/null || echo "DMG 创建失败，使用 zip 分发"
        fi
    fi
    
else
    if [ -f "dist/FHBinningTool/FHBinningTool" ]; then
        BUILD_SUCCESS=true
        
        # Linux: 创建 tar.gz
        SIZE=$(du -sh dist/FHBinningTool 2>/dev/null | cut -f1 || echo "unknown")
        
        PACKAGE_NAME="FHBinningTool-v${VERSION}-linux-${ARCH}.tar.gz"
        PACKAGE_PATH="release/${PACKAGE_NAME}"
        
        echo "压缩为 tar.gz 文件..."
        tar -czvf "$PACKAGE_PATH" -C dist FHBinningTool
    fi
fi

# 输出结果
echo ""
echo "=========================================="
if [ "$BUILD_SUCCESS" = true ]; then
    echo -e "${GREEN}✓ 打包成功!${NC}"
    echo ""
    echo "版本: v${VERSION}"
    echo "平台: ${OS} (${ARCH})"
    echo "大小: ${SIZE}"
    echo ""
    echo -e "${BLUE}分发文件路径:${NC}"
    echo "  $(pwd)/${PACKAGE_PATH}"
    
    # 显示文件详细信息
    if [ -f "$PACKAGE_PATH" ]; then
        echo ""
        ls -lh "$PACKAGE_PATH"
    fi
    
    # 如果有 dmg 也显示
    if [ -n "${DMG_PATH:-}" ] && [ -f "$DMG_PATH" ]; then
        echo ""
        echo -e "${BLUE}DMG 镜像:${NC}"
        echo "  $(pwd)/${DMG_PATH}"
        ls -lh "$DMG_PATH"
    fi
    
    echo ""
    echo "=========================================="
    echo ""
    echo "分发说明:"
    echo ""
    if [ "$OS" == "windows" ]; then
        echo "  1. 将 ${PACKAGE_NAME} 发送给用户"
        echo "  2. 用户解压后运行 FHBinningTool.exe"
        echo "  3. 注意: 极少数系统可能需要 VC++ Redistributable"
        echo "     https://aka.ms/vs/17/release/vc_redist.x64.exe"
        
    elif [ "$OS" == "macos" ]; then
        echo "  1. 将 ${PACKAGE_NAME} 发送给用户"
        echo "  2. 用户解压后拖入应用程序文件夹"
        echo "  3. 首次运行可能需要在 系统设置 > 隐私与安全性 中允许"
        
    else
        echo "  1. 将 ${PACKAGE_NAME} 发送给用户"
        echo "  2. 用户解压并运行:"
        echo "     tar -xzvf ${PACKAGE_NAME}"
        echo "     cd FHBinningTool"
        echo "     ./run.sh"
        echo "  3. 云桌面通常无需额外依赖"
    fi
    
    echo ""
    echo -e "${GREEN}打包完成！${NC}"
    
else
    echo -e "${RED}✗ 打包失败${NC}"
    echo "请检查上面的错误信息"
    exit 1
fi

echo ""
echo "=========================================="
