# GitHub Actions 自动打包教程

从零开始，使用 GitHub Actions 自动打包 FHBinningTool 的三个平台版本。

---

## 📋 目录

1. [注册 GitHub 账号](#1-注册-github-账号)
2. [创建代码仓库](#2-创建代码仓库)
3. [上传代码到 GitHub](#3-上传代码到-github)
4. [配置自动打包](#4-配置自动打包)
5. [触发构建](#5-触发构建)
6. [下载安装包](#6-下载安装包)
7. [常见问题](#7-常见问题)

---

## 1. 注册 GitHub 账号

### 步骤 1.1：访问官网
打开浏览器，访问 https://github.com

### 步骤 1.2：点击注册
点击页面右上角的 **Sign up** 按钮

### 步骤 1.3：填写信息
1. **Email**：输入你的邮箱
2. **Password**：设置密码（至少8位，包含大小写字母和数字）
3. **Username**：设置用户名（只能包含字母、数字、连字符）

### 步骤 1.4：验证
1. 完成人机验证（选择正确的图片）
2. 点击 **Create account**

### 步骤 1.5：邮箱验证
1. 登录你的邮箱
2. 找到 GitHub 发送的验证邮件
3. 点击邮件中的验证链接

✅ **完成！** 现在你已经有了 GitHub 账号。

---

## 2. 创建代码仓库

### 步骤 2.1：登录
访问 https://github.com 并登录

### 步骤 2.2：创建新仓库
点击页面左上角的绿色按钮 **New**（或右上角 + 号 → New repository）

### 步骤 2.3：配置仓库
填写以下信息：

| 字段 | 填写内容 |
|------|---------|
| **Repository name** | `FHBinningTool` |
| **Description** | `风控数据分箱工具 - Risk Control Binning Tool` |
| **Public / Private** | 选择 **Public**（免费无限 Actions） |
| **Initialize with README** | ✅ 勾选 |

### 步骤 2.4：创建
点击绿色按钮 **Create repository**

✅ **完成！** 现在你有了代码仓库。

---

## 3. 上传代码到 GitHub

### 方法 A：使用 Git 命令行（推荐）

#### 步骤 3.1：安装 Git
如果还没有安装 Git：

**macOS:**
```bash
# 如果安装了 Homebrew
brew install git

# 或下载安装包
# https://git-scm.com/download/mac
```

**Windows:**
下载安装包：https://git-scm.com/download/win

**Linux:**
```bash
sudo apt-get install git  # Debian/Ubuntu/统信UOS/麒麟
sudo yum install git      # RHEL/CentOS
```

#### 步骤 3.2：配置 Git
```bash
# 设置你的名字和邮箱（与 GitHub 一致）
git config --global user.name "你的用户名"
git config --global user.email "你的邮箱@example.com"
```

#### 步骤 3.3：初始化本地仓库
打开终端，进入你的项目目录：

```bash
cd /Users/songxianhe/Documents/trae_projects/fhtools

# 初始化 Git 仓库
git init

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit"
```

#### 步骤 3.4：关联远程仓库
在 GitHub 仓库页面，点击绿色按钮 **Code**，复制 HTTPS 链接，格式如：
```
https://github.com/你的用户名/FHBinningTool.git
```

然后执行：
```bash
# 关联远程仓库（替换成你的链接）
git remote add origin https://github.com/你的用户名/FHBinningTool.git

# 推送到 GitHub
git branch -M main
git push -u origin main
```

输入你的 GitHub 用户名和密码（或 Token）。

✅ **完成！** 代码已上传到 GitHub。

### 方法 B：使用 GitHub Desktop（图形界面）

如果你不习惯命令行：

1. 下载 GitHub Desktop：https://desktop.github.com
2. 登录你的 GitHub 账号
3. 选择 **File → Add local repository**
4. 选择你的项目文件夹 `/Users/songxianhe/Documents/trae_projects/fhtools`
5. 填写提交信息，点击 **Commit to main**
6. 点击 **Publish repository**

---

## 4. 配置自动打包

### 步骤 4.1：创建工作流文件

在你的项目目录创建文件夹：

```bash
mkdir -p .github/workflows
```

### 步骤 4.2：创建配置文件

创建文件 `.github/workflows/build.yml`：

```bash
touch .github/workflows/build.yml
```

用文本编辑器打开，粘贴以下内容：

```yaml
name: Build All Platforms

# 触发条件：代码推送到 main 分支时自动打包
on:
  push:
    branches: [main, master]
  # 也支持手动触发（点击按钮）
  workflow_dispatch:

jobs:
  # ========== macOS 打包 ==========
  build-macos:
    runs-on: macos-latest
    steps:
      # 检出代码
      - name: Checkout code
        uses: actions/checkout@v4

      # 设置 Python
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      # 安装依赖
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pyinstaller
          pip install -r requirements.txt

      # 执行打包
      - name: Build
        run: bash build_all.sh

      # 上传构建结果
      - name: Upload macOS build
        uses: actions/upload-artifact@v4
        with:
          name: FHBinningTool-macos
          path: release/*

  # ========== Windows 打包 ==========
  build-windows:
    runs-on: windows-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pyinstaller
          pip install -r requirements.txt

      - name: Build
        run: bash build_all.sh

      - name: Upload Windows build
        uses: actions/upload-artifact@v4
        with:
          name: FHBinningTool-windows
          path: release/*

  # ========== Linux 打包 ==========
  build-linux:
    runs-on: ubuntu-20.04
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      # Linux 需要安装系统依赖
      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y libgl1-mesa-glx libglib2.0-0 libx11-6 libxext6

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pyinstaller
          pip install -r requirements.txt

      - name: Build
        run: bash build_all.sh

      - name: Upload Linux build
        uses: actions/upload-artifact@v4
        with:
          name: FHBinningTool-linux
          path: release/*
```

### 步骤 4.3：提交配置文件

```bash
# 添加工作流文件
git add .github/workflows/build.yml

# 提交
git commit -m "Add GitHub Actions for auto build"

# 推送到 GitHub
git push origin main
```

✅ **完成！** 自动打包配置已完成。

---

## 5. 触发构建

### 方法 A：自动触发（推荐）

每当你推送代码到 main 分支时，GitHub Actions 会自动开始打包。

```bash
# 修改任意文件
echo "# Update" >> README.md
git add .
git commit -m "Update code"
git push origin main
```

推送后，自动触发构建。

### 方法 B：手动触发

1. 打开你的 GitHub 仓库页面
2. 点击顶部 **Actions** 标签
3. 左侧选择 **Build All Platforms**
4. 点击右侧 **Run workflow** 按钮
5. 选择分支（main），点击 **Run workflow**

---

## 6. 下载安装包

### 步骤 6.1：查看构建状态

1. 打开 GitHub 仓库页面
2. 点击顶部 **Actions** 标签
3. 你会看到正在运行的工作流：

```
Build All Platforms
├── build-macos     ● 运行中 (2m)
├── build-windows   ● 运行中 (3m)
└── build-linux     ● 运行中 (2m)
```

等待全部变为 ✅ **绿色对勾**（约 5-10 分钟）。

### 步骤 6.2：下载安装包

1. 点击完成的工作流进入详情页
2. 页面底部有 **Artifacts** 区域
3. 你会看到三个文件：
   - `FHBinningTool-macos`
   - `FHBinningTool-windows`
   - `FHBinningTool-linux`

4. 分别点击下载

### 步骤 6.3：解压使用

下载的文件是 zip 格式：

```bash
# macOS / Linux
unzip FHBinningTool-macos.zip
unzip FHBinningTool-linux.zip

# Windows
# 右键 → 解压全部
```

✅ **完成！** 你现在有了三个平台的安装包。

---

## 7. 常见问题

### Q1: 构建失败了怎么办？

点击失败的任务，查看日志：
1. 进入 Actions 页面
2. 点击失败的工作流
3. 点击失败的任务（如 build-windows）
4. 查看日志找出错误

常见错误：
- **依赖安装失败** → 检查 requirements.txt
- **打包脚本错误** → 检查 build_all.sh
- **系统库缺失** → 在 workflow 中添加 apt-get install

### Q2: 如何只打包某个平台？

编辑 `.github/workflows/build.yml`，删除不需要的 job。

例如只保留 Windows：
```yaml
jobs:
  build-windows:
    runs-on: windows-latest
    # ... 其他配置
```

### Q3: 构建太慢怎么办？

可以添加缓存：
```yaml
- name: Cache pip packages
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
```

### Q4: 如何给构建的包添加版本号？

使用 Git 标签：
```bash
git tag v1.0.0
git push origin v1.0.0
```

然后在 workflow 中读取：
```yaml
- name: Get version
  id: get_version
  run: echo "VERSION=${GITHUB_REF#refs/tags/}" >> $GITHUB_OUTPUT
```

### Q5: 可以发布到 Release 吗？

可以！添加以下步骤：
```yaml
- name: Create Release
  uses: softprops/action-gh-release@v1
  if: startsWith(github.ref, 'refs/tags/')
  with:
    files: release/*
```

推送标签后，会自动创建 Release 并上传文件。

---

## 📚 完整命令速查

```bash
# ===== 首次设置 =====
# 1. 注册 GitHub 账号 https://github.com

# 2. 创建仓库（网页操作）

# 3. 上传代码
cd /Users/songxianhe/Documents/trae_projects/fhtools
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/你的用户名/FHBinningTool.git
git push -u origin main

# 4. 创建工作流文件
mkdir -p .github/workflows
# 创建并编辑 .github/workflows/build.yml

git add .github/workflows/build.yml
git commit -m "Add GitHub Actions"
git push

# ===== 日常使用 =====
# 推送代码自动触发构建
git add .
git commit -m "Update"
git push

# 查看构建状态
# 访问 https://github.com/你的用户名/FHBinningTool/actions
```

---

## 🎉 恭喜

完成本教程后，你就拥有了一个**全自动的打包流水线**：
- 推送代码 → 自动触发
- 三台虚拟电脑同时打包
- 5-10 分钟后下载三个安装包

从此告别手动打包！
