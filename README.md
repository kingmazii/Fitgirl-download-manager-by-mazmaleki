# Fitgirl Downloader by MazMaleki

A comprehensive download manager for Fitgirl repacks with smart extraction, auto-resume, and notification features.

## 🚀 Quick Start

### Option 1: Run Directly (Recommended)
1. Clone or download all files to a folder
2. Double-click `run.bat` - automatically checks dependencies and starts app

### Option 2: Manual Setup
1. Install Python 3.10+ from [python.org](https://python.org)
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python fitgirl.py
   ```

## ✨ Features

- **Smart Download Manager**: Organizes downloads by game groups with auto-extraction
- **Multi-threaded Downloads**: Fast parallel downloading with pause/resume capability
- **Auto-Resume**: Automatically resumes interrupted downloads
- **Smart Folder Management**: Groups archives by game and tracks extraction status
- **Built-in Extractor**: Integrated RAR/ZIP extraction with password support
- **GitHub Notifications**: Real-time update notifications from GitHub repository
- **Multi-tab Help System**: Comprehensive help documentation
- **Compact Donation UI**: Clean interface with Patreon integration and QR codes

## 📁 Project Structure

- `fitgirl.py` - Main application entry point
- `config_manager.py` - Configuration and data management
- `donate_window.py` - Donation interface with QR codes
- `extractor_tab.py` - Built-in extraction interface
- `extractor_utils.py` - Extraction utilities
- `download_auto_resume.py` - Auto-resume functionality
- `github_notifications_simple.py` - GitHub notification system
- `smart_folder_manager.py` - Smart folder and archive management
- `run.bat` - Quick launcher with dependency check
- `uninstall.bat` - Library removal tool
- `requirements.txt` - Python dependencies
- `README.md` - This file

## ⚙️ Configuration

The application creates `config.json` for storing:
- Download history
- Archive groups
- Settings and preferences

## 🎮 Usage

1. **Download Tab**: Browse and download Fitgirl repacks
2. **Smart Manager Tab**: View and manage downloaded archives, extract games
3. **Extractor Tab**: Manual extraction with password support
4. **Help Tab**: Access comprehensive documentation

## 💖 Support

Consider supporting the project:
- **Patreon**: https://www.patreon.com/mazmaleki
- **Crypto**: Scan QR codes in the donation window

## 📋 Requirements

- Python 3.10 or higher
- Windows 10/11
- Internet connection

## 📄 Dependencies

- `requests>=2.28.0` - HTTP requests
- `beautifulsoup4>=4.11.0` - HTML parsing
- `psutil>=5.9.0` - System monitoring
- `Pillow>=9.0.0` - Image processing

## 📜 License

This project is for personal use only. Please respect the original content creators.

---

## 🚀 Release Notes

**This is the most stable version based on my own testing.**

If you encounter any bugs or issues, please report them via the email address listed in the app's Help section.

### 🔧 Easy Installation with Batch Files

**For your convenience, I've included batch files:**

- **`run.bat`** - Automatically installs dependencies and starts the application
  - Checks if Python is installed
  - Installs missing libraries (requests, beautifulsoup4, psutil, Pillow)
  - Validates all files are present
  - Starts the application with error handling

- **`uninstall.bat`** - Safely removes all libraries when done
  - Shows which libraries will be removed
  - Asks for confirmation before proceeding
  - Preserves Python installation (only removes libraries)
  - Provides clear feedback for each operation

### 🛡️ Antivirus Note

Some antivirus programs may flag this tool as suspicious due to its internet access and ability to read/write files on your hard drive. This is a very common false positive for open-source download utilities — the program is clean and fully open source.

To avoid interruptions, I recommend:
• Temporarily disabling your antivirus while using the tool, or
• Adding an exception for the executable in both your antivirus and Windows Defender Firewall.

### 🔧 If the .exe gets blocked or deleted by your antivirus:

You can run the tool without the executable:
1. Download all the Python files from the repository
2. Install Python (if you don't have it already) — https://www.python.org/downloads/
3. Double-click `run.bat` to install dependencies and start

Enjoy! If you find the tool helpful, please consider supporting the project — every bit of support helps keep it updated and improved.

## 🔄 Changelog

### Latest Version
- **Compact donation window** with zero spacing
- **Patreon integration** with clickable links
- **Character encoding fixes** for archive names
- **Enhanced delete confirmation** dialogs
- **Multi-tab help system** with comprehensive documentation
- **Password field** in extractor
- **GitHub notification system**
- **Auto-extraction fixes** for JSON-only mode
- **Easy batch launcher** (`run.bat` for one-click execution)
- **Library management** (`uninstall.bat` for clean removal)

---

**Made with ❤️ by MazMaleki**
