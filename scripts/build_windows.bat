@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==========================================
echo FHBinningTool Windows Build Script
echo ==========================================

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%\.."
set "ROOT_DIR=%CD%"

echo Project root: %ROOT_DIR%

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.9+ and add to PATH.
    exit /b 1
)

:: Create virtual environment if not exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

:: Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

:: Install PyInstaller
echo Installing PyInstaller...
pip install pyinstaller

:: Install requirements
echo Installing dependencies...
if exist requirements.txt (
    pip install -r requirements.txt
)

:: Set icon path
set "ICON_PATH=assets\AppIcon.ico"
set "EXTRA_ICON_ARGS="
if exist "%ICON_PATH%" (
    set "EXTRA_ICON_ARGS=--icon %ICON_PATH%"
    echo Using icon: %ICON_PATH%
) else (
    echo No icon found, using default.
)

:: Clean previous builds
echo Cleaning previous builds...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

:: Build with PyInstaller
echo Building Windows executable...
pyinstaller ^
    --windowed ^
    --noconfirm ^
    --name FHBinningTool ^
    --add-data "config.json;." ^
    --add-data "style.qss;." ^
    --hidden-import PyQt6.sip ^
    --hidden-import sklearn.tree._utils ^
    --hidden-import scipy.special.cython_special ^
    %EXTRA_ICON_ARGS% ^
    src\ui\main_window.py

if errorlevel 1 (
    echo [ERROR] Build failed!
    exit /b 1
)

echo.
echo ==========================================
echo Build completed successfully!
echo Output: %ROOT_DIR%\dist\FHBinningTool
echo Executable: %ROOT_DIR%\dist\FHBinningTool\FHBinningTool.exe
echo ==========================================

:: Create distribution package
echo Creating distribution package...
if not exist "dist\package" mkdir "dist\package"
xcopy /s /i /y "dist\FHBinningTool\*" "dist\package\"

echo.
echo Package created at: %ROOT_DIR%\dist\package

pause
endlocal
