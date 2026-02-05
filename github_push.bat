@echo off
title GitHub Push - FitGirl Downloader
color 0A

echo ========================================
echo    GitHub Push - FitGirl Downloader
echo ========================================
echo.

REM Configuration - FILL THESE IN:
set GITHUB_USERNAME=yourusername
set REPO_NAME=fitgirl-downloader
set GITHUB_TOKEN=ghp_your_github_token_here
set PROJECT_DIR=D:\Games\FitGirl Downloader\Fitgirl Downloader\backup_final
set EXE_FILE=D:\Games\FitGirl Downloader\Fitgirl Downloader\backup_final\dist\FitGirl-Downloader-v1.0.0.exe

echo Checking configuration...
if "%GITHUB_USERNAME%"=="yourusername" (
    echo [ERROR] Please edit this file and set your GitHub username
    pause
    exit /b 1
)

if "%GITHUB_TOKEN%"=="ghp_your_github_token_here" (
    echo [ERROR] Please edit this file and set your GitHub token
    pause
    exit /b 1
)

echo Username: %GITHUB_USERNAME%
echo Repository: %REPO_NAME%
echo Project: %PROJECT_DIR%
echo.

echo [1/5] Initializing Git repository...
cd /d "%PROJECT_DIR%"
if not exist .git (
    echo Initializing new Git repository...
    git init
    git config user.name "Maz.Maleki"
    git config user.email "send2mazi@gmail.com"
) else (
    echo Git repository already exists
)

echo.
echo [2/5] Adding files to Git...
echo Adding source code...
git add *.py
git add *.md
git add *.txt
git add LICENSE
git add .gitignore

echo Adding EXE file...
git add "%EXE_FILE%"

echo.
echo [3/5] Creating commit...
git commit -m "Release v1.0.0 - Complete FitGirl Downloader with all features

Features:
- Multi-threaded downloads with progress tracking
- Smart Folder Manager with auto-scan enabled by default
- Delete archives after extraction with size verification
- JSON-only extraction mode with persistence
- Update notifications via GitHub API
- Complete extraction workflow
- Donation integration
- Professional UI with all requested features

Built with PyInstaller - Standalone executable ready for distribution"

echo.
echo [4/5] Connecting to GitHub...
git remote remove origin 2>nul
git remote add origin https://%GITHUB_USERNAME%:%GITHUB_TOKEN%@github.com/%GITHUB_USERNAME%/%REPO_NAME%.git

echo.
echo [5/5] Pushing to GitHub...
git branch -M main
git push -u origin main --force

echo.
if %ERRORLEVEL% EQU 0 (
    echo ========================================
    echo        SUCCESS! 
    echo    Code pushed to GitHub successfully!
    echo    Repository: https://github.com/%GITHUB_USERNAME%/%REPO_NAME%
    echo ========================================
    echo.
    echo Next steps:
    echo 1. Go to https://github.com/%GITHUB_USERNAME%/%REPO_NAME%/releases
    echo 2. Create a new release: v1.0.0
    echo 3. Upload the EXE file as release asset
    echo.
) else (
    echo ========================================
    echo        ERROR! 
    echo    Failed to push to GitHub
    echo    Check your credentials and try again
    echo ========================================
)

echo.
pause
