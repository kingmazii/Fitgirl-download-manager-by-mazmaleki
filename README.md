# FitGirl Downloader

A comprehensive FitGirl repack downloader with smart extraction and management features.

## 🌟 Features

- 🔄 **Multi-threaded Downloads** - Fast parallel downloading
- 📁 **Smart Folder Manager** - Auto-scan and extract archives
- 🎯 **JSON-only Mode** - Extract only tracked archives
- 🗑️ **Delete After Extract** - Auto-cleanup after successful extraction
- 📋 **Session Management** - Track download progress
- 🧠 **Auto-extraction** - Automatic extraction when downloads complete
- 🔍 **Archive Preview** - View contents before extraction
- 💾 **Persistent Settings** - All preferences saved

## 📦 Requirements

- Python 3.8+
- WinRAR (for extraction)
- requests library
- tkinter (included with Python)

## 🚀 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/fitgirl-downloader.git
   cd fitgirl-downloader
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python fitgirl.py
   ```

## ⚙️ Configuration

First run will create configuration files:
- `config.json` - Main application settings
- `extractor_config.json` - Extraction tool settings

### Example Configuration:
```json
{
  "download_directory": "downloads",
  "json_only_mode": false,
  "unzip_directory": "downloads"
}
```

## 🎮 Usage

1. **Add Downloads:**
   - Paste FitGirl URLs directly
   - Use "Fetch Links" for FitGirl pages
   - Import from clipboard

2. **Download:**
   - Choose download method (Browser/Built-in)
   - Monitor progress in real-time
   - Pause/resume support

3. **Extract:**
   - Manual extraction via Extractor tab
   - Smart Manager for automatic extraction
   - JSON-only mode for tracked downloads

## 🔧 Smart Manager Features

- **Auto-scan** - Monitors folder every 30 seconds
- **Priority Extraction** - JSON-tracked archives first
- **Size Verification** - 20MB tolerance check
- **Multi-part Support** - .part01, .part001, etc.
- **Delete After Extract** - Optional cleanup

## 📋 Session Management

- **Import Tracking** - Monitors download progress
- **Archive Groups** - Groups related files together
- **Completion Detection** - Automatic status updates
- **Cache Management** - Clean session data

## ⚠️ Disclaimer

This tool is for educational and personal use only. 
Users are responsible for complying with FitGirl's terms of service and local copyright laws.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🔗 Dependencies

- `requests` - HTTP library for downloading
- `tkinter` - GUI framework (included with Python)
- `pathlib` - Modern path handling
- `threading` - Multi-threaded operations
- `json` - Configuration storage
- `re` - Regular expressions
- `subprocess` - WinRAR integration

## 🐛 Troubleshooting

**WinRAR not found:**
- Install WinRAR or update extractor_config.json path
- Use portable WinRAR if needed

**Downloads fail:**
- Check internet connection
- Try different download method
- Verify FitGirl URL is valid

**Extraction issues:**
- Ensure all parts are downloaded
- Check file permissions
- Verify archive integrity

## 📱 Screenshots

*(Add screenshots here showing main features)*

## 🔄 Updates

Updates are handled through Git. Pull the latest changes:

```bash
git pull origin main
```
