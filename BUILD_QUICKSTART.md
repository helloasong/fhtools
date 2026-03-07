# FHBinningTool 快速构建指南

## 🚀 快速开始

### Windows

```batch
git clone <repo-url>
cd FHBinningTool
scripts\build_windows.bat
```

输出：`dist\FHBinningTool\FHBinningTool.exe`

---

### macOS

```bash
git clone <repo-url>
cd FHBinningTool
bash scripts/build_mac.sh
```

输出：`dist/FHBinningTool.app`

---

### Linux（统信 UOS / 麒麟 V10）

```bash
git clone <repo-url>
cd FHBinningTool

# 自动安装依赖并构建
INSTALL_DEPS=1 bash scripts/build_linux.sh

# 或仅构建
bash scripts/build_linux.sh
```

输出：`dist/FHBinningTool/FHBinningTool`

---

## 📁 项目目录对比

| 平台 | 开发目录 | 打包后数据目录 |
|------|---------|---------------|
| Windows | `.\projects` | `%USERPROFILE%\FHBinningTool\projects` |
| macOS | `./projects` | `~/FHBinningTool/projects` |
| Linux | `./projects` | `~/.local/share/FHBinningTool/projects` |

自定义数据目录：
```bash
export FHBINNINGTOOL_PROJECT_ROOT=/your/custom/path
```

---

## 🔧 手动构建

### 1. 创建环境

```bash
python3 -m venv venv

# Windows
venv\Scripts\activate.bat

# macOS/Linux
source venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
pip install pyinstaller
```

### 3. 构建

```bash
# Windows
pyinstaller FHBinningTool_windows.spec

# macOS
pyinstaller FHBinningTool.spec

# Linux
pyinstaller FHBinningTool_linux.spec
```

---

## ⚠️ 常见问题速查

| 问题 | 解决方案 |
|------|---------|
| 找不到 PyQt6 | `pip install PyQt6` |
| Windows 缺少 DLL | 安装 [VC++ Redist](https://aka.ms/vs/17/release/vc_redist.x64.exe) |
| Linux Qt 插件错误 | `sudo apt install libqt6gui6` |
| 模块未找到 | 添加到 spec 文件的 `hiddenimports` |

---

## 📦 分发文件

构建完成后，将整个 `dist/FHBinningTool` 目录打包分发：

```bash
# Windows: 压缩为 zip
# macOS:
ditto -c -k --keepParent dist/FHBinningTool.app dist/FHBinningTool-macOS.zip

# Linux:
tar -czvf dist/FHBinningTool-linux.tar.gz -C dist FHBinningTool
```
