"""
Auto-updater for FitGirl Downloader
Checks for updates from GitHub and applies them with user permission
"""

import requests
import json
import tkinter as tk
from tkinter import messagebox
import subprocess
import sys
import os
from pathlib import Path

class AppUpdater:
    def __init__(self, current_version="1.0.0"):
        self.current_version = current_version
        self.github_repo = "yourusername/fitgirl-downloader"
        self.github_api = f"https://api.github.com/repos/{self.github_repo}/releases/latest"
        
    def check_for_updates(self, parent_window=None):
        """Check if updates are available"""
        try:
            response = requests.get(self.github_api, timeout=10)
            if response.status_code == 200:
                release_data = response.json()
                latest_version = release_data.get("tag_name", "v1.0.0").lstrip("v")
                download_url = release_data.get("assets", [{}])[0].get("browser_download_url")
                release_notes = release_data.get("body", "")
                
                if self._is_newer_version(latest_version):
                    return self._show_update_dialog(latest_version, download_url, release_notes, parent_window)
                else:
                    if parent_window:
                        messagebox.showinfo("Update Check", "You have the latest version!")
                    return False
            else:
                print(f"Failed to check updates: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Update check failed: {e}")
            if parent_window:
                messagebox.showerror("Update Error", f"Failed to check for updates:\n{e}")
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
    
    def _show_update_dialog(self, latest_version, download_url, release_notes, parent_window):
        """Show update confirmation dialog"""
        if not parent_window:
            root = tk.Tk()
            root.withdraw()
            parent_window = root
        
        dialog = tk.Toplevel(parent_window)
        dialog.title("🔄 Update Available")
        dialog.geometry("600x500")
        dialog.resizable(False, False)
        
        # Center dialog
        dialog.transient(parent_window)
        dialog.grab_set()
        
        # Main frame
        main_frame = tk.Frame(dialog, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        # Update info
        tk.Label(main_frame, text="🔄 Update Available!", 
                font=("Arial", 14, "bold"), fg="green").pack(pady=(0, 10))
        
        tk.Label(main_frame, text=f"Current version: {self.current_version}").pack()
        tk.Label(main_frame, text=f"Latest version: {latest_version}", 
                font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
        # Release notes
        tk.Label(main_frame, text="Release Notes:", font=("Arial", 10, "bold")).pack(anchor="w")
        
        notes_frame = tk.Frame(main_frame)
        notes_frame.pack(fill="both", expand=True, pady=(5, 10))
        
        notes_text = tk.Text(notes_frame, height=10, width=60, wrap="word")
        notes_text.pack(side="left", fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(notes_frame, command=notes_text.yview)
        scrollbar.pack(side="right", fill="y")
        notes_text.config(yscrollcommand=scrollbar.set)
        
        notes_text.insert("1.0", release_notes)
        notes_text.config(state="disabled")
        
        # Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))
        
        user_choice = {"update": False}
        
        def update_now():
            user_choice["update"] = True
            dialog.destroy()
        
        def update_later():
            user_choice["update"] = False
            dialog.destroy()
        
        def skip_this_version():
            user_choice["update"] = "skip"
            dialog.destroy()
        
        tk.Button(button_frame, text="🔄 Update Now", command=update_now,
                 bg="green", fg="white", font=("Arial", 10, "bold")).pack(side="left", padx=(0, 5))
        tk.Button(button_frame, text="⏰ Update Later", command=update_later).pack(side="left", padx=5)
        tk.Button(button_frame, text="⏭️ Skip This Version", command=skip_this_version).pack(side="left", padx=5)
        
        dialog.wait_window()
        
        if user_choice["update"] is True:
            return self._download_and_install(download_url, parent_window)
        elif user_choice["update"] == "skip":
            # Save skipped version to config
            self._save_skipped_version(latest_version)
        
        return False
    
    def _download_and_install(self, download_url, parent_window):
        """Download and install update"""
        try:
            # Show progress dialog
            progress_dialog = tk.Toplevel(parent_window)
            progress_dialog.title("📥 Downloading Update")
            progress_dialog.geometry("400x150")
            progress_dialog.resizable(False, False)
            
            progress_frame = tk.Frame(progress_dialog, padx=20, pady=20)
            progress_frame.pack(fill="both", expand=True)
            
            tk.Label(progress_frame, text="Downloading update...").pack()
            
            progress_bar = tk.Canvas(progress_frame, height=20, width=350)
            progress_bar.pack(pady=10)
            
            status_label = tk.Label(progress_frame, text="Starting download...")
            status_label.pack()
            
            # Download file
            response = requests.get(download_url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            # Save to temp directory
            temp_dir = Path(tempfile.gettempdir())
            update_file = temp_dir / "fitgirl-downloader-update.exe"
            
            downloaded = 0
            chunk_size = 8192
            
            with open(update_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Update progress
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            progress_bar.delete("all")
                            progress_bar.create_rectangle(0, 0, progress * 3.5, 20, fill="green")
                            status_label.config(text=f"Downloaded: {progress:.1f}%")
            
            progress_dialog.destroy()
            
            # Ask for installation permission
            if messagebox.askyesno("Install Update", 
                                 "Update downloaded successfully!\n\nInstall now?\n\n"
                                 "The application will close during installation."):
                self._install_update(update_file)
            
            return True
            
        except Exception as e:
            messagebox.showerror("Update Failed", f"Failed to download update:\n{e}")
            return False
    
    def _install_update(self, update_file):
        """Install the update"""
        try:
            # Create installer script
            script_path = Path(tempfile.gettempdir()) / "update_installer.bat"
            
            script_content = f"""
@echo off
echo Installing FitGirl Downloader update...
timeout /t 2 /nobreak >nul
start "" "{update_file}"
del "{script_path}"
"""
            
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            # Launch installer and exit current app
            subprocess.Popen([str(script_path)], shell=True)
            sys.exit(0)
            
        except Exception as e:
            messagebox.showerror("Installation Failed", f"Failed to install update:\n{e}")
    
    def _save_skipped_version(self, version):
        """Save skipped version to config"""
        try:
            from config_manager import set_setting
            set_setting("skipped_update_version", version)
        except:
            pass

# Integration function for main app
def check_for_updates(parent_window=None):
    """Convenience function to check for updates"""
    updater = AppUpdater()
    return updater.check_for_updates(parent_window)

# Example usage in main app:
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    check_for_updates(root)
