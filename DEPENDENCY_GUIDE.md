# FHBinningTool 依赖处理指南

本文档详细说明 FHBinningTool 的依赖类型，以及如何在打包时处理这些依赖。

## 依赖分类

### 1. Python 依赖 ✅ 已自动打包

| 依赖 | 用途 | 打包方式 |
|------|------|---------|
| PyQt6 | GUI 框架 | PyInstaller 自动收集 |
| qt-material | 主题样式 | PyInstaller 自动收集 |
| pyqtgraph | 图表绘制 | PyInstaller 自动收集 |
| pandas | 数据处理 | PyInstaller 自动收集 |
| numpy | 数值计算 | PyInstaller 自动收集 |
| scikit-learn | 机器学习 | PyInstaller 自动收集 |
| scipy | 科学计算 | PyInstaller 自动收集 |
| openpyxl | Excel 导出 | PyInstaller 自动收集 |
| matplotlib | 静态图表 | PyInstaller 自动收集 |

**结论**: Python 依赖已经由 PyInstaller 完整打包，用户无需安装 Python 环境。

---

### 2. 系统依赖 ⚠️ 部分需要目标系统提供

#### Windows 系统依赖

| 依赖 | 用途 | 是否已打包 | 用户操作 |
|------|------|-----------|---------|
| VC++ Runtime 2015-2022 | C++ 标准库 | ❌ 需安装 | 下载安装 |
| OpenGL 3.0+ | 图形渲染 | ✅ 系统自带 | 无需操作 |
| DirectX | 图形加速 | ✅ 系统自带 | 无需操作 |

**解决方案**:
1. **方案 A**: 在程序目录包含 VC++ Runtime 安装程序（推荐）
2. **方案 B**: 使用静态链接的 Python 解释器（实验性）
3. **方案 C**: 引导用户下载安装

**VC++ Redistributable 下载**:
- x64: https://aka.ms/vs/17/release/vc_redist.x64.exe
- x86: https://aka.ms/vs/17/release/vc_redist.x86.exe

#### Linux 系统依赖

| 依赖 | 用途 | 是否已打包 | 安装命令 (Debian/UOS/麒麟) |
|------|------|-----------|---------------------------|
| libGL.so.1 | OpenGL 渲染 | ❌ | `libgl1-mesa-glx` |
| libglib-2.0.so.0 | GLib 库 | ❌ | `libglib2.0-0` |
| libX11.so.6 | X11 客户端 | ❌ | `libx11-6` |
| libXext.so.6 | X 扩展 | ❌ | `libxext6` |
| libQt6*.so.6 | Qt6 运行库 | ✅ | 已打包 |

**解决方案**:
1. **方案 A**: 使用静态链接工具 (staticx) - 实验性
2. **方案 B**: 提供依赖检查脚本，指导用户安装
3. **方案 C**: 打包为 AppImage / Flatpak / Snap

#### macOS 系统依赖

| 依赖 | 用途 | 是否已打包 | 说明 |
|------|------|-----------|------|
| Cocoa Framework | GUI 基础 | ✅ 系统自带 | 无需操作 |
| OpenGL | 图形渲染 | ✅ 系统自带 | 无需操作 |
| Qt6 | GUI 框架 | ✅ 已打包 | PyInstaller 处理 |

**结论**: macOS 依赖最简单，通常无需用户额外操作。

---

## 推荐打包策略

### Windows 推荐方案

#### 方案 1: 目录版 + VC++ Redist（推荐）

```batch
:: 构建
scripts\build_windows_static.bat

:: 分发内容
FHBinningTool/
├── FHBinningTool.exe      # 主程序
├── *.dll                  # 依赖库
├── PyQt6/                 # Qt 库
├── config.json
├── style.qss
├── vc_redist.x64.exe      # VC++ 安装程序（可选但推荐）
├── 启动程序.bat            # 带提示的启动脚本
└── README.txt             # 用户说明
```

**优点**:
- 启动速度快
- 可包含 VC++ 安装程序
- 用户友好

#### 方案 2: 单文件版

```batch
pyinstaller FHBinningTool_windows_onefile.spec
```

**优点**:
- 只有一个文件，分发简单
- 用户无法误删依赖

**缺点**:
- 启动较慢（需要解压到临时目录）
- 无法附带额外文件

#### 方案 3: 安装包（最专业）

使用 Inno Setup 或 WiX Toolset 创建安装程序：

```
FHBinningTool_Setup.exe
├── 安装程序
├── 可选安装 VC++ Redist
├── 创建开始菜单快捷方式
└── 创建卸载程序
```

---

### Linux 推荐方案

#### 方案 1: 目录版 + 依赖检查（推荐）

```bash
# 构建
bash scripts/build_linux_static.sh

# 分发内容
FHBinningTool/
├── FHBinningTool           # 主程序
├── run.sh                  # 启动脚本（设置环境变量）
├── check_deps.sh           # 依赖检查脚本
├── install.sh              # 安装脚本
├── PyQt6/                  # Qt 库
├── config.json
├── style.qss
└── README.txt
```

**用户安装步骤**:
```bash
tar -xzvf FHBinningTool-linux.tar.gz
cd FHBinningTool
./check_deps.sh    # 检查依赖
./install.sh       # 安装到 ~/.local/opt/
```

#### 方案 2: AppImage（用户最方便）

```bash
# 需要额外工具
pip install appimage-builder

# 创建 AppImage
appimage-builder --recipe AppImageBuilder.yml
```

**优点**:
- 单个文件，双击运行
- 包含所有依赖
- 无需安装

**缺点**:
- 文件较大 (200MB+)
- 需要额外配置

#### 方案 3: 发行版原生包

##### Debian/Ubuntu/统信UOS/银河麒麟 (.deb)

创建 `DEBIAN/control`:
```
Package: fhbinningtool
Version: 1.0.0
Section: utils
Priority: optional
Architecture: amd64
Depends: libgl1-mesa-glx, libglib2.0-0, libx11-6, libxext6
Description: Risk Control Binning Tool
```

构建:
```bash
dpkg-deb --build fhbinningtool_1.0.0_amd64
```

用户安装:
```bash
sudo dpkg -i fhbinningtool_1.0.0_amd64.deb
# 或
sudo apt install ./fhbinningtool_1.0.0_amd64.deb
```

##### RPM 包 (RHEL/CentOS/Rocky)

类似流程，使用 `rpmbuild` 工具。

---

### macOS 推荐方案

#### 方案 1: .app 包（推荐）

```bash
bash scripts/build_mac.sh
```

输出: `FHBinningTool.app`

#### 方案 2: DMG 安装包

```bash
# 使用 create-dmg
brew install create-dmg
bash scripts/build_mac.sh  # 会自动创建 DMG
```

#### 方案 3: Homebrew Cask

创建 `fhbinningtool.rb`:
```ruby
cask "fhbinningtool" do
  version "1.0.0"
  sha256 "..."
  
  url "https://example.com/FHBinningTool-#{version}.dmg"
  name "FHBinningTool"
  
  app "FHBinningTool.app"
end
```

---

## 依赖检查清单

在发布前，请确认：

### Windows
- [ ] 在干净的 Windows 10/11 虚拟机测试
- [ ] 确认 VC++ Redist 是否需要
- [ ] 测试中文路径支持
- [ ] 测试带空格的路径

### Linux
- [ ] 在目标发行版测试（统信UOS、麒麟V10）
- [ ] 运行 `./check_deps.sh` 确认依赖
- [ ] 测试 Wayland 和 X11 兼容性
- [ ] 测试不同桌面环境（GNOME、KDE、UKUI）

### macOS
- [ ] 在 Intel Mac 测试
- [ ] 在 Apple Silicon Mac 测试
- [ ] 签名和公证（如需分发）

---

## 快速构建命令

```bash
# Windows - 推荐
git clone <repo>
cd FHBinningTool
scripts\build_windows_static.bat

# Linux - 推荐
git clone <repo>
cd FHBinningTool
bash scripts/build_linux_static.sh

# macOS - 推荐
git clone <repo>
cd FHBinningTool
bash scripts/build_mac.sh
```

---

## 总结

| 平台 | 推荐方案 | 用户需要安装 | 难度 |
|------|---------|-------------|------|
| Windows | 目录版 + VC++ Redist | 可能需要 VC++ Redist | ⭐⭐ |
| Linux | 目录版 + 依赖检查 | 需要系统图形库 | ⭐⭐⭐ |
| macOS | .app / DMG | 无需额外安装 | ⭐ |

对于企业内网部署，建议：
1. Windows: 使用域控推送 VC++ Redist，然后分发绿色版
2. Linux: 创建 .deb/.rpm 包，使用内部源安装
3. macOS: 使用 MDM 分发 .app 包
