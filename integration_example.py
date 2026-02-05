"""
Example: How to integrate updater into your main fitgirl.py
"""

# Add these imports to the top of fitgirl.py
import tkinter as tk
from tkinter import messagebox
from updater import check_for_updates

# In your DownloaderGUI class, add these methods:

class DownloaderGUI:
    def __init__(self, root):
        # ... existing init code ...
        
        # Add version constant
        self.APP_VERSION = "1.0.0"
        
        # Update the window title to include version
        self.root.title(f"Maz.Maleki Fitgirl Downloader v{self.APP_VERSION}")
        
        # Create menu bar with update option
        self.create_menu_bar()
        
        # Auto-check for updates after 2 seconds (optional)
        self.root.after(2000, self.auto_check_updates)
    
    def create_menu_bar(self):
        """Create menu bar with update option"""
        menubar = tk.Menu(self.root)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="🔄 Check for Updates", command=self.check_updates)
        help_menu.add_separator()
        help_menu.add_command(label="ℹ️ About", command=self.show_about)
        help_menu.add_command(label="📧 Contact", command=self.show_contact)
        
        menubar.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menubar)
    
    def check_updates(self):
        """Manual update check"""
        try:
            check_for_updates(self.root)
        except Exception as e:
            messagebox.showerror("Update Error", f"Failed to check for updates:\n{e}")
    
    def auto_check_updates(self):
        """Auto-check for updates on startup"""
        try:
            from config_manager import get_setting
            auto_check = get_setting("auto_check_updates", True)
            
            if auto_check:
                # Check silently (don't show "latest version" message)
                check_for_updates(self.root)
        except Exception as e:
            print(f"Auto-update check failed: {e}")
    
    def show_about(self):
        """Show about dialog"""
        about_text = f"""🎮 FitGirl Downloader v{self.APP_VERSION}

Created by: Maz.Maleki
Email: send2mazi@gmail.com

Features:
• Multi-threaded downloads
• Smart folder management
• Auto-extraction
• Delete after extract
• JSON-only mode

Check for updates regularly in Help menu!"""
        
        messagebox.showinfo("About FitGirl Downloader", about_text)
    
    def show_contact(self):
        """Show contact information"""
        contact_text = """📧 Contact & Support

Need help? Email: send2mazi@gmail.com
Business inquiries: send2mazi@gmail.com

Found a bug? Report it on GitHub:
https://github.com/yourusername/fitgirl-downloader/issues

Want to support development?
Check the donation menu in the app!"""
        
        messagebox.showinfo("Contact & Support", contact_text)

# Add this to your existing create_widgets method:
def create_widgets(self):
    # ... existing code ...
    
    # Add update status to status bar (optional)
    self.update_status_label = tk.Label(self.status_frame, 
                                     text="🔄 Auto-update enabled", 
                                     fg="green")
    self.update_status_label.pack(side="right", padx=10)

# Add keyboard shortcut for update check (optional)
def setup_shortcuts(self):
    """Setup keyboard shortcuts"""
    self.root.bind('<Control-u>', lambda e: self.check_updates())
    self.root.bind('<F1>', lambda e: self.show_about())

# Call setup_shortcuts in __init__ after other setup
# self.setup_shortcuts()
