#!/bin/bash
# FHBinningTool macOS 一键安装脚本
# 使用方式：
#   1. 解压 FHBinningTool-v*-macos-*.zip
#   2. 在解压出的文件夹中双击或运行 ./install.sh
#   脚本会自动把 .app 复制到 /Applications 并移除 Gatekeeper 隔离属性

set -e

APP_NAME="FHBinningTool"
APP_FILE="${APP_NAME}.app"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_APP="${SCRIPT_DIR}/${APP_FILE}"
TARGET_APP="/Applications/${APP_FILE}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "FHBinningTool macOS 安装程序"
echo "=========================================="

# 检查 .app 是否存在
if [ ! -d "$SOURCE_APP" ]; then
    echo -e "${RED}错误：在当前目录未找到 ${APP_FILE}${NC}"
    echo "请确保 install.sh 和 ${APP_FILE} 在同一目录。"
    exit 1
fi

# 检查是否以普通用户运行（安装到 /Applications 通常不需要 sudo，但可能需要）
if [ ! -w "/Applications" ]; then
    echo -e "${YELLOW}警告：当前用户对 /Applications 没有写入权限。${NC}"
    echo "安装可能需要输入管理员密码。"
fi

echo ""
echo "正在安装 ${APP_NAME} 到 /Applications ..."

# 如果已存在则先删除旧版本
if [ -d "$TARGET_APP" ]; then
    echo "发现旧版本，正在替换 ..."
    rm -rf "$TARGET_APP"
fi

# 复制到 Applications
cp -R "$SOURCE_APP" "$TARGET_APP"

echo "安装完成：${TARGET_APP}"

# 移除 Gatekeeper 隔离属性
echo ""
echo "正在移除安全隔离属性（解决 'Apple 无法验证' 提示）..."
if xattr -d com.apple.quarantine "$TARGET_APP" 2>/dev/null; then
    echo -e "${GREEN}✓ 隔离属性已移除${NC}"
else
    echo "常规移除失败，尝试递归清除 ..."
    xattr -cr "$TARGET_APP"
    echo -e "${GREEN}✓ 隔离属性已递归清除${NC}"
fi

echo ""
echo -e "${GREEN}✓ ${APP_NAME} 安装成功！${NC}"
echo ""
echo "启动方式："
echo "  1. 在启动台或应用程序文件夹中打开 ${APP_NAME}"
echo "  2. 运行本目录下的 ./start.sh"
echo "  3. 终端运行：open \"${TARGET_APP}\""
echo ""

# 询问是否立即启动
read -p "是否立即启动 ${APP_NAME}？(y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    open "$TARGET_APP"
fi
