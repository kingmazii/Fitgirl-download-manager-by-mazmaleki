"""
Simple Integration Example for Update Notifications
Just add these few lines to your main fitgirl.py
"""

# 1. Add these imports to the top of fitgirl.py
from simple_updater import check_for_updates, auto_check_updates

# 2. Add version constant to your DownloaderGUI class
class DownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.APP_VERSION = "1.0.0"  # Update this when you release new versions
        
        # ... rest of your existing __init__ code ...
        
        # Add update check to menu
        self.create_menu_bar()
        
        # Auto-check for updates on startup (after 2 seconds)
        self.root.after(2000, lambda: auto_check_updates(self.root))
    
    # 3. Add this method to create menu bar
    def create_menu_bar(self):
        """Create menu bar with update option"""
        menubar = tk.Menu(self.root)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="🔄 Check for Updates", command=self.check_updates)
        help_menu.add_separator()
        help_menu.add_command(label="ℹ️ About", command=self.show_about)
        
        menubar.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menubar)
    
    # 4. Add this method for manual update check
    def check_updates(self):
        """Manual update check"""
        check_for_updates(self.root)
    
    # 5. Update your existing show_about method
    def show_about(self):
        """Show about dialog with version"""
        about_text = f"""🎮 FitGirl Downloader v{self.APP_VERSION}

Created by: Maz.Maleki
Email: send2mazi@gmail.com

Features:
• Multi-threaded downloads
• Smart folder management  
• Auto-extraction
• Delete after extract
• JSON-only mode

Check for updates in Help menu!"""
        
        messagebox.showinfo("About FitGirl Downloader", about_text)

# 6. Update your window title to include version
# In __init__, change:
self.root.title("Maz.Maleki Fitgirl Downloader")
# To:
self.root.title(f"Maz.Maleki Fitgirl Downloader v{self.APP_VERSION}")

# That's it! Your app now has update notifications!

"""
🎯 BENEFITS OF THIS APPROACH:

✅ SIMPLE - Only 3 lines of code to add
✅ SAFE - No automatic downloads/installations  
✅ USER CONTROL - Users choose when to update
✅ SECURE - Downloads from trusted GitHub
✅ PROFESSIONAL - Standard software practice
✅ NO MAINTENANCE - GitHub handles hosting

🔄 UPDATE PROCESS:
1. App checks GitHub API on startup
2. Shows popup if new version available
3. User clicks "Download Now" 
4. Opens GitHub releases page in browser
5. User downloads and installs manually

📋 WHEN YOU UPDATE:
1. Change APP_VERSION = "1.1.0"
2. Create new release on GitHub
3. Upload your new .exe file
4. Users get notification automatically
"""
