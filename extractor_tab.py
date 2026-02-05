import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import subprocess
import re
import os
from pathlib import Path
from datetime import datetime
import time
from collections import deque
from extractor_utils import (
    find_winrar_path, get_available_extractors, 
    set_tool_path, get_common_paths, load_config
)
from donate_window import create_donate_window
from config_manager import get_setting, set_setting, get_archive_groups_status, can_extract_group, get_group_extraction_info, get_group_filename_range
from smart_folder_manager import SmartFolderManager

class ExtractorTab:
    def __init__(self, parent, main_app=None):
        self.parent = parent
        self.main_app = main_app  # Reference to main app for download monitoring
        self.frame = ttk.Frame(parent)
        
        # Variables
        self.archive_path = tk.StringVar()
        self.dest_path = tk.StringVar()
        self.password = tk.StringVar()
        self.available_tools = {}
        self.extraction_process = None  # Track extraction process for cancellation
        
        # Smart Folder Manager
        self.smart_manager = None
        self.smart_manager_window = None
        self.first_extraction_done = False
        
        # Use main app's unrar variable if available, otherwise create own
        if main_app and hasattr(main_app, 'unrar_after_download'):
            self.unrar_after_download = main_app.unrar_after_download
        else:
            self.unrar_after_download = tk.BooleanVar(value=False)  # Auto-unrar option
        
        # Delete archives after extraction - shared with Smart Manager
        self.delete_after_extract = tk.BooleanVar(value=False)
        
        # Set default destination to downloads folder
        self.set_default_destination()
        
        self.build_ui()
        self.detect_tools()
    
    def set_default_destination(self):
        """Set default destination to downloads folder"""
        try:
            # Always set destination to current download directory
            if self.main_app and hasattr(self.main_app, 'download_dir'):
                default_path = str(self.main_app.download_dir.resolve())
            else:
                # Fallback to relative downloads folder
                downloads_path = Path("downloads").resolve()
                default_path = str(downloads_path)
            
            self.dest_path.set(default_path)
            print(f"Extractor destination set to: {default_path}")
        except Exception as e:
            print(f"Error setting default destination: {e}")
        
        # Set archive path to download directory by default
        self.set_default_archive_path()
    
    def update_paths_from_download_dir(self):
        """Update both archive and destination paths when download directory changes"""
        try:
            if self.main_app and hasattr(self.main_app, 'download_dir'):
                download_dir = str(self.main_app.download_dir.resolve())
                print(f"Updating extractor paths to: {download_dir}")
                
                # Update destination path
                self.dest_path.set(download_dir)
                # Save to config
                set_setting("unzip_directory", download_dir)
                
                # Always update archive path to match download directory
                self.archive_path.set(download_dir)
        except Exception as e:
            print(f"Error updating paths: {e}")
    
    def set_default_archive_path(self):
        """Set archive path to download directory"""
        try:
            if self.main_app and hasattr(self.main_app, 'download_dir'):
                archive_dir = str(self.main_app.download_dir.resolve())
            else:
                # Fallback to relative downloads folder
                archive_dir = str(Path("downloads").resolve())
            
            # Only set if archive path is empty
            if not self.archive_path.get().strip():
                self.archive_path.set(archive_dir)
                print(f"Extractor archive path set to: {archive_dir}")
        except Exception as e:
            print(f"Error setting default archive path: {e}")
    
    def build_ui(self):
        # Main container with padding
        main_container = ttk.Frame(self.frame, padding="10")
        main_container.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(main_container, text="🗂️ ARCHIVE EXTRACTOR", font=("Segoe UI", 12, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Archive path section
        ttk.Label(main_container, text="Archive File:", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", padx=(0, 10))
        archive_frame = ttk.Frame(main_container)
        archive_frame.grid(row=1, column=1, sticky="ew", pady=(0, 15))
        
        archive_entry = ttk.Entry(archive_frame, textvariable=self.archive_path, width=60, font=("Segoe UI", 9))
        archive_entry.pack(side="left", fill="x", expand=True)
        self.create_context_menu(archive_entry)
        
        ttk.Button(archive_frame, text="Browse", command=self.browse_archive, width=12).pack(side="left", padx=(10, 0))
        
        # Destination path section
        ttk.Label(main_container, text="Destination:", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w", padx=(0, 10))
        dest_frame = ttk.Frame(main_container)
        dest_frame.grid(row=2, column=1, sticky="ew", pady=(0, 15))
        
        dest_entry = ttk.Entry(dest_frame, textvariable=self.dest_path, width=60, font=("Segoe UI", 9))
        dest_entry.pack(side="left", fill="x", expand=True)
        self.create_context_menu(dest_entry)
        
        ttk.Button(dest_frame, text="Browse", command=self.browse_dest, width=12).pack(side="left", padx=(10, 0))
        
        # Tool configuration section
        self.tool_frame = ttk.Frame(main_container)
        self.tool_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        
        ttk.Label(self.tool_frame, text="Extraction Tool:", font=("Segoe UI", 10)).pack(side="left", padx=(0, 10))
        ttk.Label(self.tool_frame, text="WinRAR", font=("Segoe UI", 10, "bold")).pack(side="left")
        
        self.config_btn = ttk.Button(self.tool_frame, text="⚙️ Configure", command=self.show_config_dialog, width=12)
        self.config_btn.pack(side="right")
        
        # Action buttons section
        button_frame = ttk.Frame(main_container)
        button_frame.grid(row=4, column=0, columnspan=2, pady=(0, 20))
        
        self.extract_btn = ttk.Button(button_frame, text="🗜️ Extract Archive", command=self.start_extract, width=20)
        self.extract_btn.pack(side="left", padx=(0, 10))
        
        self.stop_btn = ttk.Button(button_frame, text="⏹️ Stop", command=self.stop_extraction, width=15, state="disabled")
        self.stop_btn.pack(side="left", padx=(0, 10))
        
        self.bring_to_front_btn = ttk.Button(button_frame, text="🔍 Bring to Front", command=self.bring_progress_to_front, width=18, state="disabled")
        self.bring_to_front_btn.pack(side="left", padx=(0, 10))
        
        self.smart_manager_btn = ttk.Button(button_frame, text="🧠 Smart Manager", command=self.open_smart_manager, width=18)
        self.smart_manager_btn.pack(side="left")
        
        # Progress section
        progress_frame = ttk.LabelFrame(main_container, text="Extraction Progress", padding="10")
        progress_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        
        self.progress = ttk.Progressbar(progress_frame, length=500, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 5))
        
        self.progress_label = ttk.Label(progress_frame, text="0%", font=("Segoe UI", 9))
        self.progress_label.pack()
        
        # Status section
        status_frame = ttk.LabelFrame(main_container, text="Status", padding="10")
        status_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        
        self.status_label = ttk.Label(status_frame, text="Ready to extract archives", font=("Segoe UI", 10))
        self.status_label.pack()
        
        # Status window section
        status_window_frame = ttk.LabelFrame(main_container, text="Extraction Status", padding="10")
        status_window_frame.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        
        # Create scrolled text widget for status window
        status_container = ttk.Frame(status_window_frame)
        status_container.pack(fill="both", expand=True)
        
        self.status_text = tk.Text(status_container, height=8, width=80, font=("Consolas", 9), wrap=tk.WORD, state="disabled")
        status_scrollbar = ttk.Scrollbar(status_container, orient="vertical", command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=status_scrollbar.set)
        
        self.status_text.pack(side="left", fill="both", expand=True)
        status_scrollbar.pack(side="right", fill="y")
        
        # Clear status button
        clear_status_btn_frame = ttk.Frame(status_window_frame)
        clear_status_btn_frame.pack(fill="x", pady=(5, 0))
        ttk.Button(clear_status_btn_frame, text="Clear Status", command=self.clear_status, width=12).pack(side="right")
        
        # Auto-extract section
        auto_frame = ttk.LabelFrame(main_container, text="Auto-Extract Settings", padding="10")
        auto_frame.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        
        # Auto-extract checkbox
        checkbox_frame = ttk.Frame(auto_frame)
        checkbox_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Checkbutton(checkbox_frame, text="Auto-extract after downloads complete", 
                       variable=self.unrar_after_download, command=self.update_auto_status).pack(side="left")
        
        ttk.Checkbutton(checkbox_frame, text="🗑️ Delete archives after extraction", 
                       variable=self.delete_after_extract).pack(side="left", padx=(20, 0))
        
        self.auto_status_label = ttk.Label(auto_frame, text="Auto-extract is disabled", font=("Segoe UI", 9), foreground="gray")
        self.auto_status_label.pack()
        
        # Note section
        note_text = "Note: Make sure WinRAR is installed and configured. The extractor supports multi-part archives (part01, part001, part1, part0001)."
        note_label = ttk.Label(main_container, text=note_text, font=("Segoe UI", 9), foreground="blue", wraplength=600)
        note_label.grid(row=9, column=0, columnspan=2, pady=(10, 0))
        
        # Warning message about WinRAR background button
        warning_text = "⚠️ DO NOT PRESS BACKGROUND BUTTON ON WINRAR WINDOWS"
        warning_label = ttk.Label(main_container, text=warning_text, font=("Segoe UI", 11, "bold"), foreground="red")
        warning_label.grid(row=10, column=0, columnspan=2, pady=(10, 5))
        
        # Additional note about extraction advantage
        advantage_text = "Note: This extractor has the advantage of extracting RAR files directly to the selected partition, rather than first unpacking them to the Windows temporary folder and then copying them to the destination. Even the WinRAR application itself cannot do this, even when the option is enabled in the settings."
        advantage_label = ttk.Label(main_container, text=advantage_text, font=("Segoe UI", 9), foreground="blue", wraplength=600)
        advantage_label.grid(row=11, column=0, columnspan=2, pady=(10, 0))
        
        # Configure grid weights
        main_container.columnconfigure(1, weight=1)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)

    def show_donate_window(self):
        """Show the donation window"""
        create_donate_window(self.parent)

    def show_config_dialog(self):
        """Show configuration dialog for setting WinRAR path"""
        config_window = tk.Toplevel(self.parent)
        config_window.title("Configure Extraction Tool")
        config_window.geometry("600x200")  # Wider window
        config_window.transient(self.parent)
        config_window.grab_set()
        
        # Load current config
        config = load_config()
        
        # WinRAR configuration
        winrar_frame = ttk.LabelFrame(config_window, text="WinRAR Configuration", padding=10)
        winrar_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(winrar_frame, text="WinRAR Executable:").grid(row=0, column=0, sticky="w", padx=5)
        winrar_var = tk.StringVar(value=config.get("winrar", ""))
        winrar_entry = ttk.Entry(winrar_frame, textvariable=winrar_var, width=60)  # Wider entry
        winrar_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")  # Expand horizontally
        ttk.Button(winrar_frame, text="Browse", command=lambda: self.browse_tool_path(winrar_var)).grid(row=0, column=2, padx=5)
        
        def save_winrar():
            """Save WinRAR configuration"""
            if winrar_var.get().strip():
                if os.path.exists(winrar_var.get().strip()):
                    set_tool_path("winrar", winrar_var.get().strip())
                    messagebox.showinfo("Success", "WinRAR path saved successfully!")
                    self.detect_tools()  # Refresh tool detection
                else:
                    messagebox.showwarning("Invalid Path", f"WinRAR path not found: {winrar_var.get()}")
            else:
                messagebox.showinfo("Info", "Please browse to a valid WinRAR executable first.")
        
        ttk.Button(winrar_frame, text="Save WinRAR", command=save_winrar).grid(row=0, column=3, padx=5)
        
        # Configure grid weights for proper expansion
        winrar_frame.columnconfigure(1, weight=1)
        
        # Common paths help
        help_frame = ttk.LabelFrame(config_window, text="Common Installation Paths", padding=10)
        help_frame.pack(fill="x", padx=10, pady=10)
        
        help_text = """Common locations:
• C:\Program Files\WinRAR\WinRAR.exe
• C:\Program Files (x86)\WinRAR\WinRAR.exe"""
        
        ttk.Label(help_frame, text=help_text, justify="left").pack()
        
        # Buttons
        btn_frame = ttk.Frame(config_window)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="Close", command=config_window.destroy).pack(side="left", padx=5)

    def browse_tool_path(self, variable):
        """Browse for tool executable"""
        file = filedialog.askopenfilename(
            title="Select extraction tool executable",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if file:
            variable.set(file)

    def detect_tools(self):
        """Detect available extraction tools - WinRAR only"""
        self.available_tools = {}
        
        # Detect WinRAR only
        winrar_path = find_winrar_path()
        if winrar_path:
            self.available_tools["winrar"] = winrar_path
        
        # Set WinRAR as default if found
        if self.available_tools:
            self.status_label.config(text="✅ Found WinRAR on your system", foreground="green")
            self.extract_btn.config(state="normal")
        else:
            self.status_label.config(text="❌ WinRAR not found. Please install WinRAR.", foreground="red")
            self.extract_btn.config(state="disabled")

    def browse_archive(self):
        file = filedialog.askopenfilename(
            title="Select part001.rar",
            filetypes=[("RAR archives", "*.rar"), ("All archives", "*.zip;*.rar;*.7z")]
        )
        if file:
            self.archive_path.set(file)

    def browse_dest(self):
        folder = filedialog.askdirectory(title="Select destination folder")
        if folder:
            self.dest_path.set(folder)
            # Save to config
            set_setting("unzip_directory", folder)

    def start_extract(self):
        """Start extraction using Smart Folder Manager"""
        if not self.first_extraction_done:
            self.first_extraction_done = True
            self.open_smart_manager(auto_start=True)
        else:
            self.open_smart_manager()
    
    def open_smart_manager(self, auto_start=False):
        """Open Smart Folder Manager in a separate window"""
        if self.smart_manager_window and self.smart_manager_window.winfo_exists():
            self.smart_manager_window.lift()
            self.smart_manager_window.focus_force()
            return
            
        # Create new window for Smart Manager
        self.smart_manager_window = tk.Toplevel(self.parent)
        self.smart_manager_window.title("🧠 Smart Download Folder Manager")
        self.smart_manager_window.geometry("1000x730")
        
        # Create Smart Manager instance
        self.smart_manager = SmartFolderManager(self.smart_manager_window)
        self.smart_manager.frame.pack(fill="both", expand=True)
        
        # Link the delete checkboxes
        self.smart_manager.delete_after_extract.set(self.delete_after_extract.get())
        self.delete_after_extract.trace('w', lambda *args: self.smart_manager.delete_after_extract.set(self.delete_after_extract.get()))
        self.smart_manager.delete_after_extract.trace('w', lambda *args: self.delete_after_extract.set(self.smart_manager.delete_after_extract.get()))
        
        # Set the download folder to match extractor destination
        if self.dest_path.get():
            self.smart_manager.download_folder.set(self.dest_path.get())
            
        # Auto-start scanning if requested
        if auto_start:
            self.smart_manager_window.after(1000, self.smart_manager.scan_folder)
            
        # Handle window closing
        def on_closing():
            self.smart_manager_window.destroy()
            self.smart_manager_window = None
            self.smart_manager = None
            
        self.smart_manager_window.protocol("WM_DELETE_WINDOW", on_closing)

    
    def check_extraction_readiness(self):
        """Check if extraction can proceed based on download completion"""
        try:
            groups = get_archive_groups_status()
            
            if not groups:
                # No archive groups found, proceed with extraction
                return True
            
            incomplete_groups = []
            total_imported = 0
            total_downloaded = 0
            
            for group_key, group_data in groups.items():
                imported_count = group_data.get('imported_count', 0)
                downloaded_count = group_data.get('downloaded_count', 0)
                total_parts = group_data.get('total_parts', 0)
                
                total_imported += imported_count
                total_downloaded += downloaded_count
                
                # Check if this group is incomplete
                can_extract, reason = can_extract_group(group_key)
                if not can_extract and downloaded_count > 0:  # Only show groups with some downloads
                    incomplete_groups.append({
                        'name': group_data.get('base_name', 'Unknown'),
                        'imported': imported_count,
                        'downloaded': downloaded_count,
                        'total': total_parts if total_parts > 0 else imported_count,
                        'reason': reason,
                        'is_optional': group_data.get('is_optional', False)
                    })
            
            if not incomplete_groups:
                # All groups are ready for extraction
                return True
            
            # Show confirmation dialog for incomplete downloads
            return self.show_incomplete_confirmation(incomplete_groups, total_imported, total_downloaded)
            
        except Exception as e:
            print(f"Error checking extraction readiness: {e}")
            # If there's an error checking, allow extraction to proceed
            return True
    
    def show_incomplete_confirmation(self, incomplete_groups, total_imported, total_downloaded):
        """Show confirmation dialog for incomplete downloads"""
        # Create confirmation window
        confirm_window = tk.Toplevel(self.parent)
        confirm_window.title("⚠️ Incomplete Downloads Detected")
        confirm_window.geometry("600x500")
        confirm_window.transient(self.parent)
        confirm_window.grab_set()
        
        # Make window modal
        confirm_window.focus_set()
        
        # Main frame
        main_frame = ttk.Frame(confirm_window, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Warning message
        warning_text = "⚠️ Some archives are not completely downloaded!"
        warning_label = ttk.Label(main_frame, text=warning_text, font=("Segoe UI", 12, "bold"), foreground="orange")
        warning_label.pack(pady=(0, 15))
        
        # Summary
        summary_text = f"You have imported {total_imported} archive files but only downloaded {total_downloaded}."
        summary_label = ttk.Label(main_frame, text=summary_text, font=("Segoe UI", 10))
        summary_label.pack(pady=(0, 15))
        
        # Scrollable frame for incomplete groups
        canvas = tk.Canvas(main_frame, height=200)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Add incomplete groups to the list
        for i, group in enumerate(incomplete_groups):
            group_frame = ttk.Frame(scrollable_frame)
            group_frame.pack(fill="x", padx=5, pady=5)
            
            # Group name
            name_text = group['name']
            if group['is_optional']:
                name_text += " (Optional)"
            name_label = ttk.Label(group_frame, text=name_text, font=("Segoe UI", 10, "bold"))
            name_label.pack(anchor="w")
            
            # Status
            status_text = f"Downloaded: {group['downloaded']}/{group['total']} parts"
            status_label = ttk.Label(group_frame, text=status_text, font=("Segoe UI", 9))
            status_label.pack(anchor="w", padx=(20, 0))
            
            # Reason
            reason_label = ttk.Label(group_frame, text=f"⚠️ {group['reason']}", font=("Segoe UI", 9), foreground="red")
            reason_label.pack(anchor="w", padx=(20, 0))
            
            if i < len(incomplete_groups) - 1:
                ttk.Separator(scrollable_frame, orient="horizontal").pack(fill="x", padx=5, pady=5)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Question
        question_text = "Are you sure you want to proceed with extraction?"
        question_label = ttk.Label(main_frame, text=question_text, font=("Segoe UI", 11, "bold"))
        question_label.pack(pady=(15, 10))
        
        # Warning about potential issues
        warning2_text = "⚠️ Extracting incomplete archives may result in corrupted files or failed extraction!"
        warning2_label = ttk.Label(main_frame, text=warning2_text, font=("Segoe UI", 10), foreground="red")
        warning2_label.pack(pady=(0, 15))
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(10, 0))
        
        result = {'proceed': False}
        
        def on_proceed():
            result['proceed'] = True
            confirm_window.destroy()
        
        def on_cancel():
            result['proceed'] = False
            confirm_window.destroy()
        
        ttk.Button(button_frame, text="✅ Yes, Proceed Anyway", command=on_proceed, width=20).pack(side="left", padx=5)
        ttk.Button(button_frame, text="❌ No, Cancel", command=on_cancel, width=15).pack(side="left", padx=5)
        
        # Wait for window to close
        confirm_window.wait_window()
        
        return result['proceed']
    
    def bring_progress_to_front(self):
        """Bring WinRAR window to front and restore it properly"""
        try:
            import ctypes
            from ctypes import wintypes
            
            # Define Windows constants
            SW_RESTORE = 9
            SW_SHOW = 5
            SW_SHOWNORMAL = 1
            
            # Find WinRAR window (try multiple approaches)
            hwnd = None
            
            # Try different window titles for WinRAR
            possible_titles = ["WinRAR", "Extracting", "WinRAR *", "WinRAR x64"]
            
            for title in possible_titles:
                hwnd = ctypes.windll.user32.FindWindowW(None, title)
                if hwnd:
                    break
            
            # Method 2: Try to find by window class
            if not hwnd:
                hwnd = ctypes.windll.user32.FindWindowW("WinRAR", None)
            
            # Method 3: Enumerate windows to find WinRAR
            if not hwnd:
                def enum_callback(hwnd, lparam):
                    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buffer = ctypes.create_unicode_buffer(length + 1)
                        ctypes.windll.user32.GetWindowTextW(hwnd, buffer, length + 1)
                        window_text = buffer.value
                        if "WinRAR" in window_text:
                            lparam[0] = hwnd
                    return True
                
                callback = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.POINTER(ctypes.c_int))
                
                # Enumerate windows to find WinRAR
                hwnd_ptr = ctypes.c_int(0)
                ctypes.windll.user32.EnumWindows(callback, ctypes.byref(hwnd_ptr))
                
                if hwnd_ptr.value:
                    hwnd = hwnd_ptr.value
                else:
                    # Fallback: try to find by class name
                    hwnd = ctypes.windll.user32.FindWindowW(None, "WinRAR")
                
                if hwnd:
                    # Restore and bring to front
                    if ctypes.windll.user32.IsIconic(hwnd):
                        ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
                    else:
                        ctypes.windll.user32.ShowWindow(hwnd, SW_SHOW)
                    
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                    self.status_label.config(text="✅ WinRAR window brought to front", foreground="green")
                else:
                    self.status_label.config(text="❌ WinRAR window not found", foreground="orange")
                    
        except Exception as e:
            self.status_label.config(text=f"❌ Error bringing WinRAR to front: {e}", foreground="red")
            
    def stop_extraction(self):
        """Stop the extraction process"""
        if self.extraction_process and self.extraction_process.poll() is None:
            try:
                self.extraction_process.terminate()
                self.status_message("⏹️ Extraction stopped by user", "orange")
            except:
                pass
        
        self.extract_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.bring_to_front_btn.config(state="disabled")
        self.progress_label.config(text="Stopped")
    
    def is_extraction_active(self):
        """Check if extraction is currently active"""
        return (self.extraction_process is not None and 
                self.extraction_process.poll() is None)

    def update_progress(self, percent):
        self.progress["value"] = percent
        self.progress_label.config(text=f"{percent}%")

    def status_message(self, message, color="black"):
        """Add a status message to the status window with permanent color"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        def update_status():
            try:
                # Enable the text widget for editing
                self.status_text.config(state="normal")
                
                # Insert the message with timestamp
                self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
                
                # Apply color to the last line
                line_start = f"{self.status_text.index('end-2c').split('.')[0]}.0"
                line_end = f"{self.status_text.index('end-1c').split('.')[0]}.0"
                tag_name = f"color_{len(self.status_text.tag_names())}"  # Unique tag name
                self.status_text.tag_add(tag_name, line_start, line_end)
                self.status_text.tag_config(tag_name, foreground=color)
                
                # Scroll to bottom and disable editing
                self.status_text.see(tk.END)
                self.status_text.config(state="disabled")
            except Exception as e:
                print(f"Error updating status: {e}")
        
        # Ensure this runs in the main thread
        if threading.current_thread() == threading.main_thread():
            update_status()
        else:
            self.parent.after(0, update_status)
    
    def update_auto_status(self):
        """Update auto-extract status label based on checkbox state"""
        if self.unrar_after_download.get():
            self.auto_status_label.config(text="Auto-extract is enabled", foreground="green")
        else:
            self.auto_status_label.config(text="Auto-extract is disabled", foreground="gray")
    
    def clear_status(self):
        """Clear the status window"""
        self.status_text.config(state="normal")
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state="disabled")
    
    def enqueue_extractable_groups(self):
        """Populate extraction queue with groups that can be extracted"""
        groups = get_archive_groups_status()
        
        # Clear existing queue
        self.extract_queue.clear()
        
        # Sort groups to process main game first, then optional
        sorted_groups = sorted(groups.items(), key=lambda x: (not x[1].get('is_optional', False), x[0]))
        
        for group_key, group_data in sorted_groups:
            # Skip already extracted groups
            if group_key in self.extracted_groups:
                self.status_message(f"⏭️ Group '{group_data.get('base_name', group_key)}' already extracted, skipping", "gray")
                continue
                
            # Check if group can be extracted
            can_extract, reason = can_extract_group(group_key)
            if can_extract:
                self.extract_queue.append(group_key)
                self.status_message(f"📋 Queued group '{group_data.get('base_name', group_key)}' for extraction", "blue")
            else:
                self.status_message(f"⏸️ Group '{group_data.get('base_name', group_key)}' not ready: {reason}", "orange")
        
        self.status_message(f"🎯 Queue populated with {len(self.extract_queue)} groups", "green")
    
    def _process_extract_queue(self):
        """Process the extraction queue - this is the core sequential extraction logic"""
        self.status_message(f"🔄 Processing queue. is_extracting={self.is_extracting}, queue_size={len(self.extract_queue)}", "blue")
        
        if self.is_extracting:
            self.status_message("⏸️ Already extracting, waiting...", "orange")
            return  # Already extracting
            
        if not self.extract_queue:
            # No more groups to extract
            self.status_message("🏁 Extraction queue completed", "green")
            self.extraction_finished(True)
            return
        
        # Get next group to extract
        group_key = self.extract_queue.popleft()
        self.is_extracting = True
        
        groups = get_archive_groups_status()
        group_name = groups[group_key].get('base_name', group_key)
        self.status_message(f"🎯 Starting extraction of group '{group_name}' (remaining: {len(self.extract_queue)})", "blue")
        
        # Start extraction in background thread
        thread = threading.Thread(
            target=self._extract_group_worker,
            args=(group_key,),
            daemon=True
        )
        thread.start()
    
    def _extract_group_worker(self, group_key):
        """Worker thread for extracting a single group"""
        try:
            groups = get_archive_groups_status()
            group_data = groups[group_key]
            group_name = group_data.get('base_name', group_key)
            
            self.status_message(f"🔧 Starting extraction of group '{group_name}'...", "blue")
            
            # Get filenames and find the first part
            filenames = group_data.get('filenames', {})
            if not filenames:
                raise Exception("No filenames found for group")
            
            # Get first part (lowest number)
            first_part_num = min(filenames.keys(), key=lambda x: int(x) if x.isdigit() else 0)
            first_archive_name = filenames[first_part_num]
            
            # Construct full path
            base_path = self.dest_path.get()
            full_archive_path = f"{base_path}\\{first_archive_name}"
            
            self.status_message(f"📁 Archive path: {full_archive_path}", "blue")
            
            # Check if file exists
            if not Path(full_archive_path).exists():
                raise Exception(f"File not found: {first_archive_name}")
            
            # Set archive path for extraction
            self.archive_path.set(full_archive_path)
            
            self.status_message(f"🚀 Starting WinRAR extraction...", "blue")
            
            # Start extraction (non-blocking)
            process = self.run_extraction(wait_for_completion=False)
            
            if process:
                self.status_message(f"✅ WinRAR process started with PID: {process.pid}", "green")
                # Monitor completion
                self._monitor_extraction_process(process, group_key, group_name)
            else:
                raise Exception("Failed to start extraction process")
                
        except Exception as e:
            self.status_message(f"💥 Error extracting group '{group_name}': {str(e)}", "red")
            self._finish_group_extraction(group_key, success=False)
    
    def _monitor_extraction_process(self, process, group_key, group_name):
        """Monitor extraction process and handle completion"""
        def check_process():
            if process.poll() is None:
                # Still running, check again in 1 second
                self.status_message(f"⏳ Extraction of '{group_name}' still running...", "blue")
                self.parent.after(1000, lambda: check_process())
            else:
                # Process finished
                success = process.returncode == 0
                self.status_message(f"🏁 Process finished for '{group_name}'. Return code: {process.returncode}", "blue")
                
                if success:
                    self.status_message(f"✅ Successfully extracted group '{group_name}'", "green")
                else:
                    self.status_message(f"❌ Extraction failed for group '{group_name}' (exit code: {process.returncode})", "red")
                
                self._finish_group_extraction(group_key, success)
        
        # Start monitoring
        self.status_message(f"👁️ Starting to monitor extraction process for '{group_name}'...", "blue")
        check_process()
    
    def _finish_group_extraction(self, group_key, success):
        """Called when group extraction finishes - this is the MAGIC that continues the queue"""
        groups = get_archive_groups_status()
        group_name = groups[group_key].get('base_name', group_key)
        
        # Mark group as extracted
        self.extracted_groups.add(group_key)
        
        # Reset extraction state
        self.is_extracting = False
        self.extraction_process = None
        
        # Update progress
        total_groups = len(groups)
        completed_count = len(self.extracted_groups)
        progress_percent = int((completed_count / total_groups) * 100)
        self.progress.config(value=progress_percent)
        self.progress_label.config(text=f"{progress_percent}%")
        
        self.status_message(f"🔚 Group '{group_name}' extraction finished. Success: {success}. Queue size: {len(self.extract_queue)}", "blue")
        
        # 🎯 THIS IS THE MAGIC - Process next group in queue
        self.parent.after(1000, self._process_extract_queue)
    
    def simulate_manual_extraction(self, archive_file, group_name):
        """Simulate manual extraction process"""
        try:
            exe = self.available_tools["winrar"]
            dest = self.dest_path.get()
            pwd = self.password.get()
            
            # Create folder based on group name
            folder_name = self.clean_archive_name(group_name)
            extract_dest = Path(dest) / folder_name
            extract_dest.mkdir(exist_ok=True)
            
            # Build WinRAR command (same as regular extraction)
            cmd = [exe, "x", str(archive_file), str(extract_dest), "-y"]
            if pwd:
                cmd.insert(2, f"-p{pwd}")
            cmd.append("-ibck+")
            
            # Run extraction
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            # Wait for completion
            process.wait()
            success = process.returncode == 0
            
            return success
            
        except Exception as e:
            self.parent.after(0, lambda: self.status_message(f"Error extracting {group_name}: {str(e)}", "red"))
            return False
    
    def extract_single_archive_internal(self, archive_file, group_name):
        """Extract a single archive using the same logic as regular extraction"""
        try:
            exe = self.available_tools["winrar"]
            dest = self.dest_path.get()
            pwd = self.password.get()
            
            # Create folder based on group name
            folder_name = self.clean_archive_name(group_name)
            extract_dest = Path(dest) / folder_name
            extract_dest.mkdir(exist_ok=True)
            
            # Build WinRAR command
            cmd = [exe, "x", str(archive_file), str(extract_dest), "-y"]
            if pwd:
                cmd.insert(2, f"-p{pwd}")
            cmd.append("-ibck+")
            
            # Run extraction
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            # Wait for completion
            process.wait()
            success = process.returncode == 0
            
            return success
            
        except Exception as e:
            self.parent.after(0, lambda: self.status_message(f"Error extracting {group_name}: {str(e)}", "red"))
            return False
    
    def run_sequential_extraction(self):
        """Run sequential extraction for all archive groups"""
        try:
            # Clear log at start
            self.parent.after(0, self.clear_status)
            
            groups = get_archive_groups_status()
            
            if not groups:
                # No archive groups, fall back to single archive extraction
                self.parent.after(0, lambda: self.status_label.config(text="No archive groups found, extracting single archive...", foreground="blue"))
                self.run_extraction()
                return
            
            total_groups = len(groups)
            completed_groups = 0
            
            self.parent.after(0, lambda: self.status_message(f"Starting sequential extraction of {total_groups} archive groups...", "blue"))
            
            # Sort groups to process main game first, then optional
            sorted_groups = sorted(groups.items(), key=lambda x: (not x[1].get('is_optional', False), x[0]))
            
            for group_key, group_data in sorted_groups:
                group_name = group_data.get('base_name', 'Unknown')
                downloaded_parts = group_data.get('downloaded_parts', [])
                
                if not downloaded_parts:
                    self.parent.after(0, lambda gn=group_name: self.status_message(f"⏭️ Skipping group '{gn}' - no downloaded parts", "gray"))
                    continue
                
                # Find the first archive file in the download directory
                archive_file = None
                for part_num in sorted(downloaded_parts):
                    filename = group_data.get('filenames', {}).get(str(part_num))
                    if filename:
                        potential_file = Path(self.dest_path.get()) / filename
                        if potential_file.exists():
                            archive_file = potential_file
                            break
                
                if not archive_file:
                    self.parent.after(0, lambda gn=group_name: self.status_message(f"⚠️ Skipping group '{gn}' - no archive files found", "orange"))
                    continue
                
                completed_groups += 1
                self.parent.after(0, lambda gn=group_name, cg=completed_groups, tg=total_groups: 
                    self.status_label.config(text=f"Extracting group {cg}/{tg}: {gn}", foreground="blue"))
                self.parent.after(0, lambda gn=group_name: self.status_message(f"🗜️ Extracting group '{gn}'...", "blue"))
                
                # Extract this group
                success = self.extract_archive_group(archive_file, group_name)
                
                if success:
                    self.parent.after(0, lambda gn=group_name: self.status_message(f"✅ Successfully extracted group '{gn}'", "green"))
                else:
                    self.parent.after(0, lambda gn=group_name: self.status_message(f"❌ Failed to extract group '{gn}' - continuing to next group", "red"))
                
                # Update progress
                progress_percent = int((completed_groups / total_groups) * 100)
                self.parent.after(0, lambda p=progress_percent: self.progress.config(value=p))
                self.parent.after(0, lambda p=progress_percent: self.progress_label.config(text=f"{p}%"))
            
            # All groups processed
            self.parent.after(0, lambda: self.status_message(f"🏁 Sequential extraction completed. Processed {completed_groups}/{total_groups} groups.", "blue"))
            self.parent.after(0, lambda: self.extraction_finished(True))
            
        except Exception as e:
            self.parent.after(0, lambda: self.status_message(f"💥 Error in sequential extraction: {str(e)}", "red"))
            self.parent.after(0, lambda: self.extraction_finished(False))
    
    def extract_archive_group(self, archive_file, group_name):
        """Extract a single archive group"""
        try:
            exe = self.available_tools["winrar"]
            dest = self.dest_path.get()
            pwd = self.password.get()
            
            # Create folder based on group name
            folder_name = self.clean_archive_name(group_name)
            extract_dest = Path(dest) / folder_name
            extract_dest.mkdir(exist_ok=True)
            
            # Build WinRAR command
            cmd = [exe, "x", str(archive_file), str(extract_dest), "-y"]
            if pwd:
                cmd.insert(2, f"-p{pwd}")
            cmd.append("-ibck+")
            
            # Run extraction
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            # Wait for completion
            process.wait()
            success = process.returncode == 0
            
            return success
            
        except Exception as e:
            self.parent.after(0, lambda: self.status_message(f"Error extracting {group_name}: {str(e)}", "red"))
            return False
    
    def run_extraction(self, wait_for_completion=True):
        archive = self.archive_path.get()
        dest = self.dest_path.get()
        pwd = self.password.get()
        
        exe = self.available_tools["winrar"]  # Only WinRAR now
        
        # Create folder based on archive name without numbering
        archive_name = Path(archive).stem  # Get filename without extension
        folder_name = self.clean_archive_name(archive_name)
        extract_dest = Path(dest) / folder_name
        extract_dest.mkdir(exist_ok=True)
        
        # Build WinRAR command
        cmd = [exe, "x", archive, str(extract_dest), "-y"]  # -y for yes to all prompts
        if pwd:
            cmd.insert(2, f"-p{pwd}")
        # Add -ibck+ to prevent background button and keep window on top
        cmd.append("-ibck+")

        try:
            # Show WinRAR progress window
            self.extraction_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
        except Exception as e:
            if wait_for_completion:
                self.parent.after(0, lambda: messagebox.showerror("Error", f"Cannot run {exe}: {e}"))
                self.parent.after(0, self.extraction_finished, False)
            return None

        # Wait for extraction to complete (no progress parsing for WinRAR)
        if self.extraction_process and wait_for_completion:
            self.extraction_process.wait()

            # Extraction finished
            success = self.extraction_process.returncode == 0
            self.extraction_process = None
            self.parent.after(0, self.extraction_finished, success, extract_dest)
        elif self.extraction_process:
            # For sequential mode, don't wait - return process for async handling
            return self.extraction_process
        else:
            # Process was not created successfully
            if wait_for_completion:
                self.parent.after(0, self.extraction_finished, False, extract_dest)
            return None
    
    def clean_archive_name(self, archive_name):
        """Remove numbering and clean up archive name for folder creation"""
        import re
        
        # Remove common numbering patterns
        name = archive_name
        
        # Remove .part001, .part01, _part001, _part01, etc.
        name = re.sub(r'[._]part\d+$', '', name, flags=re.IGNORECASE)
        
        # Remove just numbers at the end if they look like part numbers
        name = re.sub(r'\d+$', '', name)
        
        # Clean up any remaining special characters and spaces
        name = re.sub(r'[._]+', ' ', name)  # Replace dots and underscores with spaces
        name = re.sub(r'\s+', ' ', name)   # Replace multiple spaces with single space
        name = name.strip()               # Remove leading/trailing spaces
        
        # If name is empty after cleaning, use a default
        if not name:
            name = "Extracted_Archive"
            
        return name

    def extraction_finished(self, success, extract_dest=None):
        self.extract_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.bring_to_front_btn.config(state="disabled")
        self.extraction_process = None
        if success:
            self.progress["value"] = 100
            self.progress_label.config(text="100%")
            folder_name = extract_dest.name if extract_dest else "archive"
            self.status_label.config(text=f"✅ Extraction completed: {folder_name}", foreground="green")
            messagebox.showinfo("Done", f"Extraction completed successfully!\n\nExtracted to:\n{extract_dest}")
        else:
            self.status_label.config(text="❌ Extraction failed", foreground="red")
            # Remove the error popup - just update status

    def cleanup(self):
        """Clean up extraction process - called when main app closes"""
        if self.extraction_process and self.extraction_process.poll() is None:
            try:
                self.extraction_process.terminate()
                self.extraction_process.wait(timeout=5)  # Wait up to 5 seconds
            except:
                try:
                    self.extraction_process.kill()  # Force kill if terminate doesn't work
                except:
                    pass
        
        self.extraction_process = None

    def check_downloads_and_extract(self):
        """Check if all downloads are complete and 100%, then open Smart Manager"""
        if not self.unrar_after_download.get() or not self.main_app:
            return
        
        try:
            groups = get_archive_groups_status()
            if not groups:
                return
            
            all_complete = True
            for group_key, group_data in groups.items():
                completion_pct = group_data.get('completion_percentage', 0)
                if completion_pct < 100.0:
                    all_complete = False
                    break
            
            if all_complete:
                self.auto_status_label.config(text="All downloads complete! Opening Smart Manager...", foreground="green")
                # Open Smart Manager automatically and start scanning
                self.parent.after(2000, self._open_smart_manager_auto)
            else:
                self.auto_status_label.config(text="Waiting for downloads to complete...", foreground="orange")
                
        except Exception as e:
            print(f"Error checking download completion: {e}")
    
    def _open_smart_manager_auto(self):
        """Open Smart Manager automatically and start scanning"""
        try:
            # Check if Smart Manager is already open
            if hasattr(self, 'smart_manager_window') and self.smart_manager_window and self.smart_manager_window.winfo_exists():
                # Focus existing Smart Manager
                self.smart_manager_window.lift()
                self.smart_manager_window.focus_force()
                self.smart_manager_window.attributes('-topmost', True)
                self.smart_manager_window.after(2000, lambda: self.smart_manager_window.attributes('-topmost', False))
                
                # Start scanning if not already scanning
                if hasattr(self, 'smart_manager') and self.smart_manager:
                    if not self.smart_manager.auto_scan_enabled.get():
                        self.smart_manager.auto_scan_enabled.set(True)
                        self.smart_manager.auto_scan_worker()
                    else:
                        # Trigger a scan
                        self.smart_manager_window.after(1000, self.smart_manager.scan_folder)
                
                # Update status
                self.auto_status_label.config(text="Focused existing Smart Manager for auto-extraction...", foreground="green")
            else:
                # Create Smart Manager window as a top-level window (not tied to specific tab)
                smart_window = tk.Toplevel()
                smart_window.title("🧠 Smart Download Folder Manager - Auto Extraction")
                smart_window.geometry("1000x730")
                
                # Make it always on top initially
                smart_window.attributes('-topmost', True)
                smart_window.lift()
                smart_window.focus_force()
                
                # Create Smart Manager instance
                smart_manager = SmartFolderManager(smart_window)
                smart_manager.frame.pack(fill="both", expand=True)
                
                # Link the delete checkboxes
                smart_manager.delete_after_extract.set(self.delete_after_extract.get())
                self.delete_after_extract.trace('w', lambda *args: smart_manager.delete_after_extract.set(self.delete_after_extract.get()))
                smart_manager.delete_after_extract.trace('w', lambda *args: self.delete_after_extract.set(smart_manager.delete_after_extract.get()))
                
                # Set the download folder to match extractor destination
                if self.dest_path.get():
                    smart_manager.download_folder.set(self.dest_path.get())
                
                # Auto-start scanning and enable auto-scan
                smart_window.after(1000, smart_manager.scan_folder)
                smart_manager.auto_scan_enabled.set(True)
                smart_manager.auto_scan_worker()  # Start auto-scan
                
                # Remove topmost after a delay to allow normal window behavior
                smart_window.after(3000, lambda: smart_window.attributes('-topmost', False))
                
                # Store references
                self.smart_manager_window = smart_window
                self.smart_manager = smart_manager
                
                # Handle window closing
                def on_closing():
                    self.smart_manager_window.destroy()
                    self.smart_manager_window = None
                    self.smart_manager = None
                    
                smart_window.protocol("WM_DELETE_WINDOW", on_closing)
                
                # Update status
                self.auto_status_label.config(text="Smart Manager opened and scanning for extractions...", foreground="green")
            
        except Exception as e:
            print(f"Error opening Smart Manager: {e}")
            self.auto_status_label.config(text="Error opening Smart Manager", foreground="red")
    
    def validate_multi_part_archive(self, part_files):
        """Validate multi-part archive completeness using download URL count"""
        try:
            # Sort files to find the first part
            part_files.sort(key=lambda f: f.name.lower())
            first_file = part_files[0]
            
            # Extract the base name and pattern
            first_name = first_file.name.lower()
            
            # Determine the pattern type
            if 'part001' in first_name:
                pattern_type = 'part001'
                base_name = first_name.replace('part001', '').replace('.rar', '')
            elif 'part01' in first_name:
                pattern_type = 'part01'
                base_name = first_name.replace('part01', '').replace('.rar', '')
            elif 'part1' in first_name:
                pattern_type = 'part1'
                base_name = first_name.replace('part1', '').replace('.rar', '')
            elif 'part0001' in first_name:
                pattern_type = 'part0001'
                base_name = first_name.replace('part0001', '').replace('.rar', '')
            else:
                # Unknown pattern, assume single file
                return first_file, []
            
            # Find all existing parts
            existing_parts = set()
            for file in part_files:
                name = file.name.lower()
                if pattern_type == 'part001' and 'part001' in name:
                    num = name.replace(base_name).replace('part', '').replace('.rar', '')
                    if num.isdigit():
                        existing_parts.add(int(num))
                elif pattern_type == 'part01' and 'part01' in name:
                    num = name.replace(base_name).replace('part', '').replace('.rar', '')
                    if num.isdigit():
                        existing_parts.add(int(num))
                elif pattern_type == 'part1' and 'part1' in name:
                    num = name.replace(base_name).replace('part', '').replace('.rar', '')
                    if num.isdigit():
                        existing_parts.add(int(num))
                elif pattern_type == 'part0001' and 'part0001' in name:
                    num = name.replace(base_name).replace('part', '').replace('.rar', '')
                    if num.isdigit():
                        existing_parts.add(int(num))
            
            if not existing_parts:
                return None, []
            
            # Get expected total from main app's download list
            expected_total = self.get_expected_archive_count()
            
            if expected_total > 0:
                # Use the download URL count as expected total
                expected_parts = set(range(1, expected_total + 1))
                print(f"Expected {expected_total} parts based on download URLs")
            else:
                # Fallback: use highest found part as total
                max_part = max(existing_parts)
                expected_parts = set(range(1, max_part + 1))
                print(f"Expected {max_part} parts based on highest found part")
            
            # Find missing parts
            missing_parts = expected_parts - existing_parts
            
            # Format missing part names
            missing_names = []
            for part_num in sorted(missing_parts):
                if pattern_type == 'part001':
                    missing_names.append(f"part{part_num:03d}")
                elif pattern_type == 'part01':
                    missing_names.append(f"part{part_num:02d}")
                elif pattern_type == 'part1':
                    missing_names.append(f"part{part_num}")
                elif pattern_type == 'part0001':
                    missing_names.append(f"part{part_num:04d}")
            
            return first_file, missing_names
            
        except Exception as e:
            print(f"Error validating multi-part archive: {e}")
            return part_files[0] if part_files else None, []
    
    def get_expected_archive_count(self):
        """Get expected number of archives from main app's download list"""
        try:
            if self.main_app and hasattr(self.main_app, 'links'):
                # Count URLs that look like archive downloads
                archive_urls = []
                for url in self.main_app.links:
                    if any(host in url.lower() for host in ['fuckingfast.co', 'filehoster', 'download']):
                        archive_urls.append(url)
                
                return len(archive_urls)
            return 0
        except Exception as e:
            print(f"Error getting expected archive count: {e}")
            return 0

    def auto_extract(self, archive_file):
        """Automatically extract archive"""
        try:
            # Check if WinRAR is available
            if "winrar" not in self.available_tools:
                self.parent.after(0, lambda: self.auto_status_label.config(
                    text="❌ WinRAR not available", foreground="red"))
                return
            
            # Set up extraction
            self.progress["value"] = 0
            self.progress_label.config(text="0%")
            self.extract_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.bring_to_front_btn.config(state="normal")
            
            # Use the same extraction logic as manual extraction
            exe = self.available_tools["winrar"]
            dest = self.dest_path.get()
            pwd = self.password.get()
            
            # Create folder based on archive name
            archive_name = Path(archive_file).stem
            folder_name = self.clean_archive_name(archive_name)
            extract_dest = Path(dest) / folder_name
            extract_dest.mkdir(exist_ok=True)
            
            # Build WinRAR command
            cmd = [exe, "x", str(archive_file), str(extract_dest), "-y"]
            if pwd:
                cmd.insert(2, f"-p{pwd}")
            cmd.append("-ibck+")
            
            # Update status
            self.parent.after(0, lambda: self.auto_status_label.config(
                text=f"Extracting {archive_name}...", foreground="blue"))
            
            # Run extraction
            self.extraction_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            # Wait for completion
            if self.extraction_process:
                self.extraction_process.wait()
                success = self.extraction_process.returncode == 0
                self.extraction_process = None
                
                # Update UI based on result
                if success:
                    self.parent.after(0, lambda: self.auto_status_label.config(
                        text=f"✅ Extracted: {folder_name}", foreground="green"))
                    self.parent.after(0, lambda: self.extraction_finished(success, extract_dest))
                else:
                    self.parent.after(0, lambda: self.auto_status_label.config(
                        text="❌ Extraction failed", foreground="red"))
                    self.parent.after(0, lambda: self.extraction_finished(success))
            else:
                self.parent.after(0, lambda: self.auto_status_label.config(
                    text="❌ Failed to start extraction", foreground="red"))
                self.parent.after(0, lambda: self.extraction_finished(False))
                
        except Exception as e:
            self.parent.after(0, lambda: self.auto_status_label.config(
                text=f"❌ Error: {str(e)}", foreground="red"))
            self.parent.after(0, lambda: self.extraction_finished(False))

    def get_frame(self):
        return self.frame
    
    def create_context_menu(self, entry_widget):
        """Create right-click context menu for entry widgets"""
        context_menu = tk.Menu(entry_widget, tearoff=0)
        context_menu.add_command(label="Cut", command=lambda: self.cut_text(entry_widget))
        context_menu.add_command(label="Copy", command=lambda: self.copy_text(entry_widget))
        context_menu.add_command(label="Paste", command=lambda: self.paste_text(entry_widget))
        context_menu.add_separator()
        context_menu.add_command(label="Select All", command=lambda: self.select_all_text(entry_widget))
        
        def show_context_menu(event):
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        
        entry_widget.bind("<Button-3>", show_context_menu)
    
    def cut_text(self, entry_widget):
        """Cut selected text from entry widget"""
        try:
            if entry_widget.selection_present():
                start = entry_widget.index(tk.SEL_FIRST)
                end = entry_widget.index(tk.SEL_LAST)
                selected_text = entry_widget.get(start, end)
                entry_widget.delete(start, end)
                self.parent.clipboard_clear()
                self.parent.clipboard_append(selected_text)
        except:
            pass
    
    def copy_text(self, entry_widget):
        """Copy selected text from entry widget"""
        try:
            if entry_widget.selection_present():
                start = entry_widget.index(tk.SEL_FIRST)
                end = entry_widget.index(tk.SEL_LAST)
                selected_text = entry_widget.get(start, end)
                self.parent.clipboard_clear()
                self.parent.clipboard_append(selected_text)
        except:
            pass
    
    def paste_text(self, entry_widget):
        """Paste text from clipboard to entry widget"""
        try:
            clipboard_text = self.parent.clipboard_get()
            if entry_widget.selection_present():
                start = entry_widget.index(tk.SEL_FIRST)
                end = entry_widget.index(tk.SEL_LAST)
                entry_widget.delete(start, end)
            entry_widget.insert(tk.INSERT, clipboard_text)
        except:
            pass
    
    def select_all_text(self, entry_widget):
        """Select all text in entry widget"""
        try:
            entry_widget.select_range(0, tk.END)
        except:
            pass
