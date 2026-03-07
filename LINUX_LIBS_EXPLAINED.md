# Linux 系统依赖库详解

## 这些库是什么？

### 1. libgl1-mesa-glx (OpenGL)

**是什么**:
- OpenGL 的 Mesa 软件实现
- 用于 3D/2D 图形渲染
- PyQt6 和 pyqtgraph 需要它来绘制图表

**包含什么**:
```
libGL.so.1          - OpenGL 主库
libEGL.so.1         - EGL 接口
libGLESv2.so.2      - OpenGL ES 2.0
```

**在云桌面中**:
- ✅ 通常已预装（云桌面需要图形支持）
- ⚠️ 可能没有硬件加速，使用软件渲染（llvmpipe）
- ⚠️ 某些云桌面使用虚拟 GPU（如 VirGL），可能需要特定驱动

### 2. libglib2.0-0 (GLib)

**是什么**:
- GTK/GNOME 项目的底层 C 库
- 提供数据结构、事件循环、线程等基础功能
- Qt 也依赖它的一些组件

**包含什么**:
```
libglib-2.0.so.0    - 核心功能
libgobject-2.0.so.0 - 对象系统
libgio-2.0.so.0     - I/O 抽象
```

**在云桌面中**:
- ✅ **100% 已安装**，这是 Linux 桌面系统的基础
- 没有它，桌面环境本身都无法运行

### 3. 其他常见的依赖

| 库 | 用途 | 云桌面通常有? |
|----|------|-------------|
| libX11.so.6 | X11 协议客户端 | ✅ 是 |
| libXext.so.6 | X 扩展 | ✅ 是 |
| libSM.so.6 | 会话管理 | ✅ 是 |
| libxcb.so.1 | X C Binding | ✅ 是 |
| libfontconfig.so.1 | 字体配置 | ✅ 是 |
| libfreetype.so.6 | 字体渲染 | ✅ 是 |

---

## 统信 UOS / 银河麒麟 V10 云桌面

### 典型云桌面环境

统信 UOS 和麒麟 V10 的云桌面通常基于以下技术栈：

```
┌─────────────────────────────────────┐
│         云桌面客户端 (SPICE/PCoIP)   │
├─────────────────────────────────────┤
│  UKUI / DDE (桌面环境)               │
│  ├── Qt5/Qt6 应用框架               │
│  ├── OpenGL (软件/虚拟渲染)          │
│  └── X11 / Wayland                  │
├─────────────────────────────────────┤
│  Linux 内核 + Mesa (OpenGL)         │
└─────────────────────────────────────┘
```

### 依赖库状态

**在云桌面系统中，这些库的状态**:

| 库 | 云桌面状态 | 说明 |
|----|-----------|------|
| libgl1-mesa-glx | ✅ 已安装 | 但可能是软件渲染 |
| libglib2.0-0 | ✅ 已安装 | 桌面环境基础 |
| libX11.so.6 | ✅ 已安装 | X11 必需 |
| libQt6*.so.6 | ⚠️ 可能无 | UOS/麒麟主要用 Qt5 |

### 云桌面特殊考虑

#### 1. Qt5 vs Qt6

统信 UOS 和麒麟 V10 的系统应用主要基于 **Qt5**：

```bash
# 检查系统 Qt 版本
ls /usr/lib/x86_64-linux-gnu/libQt*.so

# 典型输出（以 Qt5 为主）
libQt5Core.so.5
libQt5Gui.so.5
libQt5Widgets.so.5
# 可能没有 libQt6*
```

**影响**: 你的应用使用 PyQt6，已经打包了 Qt6 库，所以不依赖系统的 Qt。但需要确保 Qt6 的 OpenGL 支持在云桌面能正常工作。

#### 2. OpenGL 渲染方式

云桌面通常使用以下 OpenGL 方案：

| 方案 | 说明 | 性能 |
|------|------|------|
| **VirGL** | 虚拟 GPU，GPU 虚拟化 | 较好 |
| **llvmpipe** | 纯软件渲染，使用 CPU | 一般 |
| **SPICE 图形** | 远程协议自带压缩传输 | 视网络而定 |

**检查当前 OpenGL 渲染**:
```bash
# 查看 OpenGL 信息
glxinfo | grep "OpenGL renderer"

# 典型云桌面输出
OpenGL renderer string: llvmpipe (LLVM 12.0.0, 256 bits)  # 软件渲染
# 或
OpenGL renderer string: virgl (AMD Radeon Pro W6800)      # 虚拟 GPU
```

#### 3. 可能遇到的问题

**问题 1: Qt6 与 X11 兼容性**
```bash
# 错误信息
qt.qpa.xcb: could not connect to display
qt.qpa.plugin: Could not load the Qt platform plugin "xcb"
```

**解决**: 确保打包了 Qt6 的 XCB 平台插件，或设置：
```bash
export QT_QPA_PLATFORM=xcb
export QT_QPA_PLATFORM_PLUGIN_PATH=/path/to/PyQt6/Qt6/plugins
```

**问题 2: 软件渲染性能**
```bash
# 如果使用 llvmpipe，复杂图表可能卡顿
# 解决: 降低图表复杂度，或要求配置虚拟 GPU
```

**问题 3: 字体渲染**
云桌面可能没有完整的中文字体：
```bash
# 检查中文字体
fc-list :lang=zh

# 如果缺少，安装
sudo apt-get install fonts-wqy-zenhei fonts-wqy-microhei
```

---

## 云桌面优化建议

### 1. 检测脚本优化

针对云桌面环境，更新 `check_deps.sh`:

```bash
#!/bin/bash
echo "检查 FHBinningTool 系统依赖..."
echo "================================"

# 检查 OpenGL
echo -n "OpenGL 支持: "
if ldconfig -p | grep -q libGL.so.1; then
    echo "✓ 已安装"
    # 检查渲染方式
    if command -v glxinfo &> /dev/null; then
        RENDERER=$(glxinfo 2>/dev/null | grep "OpenGL renderer" | cut -d: -f2)
        echo "  渲染器:$RENDERER"
    fi
else
    echo "✗ 缺失"
fi

# 检查 GLib（云桌面一定有）
echo -n "GLib 库: "
if ldconfig -p | grep -q libglib-2.0.so.0; then
    echo "✓ 已安装"
else
    echo "✗ 缺失（异常，云桌面应已安装）"
fi

# 检查 X11
echo -n "X11 客户端: "
if ldconfig -p | grep -q libX11.so.6; then
    echo "✓ 已安装"
else
    echo "✗ 缺失（异常，云桌面应已安装）"
fi

# 检查中文字体
echo -n "中文字体: "
if fc-list :lang=zh | grep -q .; then
    COUNT=$(fc-list :lang=zh | wc -l)
    echo "✓ 已安装 ($COUNT 个)"
else
    echo "⚠ 未检测到（建议安装 fonts-wqy-zenhei）"
fi

echo ""
echo "================================"
echo "云桌面环境通常已包含所有基础依赖"
echo "如有问题，请联系云桌面管理员"
```

### 2. 启动脚本优化

```bash
#!/bin/bash
# run.sh - 云桌面优化版

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 检测云桌面环境
IS_CLOUD_DESKTOP=false
if [ -n "$SPICE_DISPLAY" ] || [ -n "$VDPAU_DRIVER" ] || 
   systemctl is-active --quiet spice-vdagentd 2>/dev/null; then
    IS_CLOUD_DESKTOP=true
    echo "检测到云桌面环境"
fi

# 设置 Qt 平台插件
export QT_QPA_PLATFORM_PLUGIN_PATH="$SCRIPT_DIR/PyQt6/Qt6/plugins"

# 云桌面特定优化
if [ "$IS_CLOUD_DESKTOP" = true ]; then
    # 强制使用 XCB（更稳定）
    export QT_QPA_PLATFORM=xcb
    
    # 禁用 GPU 加速（如果出现问题）
    # export QT_OPENGL=software
    
    # 优化字体渲染
    export QT_XFT=true
fi

# 启动程序
exec "$SCRIPT_DIR/FHBinningTool" "$@"
```

### 3. 打包策略调整

对于云桌面部署，可以简化依赖检查：

```bash
# build_cloud_desktop.sh - 云桌面专用构建
#!/bin/bash

# 1. 正常构建
bash scripts/build_linux_static.sh

# 2. 创建云桌面专用说明
cat > "dist/FHBinningTool/CLOUD_DESKTOP_README.txt" << 'EOF'
云桌面部署说明
==============

统信 UOS / 银河麒麟 V10 云桌面通常已包含所有必需依赖。

快速启动:
    ./run.sh

如遇到显示问题:
    1. 检查 OpenGL: glxinfo | grep "OpenGL renderer"
    2. 如果是 llvmpipe（软件渲染），图表功能正常但性能一般
    3. 如果是 VirGL，性能较好

技术支持: xxx@company.com
EOF

# 3. 创建静默安装脚本
cat > "dist/FHBinningTool/install_silent.sh" << 'EOF'
#!/bin/bash
# 静默安装到 /opt（需要管理员权限）
INSTALL_DIR="/opt/fhbinningtool"
sudo mkdir -p "$INSTALL_DIR"
sudo cp -r "$(dirname "$0")/"* "$INSTALL_DIR/"
sudo chmod +x "$INSTALL_DIR/FHBinningTool"
sudo chmod +x "$INSTALL_DIR/run.sh"

# 创建全局命令
sudo ln -sf "$INSTALL_DIR/run.sh" /usr/local/bin/fhbinningtool

echo "安装完成，运行: fhbinningtool"
EOF
chmod +x "dist/FHBinningTool/install_silent.sh"
```

---

## 总结

### 你的担心是对的

对于 **统信 UOS / 麒麟 V10 云桌面**：

| 库 | 是否已安装 | 是否需要检查 |
|----|-----------|-------------|
| libgl1-mesa-glx | ✅ 是 | 可选 |
| libglib2.0-0 | ✅ 是（100%） | 无需 |
| libX11.so.6 | ✅ 是（100%） | 无需 |

### 建议

1. **云桌面部署** - 可以简化依赖检查，因为基础库一定存在
2. **物理机部署** - 建议保留依赖检查，因为可能有最小化安装
3. **混合部署** - 使用检测脚本自动判断环境

### 一句话

> 统信 UOS / 麒麟 V10 云桌面**一定已经安装了** libglib2.0-0 和 X11 库，**很可能已经安装了** OpenGL（虽然可能是软件渲染）。你的程序在这些系统上应该可以直接运行，不需要用户额外安装系统包。
