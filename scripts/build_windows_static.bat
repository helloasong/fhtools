@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==========================================
echo FHBinningTool Windows Static Build
echo (包含所有依赖，无需用户安装运行库)
echo ==========================================

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\.."
set "ROOT_DIR=%CD%"

echo Project root: %ROOT_DIR%

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    exit /b 1
)

:: Create virtual environment
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

:: Upgrade pip and install build tools
echo Installing build dependencies...
python -m pip install --upgrade pip setuptools wheel

:: Install PyInstaller and static analysis tools
pip install pyinstaller staticx 2>nul || echo staticx not available on Windows

:: Install all requirements
echo Installing project dependencies...
pip install -r requirements.txt

:: Install additional dependencies for static linking
echo Installing static linking dependencies...

:: Try to install PyQt6 with all binaries
pip install --force-reinstall --no-binary :all: PyQt6 2>nul || echo Using pre-built PyQt6 wheels

:: Install VC++ runtime redistributable (will be bundled)
echo Setting up VC++ runtime...
if not exist "dist\vc_redist" mkdir "dist\vc_redist"

:: Download VC++ Redist if not present (optional, for manual distribution)
if not exist "dist\vc_redist\vc_redist.x64.exe" (
    echo Note: Consider bundling VC++ Redistributable for older Windows versions
    echo Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe
)

:: Set icon
set "ICON_PATH=assets\AppIcon.ico"
set "EXTRA_ICON_ARGS="
if exist "%ICON_PATH%" (
    set "EXTRA_ICON_ARGS=--icon %ICON_PATH%"
)

:: Clean previous builds
echo Cleaning previous builds...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

:: Build with PyInstaller - One Directory Mode (Recommended)
echo Building Windows executable (Directory mode - recommended)...
pyinstaller ^
    --windowed ^
    --noconfirm ^
    --name FHBinningTool ^
    --add-data "config.json;." ^
    --add-data "style.qss;." ^
    --add-binary "%SystemRoot%\System32\msvcp140.dll;." 2>nul ^
    --add-binary "%SystemRoot%\System32\vcruntime140.dll;." 2>nul ^
    --add-binary "%SystemRoot%\System32\vcruntime140_1.dll;." 2>nul ^
    --hidden-import PyQt6.sip ^
    --hidden-import PyQt6.QtCore ^
    --hidden-import PyQt6.QtGui ^
    --hidden-import PyQt6.QtWidgets ^
    --hidden-import sklearn.tree._utils ^
    --hidden-import sklearn.utils._typedefs ^
    --hidden-import sklearn.utils._heap ^
    --hidden-import sklearn.utils._sorting ^
    --hidden-import sklearn.utils._vector_sentinel ^
    --hidden-import scipy.special.cython_special ^
    --hidden-import scipy.special._ufuncs_cxx ^
    --hidden-import pandas._libs.tslibs.base ^
    --hidden-import pandas._libs.tslibs.np_datetime ^
    --hidden-import pandas._libs.tslibs.nattype ^
    --hidden-import openpyxl ^
    --hidden-import openpyxl.cell._writer ^
    --hidden-import qt_material ^
    --hidden-import pyqtgraph ^
    --collect-all PyQt6 ^
    --collect-all qt_material ^
    --collect-all pyqtgraph ^
    %EXTRA_ICON_ARGS% ^
    src\ui\main_window.py

if errorlevel 1 (
    echo [ERROR] Build failed!
    exit /b 1
)

:: Copy additional Qt plugins if needed
echo Copying Qt plugins...
if exist "venv\Lib\site-packages\PyQt6\Qt6\plugins" (
    xcopy /s /i /y "venv\Lib\site-packages\PyQt6\Qt6\plugins\*" "dist\FHBinningTool\PyQt6\Qt6\plugins\" 2>nul || echo Plugins already included
)

:: Create launcher script for troubleshooting
echo Creating launcher scripts...
(
echo @echo off
chcp 65001 >nul
echo FHBinningTool Launcher
echo ======================
echo.
echo If the application fails to start, you may need to install VC++ Redistributable:
echo https://aka.ms/vs/17/release/vc_redist.x64.exe
echo.
pause
start FHBinningTool.exe
) > "dist\FHBinningTool\启动程序.bat"

:: Create README for end users
echo Creating user README...
(
echo # FHBinningTool 风控数据分箱工具
echo.
echo ## 系统要求
echo - Windows 10 (版本 1903+) 或 Windows 11
echo - 4GB RAM 推荐
echo - 500MB 可用磁盘空间
echo.
echo ## 启动方式
echo 1. 双击 FHBinningTool.exe 启动程序
echo 2. 如果遇到启动问题，先运行"启动程序.bat"
echo.
echo ## 常见问题
echo.
echo ### 程序无法启动，提示缺少 DLL
echo 请安装 Visual C++ Redistributable：
echo https://aka.ms/vs/17/release/vc_redist.x64.exe
echo.
echo ### 数据存储位置
echo 项目数据默认保存在：%%USERPROFILE%%\FHBinningTool\projects
echo.
echo ## 技术支持
echo 如有问题，请联系技术支持团队。
) > "dist\FHBinningTool\README.txt"

echo.
echo ==========================================
echo Build completed successfully!
echo Output: %ROOT_DIR%\dist\FHBinningTool
echo ==========================================
echo.
echo [注意事项]
echo 1. 此构建已包含大部分 Python 依赖
echo 2. 极少数 Windows 系统可能需要安装 VC++ Redistributable
echo 3. 已生成 README.txt 供最终用户参考
echo.

pause
endlocal
