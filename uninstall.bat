@echo off
title Uninstall Fitgirl Downloader Libraries
cd /d "%~dp0"

echo.
echo ========================================
echo   Uninstall Fitgirl Downloader Libraries
echo ========================================
echo.
echo This tool will remove the following Python libraries:
echo   - requests
echo   - beautifulsoup4
echo   - psutil
echo   - Pillow
echo.
echo WARNING: This will NOT remove Python itself, only the libraries.
echo.

set /p confirm="Do you want to proceed? (y/N): "
if /i not "%confirm%"=="y" (
    echo.
    echo Operation cancelled by user.
    echo.
    pause
    exit /b 0
)

echo.
echo Removing libraries...
echo.

REM Remove requests library
echo Removing requests...
pip uninstall requests -y >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] requests removed successfully
) else (
    echo   [SKIP] requests not found or already removed
)

REM Remove beautifulsoup4 library
echo Removing beautifulsoup4...
pip uninstall beautifulsoup4 -y >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] beautifulsoup4 removed successfully
) else (
    echo   [SKIP] beautifulsoup4 not found or already removed
)

REM Remove psutil library
echo Removing psutil...
pip uninstall psutil -y >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] psutil removed successfully
) else (
    echo   [SKIP] psutil not found or already removed
)

REM Remove Pillow library
echo Removing Pillow...
pip uninstall Pillow -y >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] Pillow removed successfully
) else (
    echo   [SKIP] Pillow not found or already removed
)

echo.
echo ========================================
echo Uninstallation complete!
echo.
echo Python installation is preserved.
echo You can reinstall libraries anytime by running run.bat
echo.
pause
