# FHBinningTool 跨平台构建指南

本文档介绍如何在 Windows、macOS 和 Linux（统信 UOS / 银河麒麟 V10）平台上构建 FHBinningTool。

## 目录

- [环境要求](#环境要求)
- [Windows 构建](#windows-构建)
- [macOS 构建](#macos-构建)
- [Linux 构建（统信 UOS / 麒麟 V10）](#linux-构建统信-uos--麒麟-v10)
- [常见问题](#常见问题)

---

## 环境要求

### 所有平台通用要求

- **Python**: 3.9 或更高版本
- **内存**: 建议 4GB+
- **磁盘空间**: 建议 2GB+ 可用空间

### 平台特定要求

| 平台 | 额外要求 |
|------|---------|
| Windows | Visual C++ Redistributable (通常已安装) |
| macOS | Xcode Command Line Tools (可选) |
| Linux | 详见 [Linux 系统依赖](#linux-系统依赖) |

---

## Windows 构建

### 支持版本

- Windows 11 (推荐)
- Windows 10 (版本 1903+)

### 构建步骤

#### 方法一：使用批处理脚本（推荐）

```batch
# 打开命令提示符或 PowerShell，进入项目目录
cd FHBinningTool

# 运行构建脚本
scripts\build_windows.bat
```

#### 方法二：使用 PyInstaller 直接构建

```batch
# 1. 创建虚拟环境
python -m venv venv
venv\Scripts\activate.bat

# 2. 安装依赖
pip install -r requirements.txt
pip install pyinstaller

# 3. 构建
pyinstaller FHBinningTool_windows.spec
```

#### 方法三：单文件版本

```batch
# 构建单个可执行文件（启动较慢，但分发更方便）
pyinstaller FHBinningTool_windows_onefile.spec
```

### 输出位置

```
dist/
├── FHBinningTool/              # 目录版本（推荐）
│   ├── FHBinningTool.exe
│   ├── config.json
│   ├── style.qss
│   └── ...
└── package/                    # 可分发包
```

### Windows 特定配置

- **项目数据目录**: `%USERPROFILE%\FHBinningTool\projects`
- **环境变量**: 可设置 `FHBINNINGTOOL_PROJECT_ROOT` 自定义项目目录

---

## macOS 构建

### 支持版本

- macOS 11 (Big Sur) 及以上
- 支持 Intel 和 Apple Silicon (M1/M2/M3)

### 构建步骤

#### 方法一：使用 shell 脚本（推荐）

```bash
cd FHBinningTool
bash scripts/build_mac.sh
```

#### 方法二：手动构建

```bash
# 1. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt
pip install pyinstaller

# 3. 构建
pyinstaller FHBinningTool.spec
```

### 输出位置

```
dist/
├── FHBinningTool.app/          # macOS 应用包
└── FHBinningTool/              # 命令行版本
```

### macOS 特定配置

- **项目数据目录**: `~/FHBinningTool/projects`
- **Bundle ID**: `com.fhtools.fhbinningtool`（可在构建脚本中自定义）

---

## Linux 构建（统信 UOS / 麒麟 V10）

### 支持版本

- 统信 UOS 20+ (Desktop/Server)
- 银河麒麟 V10 (x86_64, arm64)
- Ubuntu 20.04+ / Debian 10+
- CentOS 7+ / RHEL 7+ / Rocky Linux 8+

### 系统依赖

#### Debian/Ubuntu / 统信 UOS / 麒麟 V10

```bash
# 安装系统依赖
sudo apt-get update
sudo apt-get install -y \
    python3-dev \
    python3-pip \
    python3-venv \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1

# Qt6 依赖（如果使用系统 Qt）
sudo apt-get install -y \
    libqt6gui6 \
    libqt6network6 \
    libqt6widgets6 \
    libqt6core6
```

#### RHEL/CentOS/Rocky

```bash
sudo yum install -y \
    python3-devel \
    mesa-libGL \
    glib2 \
    libSM \
    libXext \
    libXrender \
    libgomp
```

### 构建步骤

#### 方法一：使用 shell 脚本（推荐，自动安装依赖）

```bash
cd FHBinningTool

# 自动安装系统依赖并构建
INSTALL_DEPS=1 bash scripts/build_linux.sh

# 或仅构建（假设依赖已安装）
bash scripts/build_linux.sh
```

#### 方法二：手动构建

```bash
# 1. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt
pip install pyinstaller

# 3. 构建
pyinstaller FHBinningTool_linux.spec
```

### 输出位置

```
dist/
├── FHBinningTool/              # 可执行目录
│   ├── FHBinningTool           # 主程序
│   ├── config.json
│   ├── style.qss
│   └── FHBinningTool.desktop   # 桌面快捷方式
└── package/                    # 可分发包
    ├── install.sh              # 安装脚本
    └── ...
```

### 安装到系统

```bash
# 运行安装脚本
cd dist/package
bash install.sh

# 或手动安装
mkdir -p ~/.local/opt/FHBinningTool
cp -r dist/FHBinningTool/* ~/.local/opt/FHBinningTool/
ln -sf ~/.local/opt/FHBinningTool/FHBinningTool ~/.local/bin/fhbinningtool
```

### Linux 特定配置

- **项目数据目录**: `~/.local/share/FHBinningTool/projects`（遵循 XDG 规范）
- **环境变量**: 可设置 `FHBINNINGTOOL_PROJECT_ROOT` 自定义项目目录

---

## 常见问题

### Q1: PyInstaller 打包后找不到模块

**解决方法**：在 spec 文件的 `hiddenimports` 中添加缺失的模块：

```python
hiddenimports=[
    'PyQt6.sip',
    'sklearn.tree._utils',
    'scipy.special.cython_special',
    # ... 其他模块
]
```

### Q2: Windows 上运行时提示缺少 DLL

**解决方法**：安装 Visual C++ Redistributable：
- 下载地址：https://aka.ms/vs/17/release/vc_redist.x64.exe

### Q3: Linux 上 Qt 平台插件错误

**错误信息**：`qt.qpa.plugin: Could not load the Qt platform plugin`

**解决方法**：
```bash
# 设置 Qt 平台插件路径
export QT_QPA_PLATFORM_PLUGIN_PATH=/path/to/plugins

# 或使用 xcb 平台
export QT_QPA_PLATFORM=xcb
```

### Q4: 打包后的程序找不到配置文件

**检查事项**：
1. 确认 `config.json` 已正确添加到 PyInstaller 的 `datas`
2. 使用 `get_base_dir()` 函数获取正确的路径
3. 检查文件编码是否为 UTF-8

### Q5: 统信 UOS / 麒麟 V10 上的兼容性问题

**解决方法**：
1. 使用系统自带的 Python3（避免版本冲突）
2. 确保安装了所有 Qt6 依赖
3. 如果 Qt6 不可用，考虑使用 Qt5 版本（需要修改代码）

```bash
# 检查 Qt 版本
python3 -c "from PyQt6.QtCore import QT_VERSION_STR; print(QT_VERSION_STR)"
```

### Q6: 如何自定义项目存储位置

**方法 1**：环境变量
```bash
# Linux/macOS
export FHBINNINGTOOL_PROJECT_ROOT=/path/to/projects

# Windows
set FHBINNINGTOOL_PROJECT_ROOT=C:\path\to\projects
```

**方法 2**：修改代码（开发环境）
```python
# 在创建 ProjectRepository 时指定路径
repository = ProjectRepository(project_root="/custom/path")
```

---

## 构建配置说明

### Spec 文件对比

| 文件 | 用途 | 适用场景 |
|------|------|---------|
| `FHBinningTool.spec` | macOS 专用 | macOS 应用打包 |
| `FHBinningTool_windows.spec` | Windows 目录版 | 常规分发 |
| `FHBinningTool_windows_onefile.spec` | Windows 单文件版 | 简单分发 |
| `FHBinningTool_linux.spec` | Linux 通用 | 所有 Linux 发行版 |

### 路径处理最佳实践

项目已统一使用 `pathlib` 和 `os.path.join` 处理路径，确保跨平台兼容：

```python
from pathlib import Path

# 获取项目根目录（支持开发环境和打包环境）
def get_base_dir() -> str:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return str(Path(__file__).resolve().parent.parent.parent)

# 构建路径
config_path = Path(base_dir) / "config.json"
```

---

## 故障排查

如果构建失败，请检查：

1. **Python 版本**: `python --version` >= 3.9
2. **虚拟环境**: 确保在激活的虚拟环境中运行
3. **依赖完整性**: `pip install -r requirements.txt`
4. **磁盘空间**: 确保有足够空间（建议 2GB+）
5. **权限**: Linux/macOS 上确保脚本有执行权限

如需进一步帮助，请提供：
- 操作系统版本
- Python 版本
- 完整的错误日志
