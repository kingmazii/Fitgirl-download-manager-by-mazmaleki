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

REM Check if requirements.txt exists
if exist "requirements.txt" (
    echo Checking dependencies...
    python -c "import requests, bs4, psutil, PIL" >nul 2>&1
    if %errorlevel% neq 0 (
        echo Installing required dependencies...
        pip install -r requirements.txt
        if %errorlevel% neq 0 (
            echo Error: Failed to install dependencies!
            echo Please run: pip install -r requirements.txt
            echo.
            pause
            exit /b 1
        )
    )
) else (
    echo Warning: requirements.txt not found. Assuming dependencies are already installed.
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
