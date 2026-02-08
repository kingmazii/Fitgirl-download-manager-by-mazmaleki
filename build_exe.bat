@echo off
title Build Fitgirl Downloader EXE
echo.
echo ========================================
echo   Build Fitgirl Downloader EXE
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH!
    echo Please install Python 3.10 or higher from https://python.org
    echo.
    pause
    exit /b 1
)

REM Check if PyInstaller is installed
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo Error: Failed to install PyInstaller!
        echo.
        pause
        exit /b 1
    )
)

REM Clean previous builds
echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del *.spec

REM Build EXE
echo.
echo Building executable...
echo This may take a few minutes...
echo.
python -m PyInstaller --onefile --windowed --name "Fitgirl Downloader" fitgirl.py

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo   Build Successful!
    echo ========================================
    echo.
    echo EXE location: dist\Fitgirl Downloader.exe
    echo Size: 
    dir "dist\Fitgirl Downloader.exe" | find "Fitgirl Downloader.exe"
    echo.
    echo You can now distribute the EXE file!
) else (
    echo.
    echo Error: Build failed!
    echo Please check the error messages above.
)

echo.
pause
