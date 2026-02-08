# Smart Download Manager by MazMaleki (fitgirl repack batch downloader) 

A comprehensive download manager for every internet download links and Fitgirl repacks with smart extraction, auto-resume, and notification features.

## Features

- **Smart Download Manager**: Organizes downloads by game groups with auto-extraction
- **Multi-threaded Downloads**: Fast parallel downloading with pause/resume capability
- **Auto-Resume**: Automatically resumes interrupted downloads
- **Smart Folder Management**: Groups archives by game and tracks extraction status
- **Built-in Extractor**: Integrated RAR/ZIP extraction with password support
- **GitHub Notifications**: Real-time update notifications from GitHub repository
- **Multi-tab Help System**: Comprehensive help documentation
- **Donation Support**: Integrated donation options with QR codes and Patreon link

## Requirements

- Python 3.10 or higher
- Required packages listed in `requirements.txt`

## Installation

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python fitgirl.py
   ```

## Usage

1. **Download Tab**: Browse and download Fitgirl repacks
2. **Smart Manager Tab**: View and manage downloaded archives, extract games
3. **Extractor Tab**: Manual extraction with password support
4. **Help Tab**: Access comprehensive documentation

## Project Structure

- `fitgirl.py` - Main application entry point
- `config_manager.py` - Configuration and data management
- `donate_window.py` - Donation interface with QR codes
- `extractor_tab.py` - Built-in extraction interface
- `extractor_utils.py` - Extraction utilities
- `download_auto_resume.py` - Auto-resume functionality
- `github_notifications_simple.py` - GitHub notification system
- `smart_folder_manager.py` - Smart folder and archive management

## Configuration

The application creates `config.json` for storing:
- Download history
- Archive groups
- Settings and preferences

## Support

Consider supporting the project:
- **Patreon**: https://www.patreon.com/mazmaleki
- **Crypto**: Scan QR codes in the donation window

## License

This project is for personal use only. Please respect the original content creators.

## Changelog

### Latest Version
- Compact donation window design
- Patreon integration with clickable links
- Improved character encoding for archive names
- Enhanced delete confirmation dialogs
- Multi-tab help system
- Password field in extractor
- GitHub notification system
- Auto-extraction fixes for JSON-only mode
