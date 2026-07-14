#!/bin/bash
# FHBinningTool macOS 启动脚本
# 优先启动当前目录下的 .app，如果不存在则尝试启动 /Applications 下的版本

set -e

APP_NAME="FHBinningTool"
APP_FILE="${APP_NAME}.app"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCAL_APP="${SCRIPT_DIR}/${APP_FILE}"
INSTALLED_APP="/Applications/${APP_FILE}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 优先使用当前目录的 app
if [ -d "$LOCAL_APP" ]; then
    TARGET_APP="$LOCAL_APP"
    echo "启动本地版本：${TARGET_APP}"
else
    TARGET_APP="$INSTALLED_APP"
    echo "启动已安装版本：${TARGET_APP}"
fi

# 检查 app 是否存在
if [ ! -d "$TARGET_APP" ]; then
    echo -e "${RED}错误：未找到 ${APP_FILE}${NC}"
    echo "请先运行 ./install.sh 安装到 /Applications。"
    exit 1
fi

# 尝试移除隔离属性（如果还存在的话）
if xattr -d com.apple.quarantine "$TARGET_APP" 2>/dev/null; then
    echo -e "${GREEN}✓ 已移除安全隔离属性${NC}"
fi

echo "正在启动 ${APP_NAME} ..."
open "$TARGET_APP"
