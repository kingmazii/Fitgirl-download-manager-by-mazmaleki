"""
Simple Update Notifier for FitGirl Downloader
Shows popup notification when updates are available on GitHub
Directs users to GitHub for manual download
"""

import requests
import tkinter as tk
from tkinter import messagebox
import webbrowser
import json

class SimpleUpdateNotifier:
    def __init__(self, current_version="1.0.0"):
        self.current_version = current_version
        self.github_repo = "yourusername/fitgirl-downloader"
        self.github_api = f"https://api.github.com/repos/{self.github_repo}/releases/latest"
        self.github_releases = f"https://github.com/{self.github_repo}/releases"
        
    def check_for_updates(self, parent_window=None, silent=False):
        """Check if updates are available and show notification"""
        try:
            response = requests.get(self.github_api, timeout=10)
            if response.status_code == 200:
                release_data = response.json()
                latest_version = release_data.get("tag_name", "v1.0.0").lstrip("v")
                release_notes = release_data.get("body", "")
                release_date = release_data.get("published_at", "")
                
                if self._is_newer_version(latest_version):
                    return self._show_update_notification(
                        latest_version, release_notes, release_date, parent_window
                    )
                else:
                    if not silent and parent_window:
                        messagebox.showinfo("Update Check", 
                                         "✅ You have the latest version!")
                    return False
            else:
                print(f"Failed to check updates: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Update check failed: {e}")
            if not silent and parent_window:
                messagebox.showerror("Update Error", 
                                 f"Failed to check for updates:\n{e}")
            return False
    
    def _is_newer_version(self, latest_version):
        """Compare version strings"""
        try:
            current_parts = [int(x) for x in self.current_version.split('.')]
            latest_parts = [int(x) for x in latest_version.split('.')]
            
            # Pad shorter version with zeros
            max_len = max(len(current_parts), len(latest_parts))
            current_parts.extend([0] * (max_len - len(current_parts)))
            latest_parts.extend([0] * (max_len - len(latest_parts)))
            
            return latest_parts > current_parts
        except:
            return False
    
    def _show_update_notification(self, latest_version, release_notes, release_date, parent_window):
        """Show simple update notification dialog"""
        if not parent_window:
            root = tk.Tk()
            root.withdraw()
            parent_window = root
        
        # Create notification dialog
        dialog = tk.Toplevel(parent_window)
        dialog.title("🔄 Update Available!")
        dialog.geometry("500x400")
        dialog.resizable(False, False)
        
        # Make dialog stand out
        dialog.attributes('-topmost', True)
        dialog.transient(parent_window)
        dialog.grab_set()
        
        # Main frame
        main_frame = tk.Frame(dialog, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        # Header with icon
        header_frame = tk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(header_frame, text="🔄", font=("Arial", 24)).pack(side="left")
        tk.Label(header_frame, text="Update Available!", 
                font=("Arial", 16, "bold"), fg="green").pack(side="left", padx=(10, 0))
        
        # Version info
        version_frame = tk.Frame(main_frame)
        version_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(version_frame, text=f"Current version: {self.current_version}", 
                font=("Arial", 10)).pack(anchor="w")
        tk.Label(version_frame, text=f"Latest version: {latest_version}", 
                font=("Arial", 12, "bold"), fg="blue").pack(anchor="w")
        
        if release_date:
            tk.Label(version_frame, text=f"Released: {release_date[:10]}", 
                    font=("Arial", 9), fg="gray").pack(anchor="w")
        
        # Release notes preview
        tk.Label(main_frame, text="What's new:", 
                font=("Arial", 10, "bold")).pack(anchor="w", pady=(15, 5))
        
        notes_frame = tk.Frame(main_frame)
        notes_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        notes_text = tk.Text(notes_frame, height=8, width=50, wrap="word")
        notes_text.pack(side="left", fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(notes_frame, command=notes_text.yview)
        scrollbar.pack(side="right", fill="y")
        notes_text.config(yscrollcommand=scrollbar.set)
        
        # Show first 500 characters of release notes
        preview_notes = release_notes[:500] + "..." if len(release_notes) > 500 else release_notes
        notes_text.insert("1.0", preview_notes)
        notes_text.config(state="disabled")
        
        # Action buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(15, 0))
        
        def download_now():
            """Open GitHub releases page"""
            webbrowser.open(self.github_releases)
            dialog.destroy()
        
        def remind_later():
            """Close dialog and remind later"""
            dialog.destroy()
        
        def skip_this_version():
            """Skip this version"""
            self._save_skipped_version(latest_version)
            dialog.destroy()
        
        # Buttons with better styling
        tk.Button(button_frame, text="📥 Download Now", command=download_now,
                 bg="green", fg="white", font=("Arial", 10, "bold"),
                 width=15).pack(side="left", padx=(0, 10))
        
        tk.Button(button_frame, text="⏰ Remind Later", command=remind_later,
                 font=("Arial", 10), width=15).pack(side="left", padx=5)
        
        tk.Button(button_frame, text="⏭️ Skip Version", command=skip_this_version,
                 font=("Arial", 10), width=15).pack(side="left", padx=5)
        
        # Center dialog on screen
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        dialog.wait_window()
        return True
    
    def _save_skipped_version(self, version):
        """Save skipped version to config"""
        try:
            from config_manager import set_setting
            set_setting("skipped_update_version", version)
        except:
            pass

# Convenience function for easy integration
def check_for_updates(parent_window=None, silent=False):
    """Convenience function to check for updates"""
    notifier = SimpleUpdateNotifier()
    return notifier.check_for_updates(parent_window, silent)

# Auto-check function for startup
def auto_check_updates(parent_window=None):
    """Check for updates on startup (silent if no update)"""
    try:
        from config_manager import get_setting
        auto_check = get_setting("auto_check_updates", True)
        skipped_version = get_setting("skipped_update_version", "")
        
        if auto_check:
            notifier = SimpleUpdateNotifier()
            # Don't check if user skipped this version
            response = requests.get(notifier.github_api, timeout=5)
            if response.status_code == 200:
                release_data = response.json()
                latest_version = release_data.get("tag_name", "v1.0.0").lstrip("v")
                
                if latest_version != skipped_version:
                    return notifier.check_for_updates(parent_window, silent=True)
    except:
        pass

if __name__ == "__main__":
    # Test the updater
    root = tk.Tk()
    root.withdraw()
    check_for_updates(root)
