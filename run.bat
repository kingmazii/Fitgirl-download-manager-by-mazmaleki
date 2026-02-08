@echo off
title Fitgirl Downloader by MazMaleki
cd /d "%~dp0"

echo.
echo ========================================
echo   Fitgirl Downloader by MazMaleki
echo ========================================
echo.
echo Starting application...
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

REM Check if fitgirl.py exists in current directory
if not exist "fitgirl.py" (
    echo Error: fitgirl.py not found in current directory!
    echo Please make sure all files are in the same folder.
    echo.
    pause
    exit /b 1
)

REM Check and install required libraries
echo Checking dependencies...
python -c "import requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing requests library...
    pip install requests
)

python -c "import bs4" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing beautifulsoup4 library...
    pip install beautifulsoup4
)

python -c "import psutil" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing psutil library...
    pip install psutil
)

python -c "import PIL" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing Pillow library...
    pip install Pillow
)

REM Run the application
echo.
echo Starting Fitgirl Downloader...
echo.
python fitgirl.py

REM If application crashes, keep window open for debugging
if %errorlevel% neq 0 (
    echo.
    echo Application closed with error code: %errorlevel%
    echo.
    pause
)
