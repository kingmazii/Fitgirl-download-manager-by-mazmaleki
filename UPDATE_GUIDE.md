# 🔄 Update Management Guide

## 📋 Update Options for Your FitGirl Downloader

### **Option 1: GitHub Auto-Update (Recommended)**

#### **How It Works:**
1. App checks GitHub API for new releases
2. Shows update dialog with release notes
3. Downloads update with user permission
4. Installs and restarts automatically

#### **Integration Steps:**

1. **Add to main app (fitgirl.py):**
```python
# Add to imports
from updater import check_for_updates

# Add to menu bar
def create_menu_bar(self):
    menubar = tk.Menu(self.root)
    
    # Help menu
    help_menu = tk.Menu(menubar, tearoff=0)
    help_menu.add_command(label="🔄 Check for Updates", command=self.check_updates)
    help_menu.add_separator()
    help_menu.add_command(label="ℹ️ About", command=self.show_about)
    
    menubar.add_cascade(label="Help", menu=help_menu)
    self.root.config(menu=menubar)

def check_updates(self):
    """Check for updates"""
    check_for_updates(self.root)

def show_about(self):
    """Show about dialog"""
    messagebox.showinfo("About", 
                     "FitGirl Downloader v1.0.0\n\n"
                     "Created by: Maz.Maleki\n"
                     "Check for updates regularly!")
```

2. **Auto-check on startup:**
```python
def __init__(self, root):
    # ... existing code ...
    
    # Check for updates on startup (optional)
    self.root.after(2000, self.auto_check_updates)

def auto_check_updates(self):
    """Auto-check for updates on startup"""
    try:
        from config_manager import get_setting
        auto_check = get_setting("auto_check_updates", True)
        
        if auto_check:
            check_for_updates(self.root)
    except:
        pass
```

3. **Add to config_manager.py:**
```python
def get_setting(key, default=None):
    """Get setting with default value"""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        return config.get(key, default)
    except:
        return default
```

---

### **Option 2: Manual Update Notifications**

#### **Simple Update Check:**
```python
def check_updates_simple(self):
    """Simple update check"""
    try:
        import webbrowser
        webbrowser.open("https://github.com/yourusername/fitgirl-downloader/releases")
        messagebox.showinfo("Update", 
                         "Opening download page in browser...\n\n"
                         "Download the latest version and replace your current files.")
    except:
        messagebox.showerror("Error", "Failed to open download page")
```

---

### **Option 3: Update Server (Advanced)**

#### **Your Own Update Server:**
```python
# updater_server.py - Host on your server
import json
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/v1/version')
def get_version():
    return jsonify({
        "version": "1.1.0",
        "download_url": "https://yoursite.com/updates/fitgirl-latest.exe",
        "release_notes": "Bug fixes and new features...",
        "required": False,
        "release_date": "2026-02-05"
    })

@app.route('/api/v1/download')
def download_update():
    # Serve the update file
    return send_file("updates/fitgirl-latest.exe")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
```

#### **Client Update Checker:**
```python
def check_server_updates(self):
    """Check your own server for updates"""
    try:
        response = requests.get("https://yoursite.com/api/v1/version", timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            if self._is_newer_version(data["version"]):
                return self._show_server_update_dialog(data)
    except Exception as e:
        print(f"Server update check failed: {e}")
```

---

## 🚀 **Release Workflow**

### **When You Update:**

1. **Update Version Number:**
```python
# In fitgirl.py
APP_VERSION = "1.1.0"  # Increment this

def __init__(self, root):
    self.root.title(f"Maz.Maleki Fitgirl Downloader v{APP_VERSION}")
```

2. **Test Changes:**
   - Test all new features
   - Verify no regressions
   - Check update process works

3. **Create Release:**
```bash
# Create executable
pyinstaller --onefile --windowed fitgirl.py

# Tag release on GitHub
git tag v1.1.0
git push origin v1.1.0

# Create GitHub release
# Upload: fitgirl-downloader-v1.1.0.exe
# Add release notes
```

4. **Update Users:**
   - Users get auto-update notification
   - Or manually check Help → Check for Updates
   - Download and install new version

---

## 📱 **User Experience**

### **Update Dialog Flow:**
1. **Check:** App checks for updates on startup/manual trigger
2. **Notify:** Shows "Update Available!" dialog
3. **Preview:** Displays release notes and version info
4. **Choose:** User chooses Update Now/Later/Skip
5. **Download:** Shows progress bar during download
6. **Install:** Asks permission, installs, restarts

### **User Options:**
- ✅ **Auto-check on startup** (configurable)
- ✅ **Manual check** via Help menu
- ✅ **Skip versions** (remember user choice)
- ✅ **Release notes preview** before download
- ✅ **Permission required** for installation

---

## 🔒 **Security Considerations**

### **Update Security:**
- ✅ **HTTPS only** for update downloads
- ✅ **GitHub releases** (trusted source)
- ✅ **User permission** required
- ✅ **Digital signatures** (optional, for .exe)
- ✅ **Checksum verification** (optional)

### **Best Practices:**
- 🔄 **Incremental updates** (small patches)
- 📋 **Detailed release notes**
- 🧪 **Test before release**
- 📦 **Backup before update**
- 🔐 **Secure update channel**

---

## 🎯 **Recommended Implementation**

**Start with Option 1 (GitHub Auto-Update):**

1. ✅ **Easy to implement** (uses GitHub API)
2. ✅ **Secure and trusted** (GitHub infrastructure)
3. ✅ **Free hosting** (no server costs)
4. ✅ **Professional** (standard open source practice)
5. ✅ **User-friendly** (automatic updates)

**Add to your main app today and users will always have the latest version!** 🚀
