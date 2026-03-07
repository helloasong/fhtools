# FHBinningTool 打包方案汇总

## 📦 依赖处理现状

### ✅ 已自动打包（用户无需安装）
- Python 3.9+ 解释器
- PyQt6 及所有 Python 库
- pandas, numpy, sklearn 等数据科学库

### ⚠️ 需要目标系统提供
- **Windows**: VC++ Redistributable 2015-2022（部分系统已预装）
- **Linux**: OpenGL, X11, GLib 等基础图形库
- **macOS**: 系统自带，无需额外安装

---

## 🚀 推荐打包方案

### Windows

```batch
:: 使用增强版构建脚本（自动包含 VC++ 提示）
scripts\build_windows_static.bat
```

**输出**: `dist/FHBinningTool/` 目录

**分发建议**:
- 小范围测试：直接压缩整个目录
- 正式分发：打包为安装程序（Inno Setup）

**用户系统要求**:
- Windows 10 (1903+) 或 Windows 11
- 绝大多数系统已预装 VC++ Runtime
- 极少数老旧系统需要手动安装

---

### Linux（统信 UOS / 银河麒麟 V10）

```bash
# 使用静态构建脚本
bash scripts/build_linux_static.sh
```

**输出**: `dist/FHBinningTool/` 目录，包含：
- `FHBinningTool` - 主程序
- `run.sh` - 启动脚本
- `check_deps.sh` - 依赖检查
- `install.sh` - 安装脚本

**分发建议**:
```bash
# 打包为 tar.gz
tar -czvf FHBinningTool-linux.tar.gz -C dist FHBinningTool

# 用户安装步骤
tar -xzvf FHBinningTool-linux.tar.gz
cd FHBinningTool
./check_deps.sh    # 检查依赖
./install.sh       # 安装
```

**用户系统要求**:
- 安装基础图形库：
```bash
# 统信UOS / 银河麒麟 / Ubuntu / Debian
sudo apt-get install libgl1-mesa-glx libglib2.0-0 libsm6 libxext6

# RHEL / CentOS / Rocky
sudo yum install mesa-libGL glib2 libSM libXext
```

---

### macOS

```bash
bash scripts/build_mac.sh
```

**输出**: `dist/FHBinningTool.app`

**分发建议**:
- 开发测试：直接分发 .app
- 正式分发：打包为 DMG

**用户系统要求**:
- macOS 11+
- 无需额外安装

---

## 📊 方案对比

| 方案 | 文件大小 | 用户友好度 | 依赖处理 | 适用场景 |
|------|---------|-----------|---------|---------|
| **Windows 目录版** | ~150MB | ⭐⭐⭐ | 可能需要 VC++ | 推荐 |
| **Windows 单文件版** | ~150MB | ⭐⭐⭐⭐ | 可能需要 VC++ | 简单分发 |
| **Linux 目录版** | ~180MB | ⭐⭐⭐ | 需要图形库 | 推荐 |
| **Linux AppImage** | ~200MB | ⭐⭐⭐⭐⭐ | 包含所有 | 最佳体验 |
| **macOS .app** | ~160MB | ⭐⭐⭐⭐⭐ | 无需额外 | 推荐 |

---

## 🔧 进阶：创建专业安装包

### Windows - Inno Setup

创建 `setup.iss`:
```pascal
[Setup]
AppName=FHBinningTool
AppVersion=1.0
DefaultDirName={autopf}\FHBinningTool
OutputDir=dist

[Files]
Source: "dist\FHBinningTool\*"; DestDir: "{app}"; Flags: recursesubdirs
Source: "vc_redist.x64.exe"; DestDir: "{tmp}"

[Run]
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; Check: NeedsVCRedist
Filename: "{app}\FHBinningTool.exe"; Description: "启动程序"
```

编译：
```batch
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" setup.iss
```

### Linux - .deb 包

创建打包脚本 `build_deb.sh`:
```bash
#!/bin/bash
VERSION="1.0.0"
ARCH="amd64"
PKGDIR="fhbinningtool_${VERSION}_${ARCH}"

mkdir -p "$PKGDIR/DEBIAN"
mkdir -p "$PKGDIR/opt/fhbinningtool"
mkdir -p "$PKGDIR/usr/share/applications"
mkdir -p "$PKGDIR/usr/bin"

# 控制文件
cat > "$PKGDIR/DEBIAN/control" << EOF
Package: fhbinningtool
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Depends: libgl1-mesa-glx, libglib2.0-0, libx11-6, libxext6
Description: Risk Control Binning Tool
 Risk control data analysis and scorecard development tool.
EOF

# 复制程序文件
cp -r dist/FHBinningTool/* "$PKGDIR/opt/fhbinningtool/"

# 创建启动器
ln -s /opt/fhbinningtool/run.sh "$PKGDIR/usr/bin/fhbinningtool"

# 桌面文件
cat > "$PKGDIR/usr/share/applications/fhbinningtool.desktop" << EOF
[Desktop Entry]
Name=FHBinningTool
Exec=/opt/fhbinningtool/run.sh
Icon=/opt/fhbinningtool/FHBinningTool
Type=Application
Categories=Office;Finance;
EOF

# 构建
dpkg-deb --build "$PKGDIR"
```

---

## 📋 企业部署建议

### 场景 1：内网环境（Windows）

1. **准备工作站**: 安装 VC++ Redist 到黄金镜像
2. **分发绿色版**: 使用目录版，通过共享文件夹/内网盘分发
3. **桌面快捷方式**: 使用组策略推送

### 场景 2：内网环境（Linux - 统信UOS/麒麟）

1. **创建私有源**: 搭建 Apt 或 Yum 源
2. **打包为 deb/rpm**: 创建系统原生包
3. **依赖预装**: 将图形库依赖预装在黄金镜像中

```bash
# 使用内部 apt 源
sudo apt-get update
sudo apt-get install fhbinningtool
```

### 场景 3：外网分发

- **Windows**: 提供安装程序 + VC++ Redist 下载链接
- **Linux**: 提供 AppImage 或 Flatpak 包
- **macOS**: 提供签名后的 DMG

---

## ✅ 发布前检查清单

### 功能测试
- [ ] 数据导入（CSV/Excel）
- [ ] 分箱计算
- [ ] 图表显示
- [ ] Excel 导出
- [ ] 项目保存/加载

### 兼容性测试
- [ ] 中文路径支持
- [ ] 带空格的路径
- [ ] 不同分辨率屏幕
- [ ] 高 DPI 显示

### 平台特定测试

**Windows**:
- [ ] 干净的 Win10 虚拟机测试
- [ ] 检查 VC++ 依赖提示

**Linux**:
- [ ] 在目标发行版测试（统信UOS/麒麟）
- [ ] 运行依赖检查脚本
- [ ] 测试 Wayland/X11

**macOS**:
- [ ] Intel Mac 测试
- [ ] Apple Silicon Mac 测试

---

## 📞 获取帮助

如果遇到打包问题：
1. 查看详细指南：`BUILD_GUIDE.md`
2. 查看依赖说明：`DEPENDENCY_GUIDE.md`
3. 检查构建日志中的错误信息

---

## 📝 总结

**一句话建议**:
- **Windows**: 用 `build_windows_static.bat`，分发目录 + VC++ Redist
- **Linux**: 用 `build_linux_static.sh`，用户先装图形库
- **macOS**: 用 `build_mac.sh`，直接分发 .app

Python 依赖已全部打包，用户只需要处理系统级依赖即可！
