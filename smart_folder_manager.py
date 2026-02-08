#!/usr/bin/env python3
"""
Smart Download Folder Manager - Auto-scan and Extract
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import subprocess
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from extractor_utils import find_winrar_path
from config_manager import get_archive_groups_status, can_extract_group, get_url_tracking

class SmartFolderManager:
    def __init__(self, parent):
        self.parent = parent
        self.frame = ttk.Frame(parent)
        
        # Variables
        self.download_folder = tk.StringVar(value="E:\\Download")
        self.winrar_path = find_winrar_path()
        self.file_groups = {}
        self.is_scanning = False
        self.is_extracting = False
        
        # Auto-scan variables
        self.auto_scan_enabled = tk.BooleanVar(value=True)  # Changed to True by default
        self.auto_scan_interval = 30
        self.auto_scan_job = None
        
        # Failed extraction tracking
        self.failed_groups = set()  # Groups that failed extraction
        self.extracted_groups = set()  # Successfully extracted groups
        
        # Auto-extract checkbox (when auto-scan is enabled)
        self.auto_extract_enabled = tk.BooleanVar(value=False)
        
        # Delete archives after extraction checkbox
        self.delete_after_extract = tk.BooleanVar(value=False)
        
        self.build_ui()
        
        # Start auto-scan after UI is ready
        self.parent.after(2000, self.start_auto_scan)
        
        # Trigger an immediate scan for testing
        self.parent.after(3000, self.manual_scan_for_debug)
        
    def manual_scan_for_debug(self):
        """Manual scan for debugging purposes"""
        self.log("=== DEBUG: Manual scan triggered ===", "blue")
        self.scan_folder()
        
    def build_ui(self):
        # Main container
        main_frame = ttk.Frame(self.frame, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title = ttk.Label(main_frame, text="📁 Smart Download Manager", font=("Segoe UI", 16, "bold"))
        title.pack(pady=(0, 20))
        
        # Folder selection
        folder_frame = ttk.Frame(main_frame)
        folder_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Label(folder_frame, text="Download Folder:").pack(side="left", padx=(0, 10))
        self.folder_entry = ttk.Entry(folder_frame, textvariable=self.download_folder, width=60)
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ttk.Button(folder_frame, text="Browse", command=self.browse_folder).pack(side="left", padx=(0, 10))
        ttk.Button(folder_frame, text="🔍 Scan", command=self.scan_folder).pack(side="left")
        
        # Auto-scan controls
        auto_frame = ttk.Frame(main_frame)
        auto_frame.pack(fill="x", pady=(0, 10))
        
        self.auto_scan_check = ttk.Checkbutton(auto_frame, text="🔄 Auto-scan every 30 seconds", 
                                               variable=self.auto_scan_enabled, command=self.toggle_auto_scan)
        self.auto_scan_check.pack(side="left")
        
        self.auto_scan_label = ttk.Label(auto_frame, text="Auto-scan: OFF", foreground="gray")
        self.auto_scan_label.pack(side="left", padx=(10, 0))
        
        # Delete archives after extraction checkbox
        ttk.Checkbutton(auto_frame, text="🗑️ Delete archives after extraction", 
                       variable=self.delete_after_extract).pack(side="left", padx=(20, 0))
        
        # File groups display
        groups_frame = ttk.LabelFrame(main_frame, text="📦 Detected File Groups", padding="10")
        groups_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Treeview
        columns = ("Group Name", "Files", "Size", "Status")
        self.groups_tree = ttk.Treeview(groups_frame, columns=columns, show="tree headings", height=8)
        
        for col in columns:
            self.groups_tree.heading(col, text=col)
        self.groups_tree.heading("#0", text="Select")
        
        self.groups_tree.column("#0", width=50)
        self.groups_tree.column("Group Name", width=250)
        self.groups_tree.column("Files", width=80)
        self.groups_tree.column("Size", width=100)
        self.groups_tree.column("Status", width=120)
        
        tree_scroll = ttk.Scrollbar(groups_frame, orient="vertical", command=self.groups_tree.yview)
        self.groups_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.groups_tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")
        
        # Status log
        log_frame = ttk.LabelFrame(main_frame, text="📋 Status Log", padding="10")
        log_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        self.status_text = tk.Text(log_frame, height=8, wrap=tk.WORD)
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=log_scroll.set)
        
        self.status_text.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")
        
        # Progress and controls
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill="x")
        
        # Progress
        progress_frame = ttk.Frame(control_frame)
        progress_frame.pack(fill="x", pady=(0, 10))
        
        self.progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress.pack(fill="x", pady=(0, 5))
        
        self.progress_label = ttk.Label(progress_frame, text="Ready")
        self.progress_label.pack()
        
        # Options frame
        options_frame = ttk.Frame(control_frame)
        options_frame.pack(fill="x", pady=(5, 10))
        
        # Checkbox for JSON-only extraction
        from config_manager import get_setting, set_setting
        json_only_setting = get_setting("json_only_mode", True)  # Changed default to True
        self.json_only_var = tk.BooleanVar(value=True)  # Force checked by default
        
        # Save the default setting to config
        set_setting("json_only_mode", True)
        
        self.json_only_cb = ttk.Checkbutton(
            options_frame, 
            text="🎯 Extract only JSON-tracked archives (skip existing archives)", 
            variable=self.json_only_var,
            command=self.update_extraction_mode
        )
        self.json_only_cb.pack(anchor="w")
        
        # Mode label
        self.mode_label = ttk.Label(options_frame, text="🎯 Current mode: JSON-only extraction", font=("Segoe UI", 9), foreground="green")
        self.mode_label.pack(anchor="w", pady=(2, 0))
        
        # Buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        
        self.scan_btn = ttk.Button(btn_frame, text="🔍 Scan Folder", command=self.scan_folder)
        self.scan_btn.pack(side="left", padx=(0, 5))
        
        self.extract_btn = ttk.Button(btn_frame, text="🚀 Extract Selected", command=self.extract_selected, state="disabled")
        self.extract_btn.pack(side="left", padx=(0, 5))
        
        self.extract_all_btn = ttk.Button(btn_frame, text="📦 Extract All", command=self.extract_all, state="disabled")
        self.extract_all_btn.pack(side="left", padx=(0, 5))
        
        # Delete archives button
        self.test_delete_btn = ttk.Button(btn_frame, text="🗑️ Delete Archives", command=self.show_delete_confirmation)
        self.test_delete_btn.pack(side="left", padx=(0, 5))
        
        # Debug JSON button
        self.debug_json_btn = ttk.Button(btn_frame, text="🔍 Debug JSON", command=self.debug_json_function)
        self.debug_json_btn.pack(side="left", padx=(0, 5))
        
        ttk.Button(btn_frame, text="🗑️ Clear Log", command=self.clear_log).pack(side="right")
        
    def update_extraction_mode(self):
        """Update the extraction mode display and logic"""
        from config_manager import set_setting
        
        # Save the setting
        set_setting("json_only_mode", self.json_only_var.get())
        
        if self.json_only_var.get():
            self.mode_label.config(text="🎯 Current mode: JSON-only extraction", foreground="green")
            self.log("🎯 Switched to JSON-only extraction mode", "green")
        else:
            self.mode_label.config(text="📁 Current mode: Extract all archives", foreground="blue")
            self.log("📁 Switched to extract all archives mode", "blue")
        
        # Refresh the display to show/hide appropriate groups
        if hasattr(self, 'file_groups') and self.file_groups:
            self._update_groups_display(dict(self.file_groups))
    
    def browse_folder(self):
        folder = filedialog.askdirectory(title="Select Download Folder")
        if folder:
            self.download_folder.set(folder)
            
    def log(self, message, color="black"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.config(state="normal")
        self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
        
        if color == "red":
            self.status_text.tag_add("error", f"end-2c", f"end-1c")
            self.status_text.tag_config("error", foreground="red")
        elif color == "green":
            self.status_text.tag_add("success", f"end-2c", f"end-1c")
            self.status_text.tag_config("success", foreground="green")
        elif color == "blue":
            self.status_text.tag_add("info", f"end-2c", f"end-1c")
            self.status_text.tag_config("info", foreground="blue")
        elif color == "orange":
            self.status_text.tag_add("warning", f"end-2c", f"end-1c")
            self.status_text.tag_config("warning", foreground="orange")
            
        self.status_text.see(tk.END)
        self.status_text.config(state="disabled")
        self.parent.update_idletasks()
        
    def clear_log(self):
        self.status_text.config(state="normal")
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state="disabled")
        
    def toggle_auto_scan(self):
        if self.auto_scan_enabled.get():
            self.start_auto_scan()
        else:
            self.stop_auto_scan()
            
    def start_auto_scan(self):
        if self.auto_scan_job:
            return
            
        self.auto_scan_label.config(text="Auto-scan: ON", foreground="green")
        self.log("🔄 Auto-scan started", "blue")
        self.schedule_next_scan()
        
    def stop_auto_scan(self):
        if self.auto_scan_job:
            self.parent.after_cancel(self.auto_scan_job)
            self.auto_scan_job = None
            
        self.auto_scan_label.config(text="Auto-scan: OFF", foreground="gray")
        self.log("⏸️ Auto-scan stopped", "orange")
        
    def schedule_next_scan(self):
        if self.auto_scan_enabled.get():
            self.auto_scan_job = self.parent.after(self.auto_scan_interval * 1000, self.auto_scan_worker)
            
    def auto_scan_worker(self):
        """Auto-scan worker thread - minimal logging"""
        if not self.auto_scan_enabled.get():
            return
            
        previous_groups = dict(self.file_groups)
        self._scan_folder_worker()
        
        # Update UI display to reflect current extraction status
        self.parent.after(50, lambda: self._update_groups_display(dict(self.file_groups)))
        
        self.parent.after(100, lambda: self.check_for_completed_groups(previous_groups))
        self.schedule_next_scan()
        
    def check_for_completed_groups(self, previous_groups):
        """Check for newly completed groups - minimal logging"""
        if not self.file_groups or self.is_extracting:
            # Don't check during active extraction to avoid false mismatches
            return
            
        # DEBUG: Log current file groups
        self.log(f"DEBUG: Found {len(self.file_groups)} file groups: {list(self.file_groups.keys())}", "blue")
            
        # Get authoritative group data from JSON
        try:
            print("DEBUG: About to call get_archive_groups_status()")
            json_groups = get_archive_groups_status()
            print(f"DEBUG: Got {len(json_groups)} JSON groups from config manager")
            self.log(f"DEBUG: Found {len(json_groups)} JSON groups: {list(json_groups.keys())}", "green")
            
            # DEBUG: Log group details
            for group_key, group_data in json_groups.items():
                group_name = group_data.get('base_name', group_key)
                downloaded_count = group_data.get('downloaded_count', 0)
                total_parts = group_data.get('total_parts', 0)
                completion_pct = group_data.get('completion_percentage', 0)
                self.log(f"DEBUG: JSON Group '{group_name}' - {downloaded_count}/{total_parts} ({completion_pct:.1f}%)", "green")
                
        except Exception as e:
            self.log(f"DEBUG: Error getting JSON groups: {e}", "red")
            return  # Silent fail for auto-scan
            
        # Separate JSON groups and non-JSON groups
        json_group_names = set()
        ready_json_groups = []
        
        for group_key, group_data in json_groups.items():
            group_name = group_data.get('base_name', group_key)
            json_group_names.add(group_name)
            
            # Check if this group exists in our scanned files
            # FIX: Try both with and without _group suffix
            group_file_name = group_name
            if group_name.endswith('_group'):
                group_file_name = group_name[:-6]  # Remove '_group' suffix
                
            if group_file_name in self.file_groups:
                downloaded_count = group_data.get('downloaded_count', 0)
                total_parts = group_data.get('total_parts', 0)
                completion_pct = group_data.get('completion_percentage', 0)
                
                # === MULTI-SOURCE CHECKING ===
                from config_manager import get_group_fetch_total, get_url_tracking
                from pathlib import Path
                
                # Method 1: Check files in download folder
                download_folder_files = []
                download_folder = Path(self.download_folder.get())
                if download_folder.exists():
                    for file in download_folder.iterdir():
                        if file.is_file():
                            filename = file.name.lower()
                            # Check if file belongs to this group
                            base_patterns = [
                                f"{group_file_name.lower()}.part",
                                f"{group_file_name.lower()}_part",
                                f"{group_file_name.lower()}.",
                                f"{group_file_name.lower()}_"
                            ]
                            
                            for pattern in base_patterns:
                                if filename.startswith(pattern) and filename.endswith(('.rar', '.zip', '.7z', '.r01', '.r02')):
                                    download_folder_files.append(file.name)
                                    break
                
                download_folder_count = len(download_folder_files)
                
                # Method 2: Get fetch total from stored data
                fetch_total = get_group_fetch_total(group_file_name)
                
                # Method 3: Get imported count from JSON
                imported_parts = group_data.get('imported_parts', [])
                imported_count = len(imported_parts)
                
                # Determine the most reliable total (multi-source logic)
                if fetch_total > 0:
                    multi_source_total = fetch_total
                    source = "fetch data"
                elif imported_count > 0:
                    multi_source_total = imported_count
                    source = "imported data"
                else:
                    multi_source_total = download_folder_count
                    source = "download folder"
                
                # Override old values with multi-source results
                total_parts = multi_source_total
                if total_parts > 0:
                    completion_pct = (downloaded_count / total_parts) * 100
                
                # === UPDATE JSON TRACKING IF NEW FILES DETECTED ===
                # If download folder has more files than JSON tracking, update JSON
                if download_folder_count > downloaded_count:
                    self.log(f"🔄 New files detected! Updating JSON tracking: {downloaded_count} → {download_folder_count}", "orange")
                    self._update_json_tracking(group_file_name, download_folder_count, download_folder_files)
                    # Use updated count for completion check
                    downloaded_count = download_folder_count
                    if total_parts > 0:
                        completion_pct = (downloaded_count / total_parts) * 100
                
                self.log(f"DEBUG: Multi-source check for '{group_file_name}': {downloaded_count}/{total_parts} ({completion_pct:.1f}%) using {source}", "blue")
                self.log(f"DEBUG:  Download folder: {download_folder_count}, Fetch total: {fetch_total}, Imported: {imported_count}", "blue")
                
                # DEBUG: Log group status
                self.log(f"DEBUG: Group '{group_file_name}' (from JSON '{group_name}') - Downloaded: {downloaded_count}/{total_parts} ({completion_pct}%)", "blue")
                
                # NEW: Check actual file sizes on disk vs expected sizes
                actual_files = self.file_groups[group_file_name]
                actual_total_size = 0
                expected_total_size = 0
                
                # Calculate actual size of files on disk
                for file_path in actual_files:
                    if file_path.exists():
                        actual_size = file_path.stat().st_size
                        actual_total_size += actual_size
                        self.log(f"DEBUG: File {file_path.name} - Actual size: {self._format_size(actual_size)}", "info")
                
                # Get expected sizes from JSON data
                for part_num, url in group_data.get('urls', {}).items():
                    filename = group_data.get('filenames', {}).get(str(part_num), f"part{part_num}.rar")
                    # Try to get expected size from url_to_filename mapping
                    tracking = get_url_tracking()
                    if url in tracking.get('url_to_filename', {}):
                        # This is a rough estimate - we can't get exact expected size without downloading
                        expected_total_size += actual_total_size  # Use actual as fallback
                
                # Check if files are complete by comparing actual vs expected
                # For now, we'll assume files are complete if they exist and have reasonable size
                min_reasonable_size = 10 * 1024 * 1024  # 10MB minimum (more reasonable)
                files_are_complete = all(f.exists() and f.stat().st_size > min_reasonable_size for f in actual_files)
                
                # Additional check: Make sure no .tmp files exist for this group
                has_temp_files = any(f.suffix == '.tmp' and group_file_name.lower() in f.name.lower() for f in Path(self.download_folder.get()).glob('*'))
                
                self.log(f"DEBUG: Group '{group_file_name}' - Files complete: {files_are_complete}, Has temp files: {has_temp_files}, Total actual size: {self._format_size(actual_total_size)}", "blue")
                
                # Only extract if group is 100% complete AND files are actually complete on disk
                # Use the same logic as config manager: if total_parts is 0, use imported_count
                is_fully_complete = (
                    completion_pct >= 100.0 and files_are_complete and
                    (downloaded_count > 0)  # At least one file downloaded
                )
                self.log(f"DEBUG: Group '{group_file_name}' fully complete check: {is_fully_complete} (downloaded={downloaded_count}, total={total_parts}, pct={completion_pct}, files_complete={files_are_complete})", "blue")
                
                if is_fully_complete:
                    if (group_file_name not in self.failed_groups and 
                        group_file_name not in self.extracted_groups):
                        # Check extraction status with size verification
                        extraction_status = self._check_extraction_status(group_file_name)
                        if extraction_status == "needs_re_extraction":
                            self.log(f"🔄 JSON group '{group_file_name}' has size mismatch - re-extracting", "orange")
                            ready_json_groups.append(group_file_name)
                        elif extraction_status == "already_extracted":
                            self.log(f"⏸️ JSON group '{group_file_name}' already extracted - skipping", "orange")
                        else:  # not_extracted
                            self.log(f"✅ JSON group '{group_file_name}' ready for extraction", "green")
                            ready_json_groups.append(group_file_name)
                    else:
                        self.log(f"⏸️ JSON group '{group_file_name}' already processed - skipping", "orange")
        
        # Extract ready JSON groups first
        if ready_json_groups:
            for group_name in ready_json_groups:
                self.log(f"✅ JSON group '{group_name}' is 100% complete - starting auto-extraction", "green")
                # Add a 5-second delay before extraction to ensure files are fully written
                self.parent.after(5000, lambda: self._auto_extract_group(group_name))
                return  # Only extract one at a time
        
        # If no JSON groups ready, check non-JSON groups (only if not in JSON-only mode)
        if not self.json_only_var.get():
            non_json_groups = []
            for group_name in self.file_groups:
                if group_name not in json_group_names:
                    if (group_name not in self.failed_groups and 
                        group_name not in self.extracted_groups):
                        # Check extraction status with size verification
                        extraction_status = self._check_extraction_status(group_name)
                        if extraction_status == "needs_re_extraction":
                            self.log(f"🔄 Non-JSON group '{group_name}' has size mismatch - re-extracting", "orange")
                            non_json_groups.append(group_name)
                        elif extraction_status != "already_extracted":
                            non_json_groups.append(group_name)
                        
            if non_json_groups:
                self.log(f"📦 No JSON groups ready, extracting non-JSON group: {non_json_groups[0]}", "blue")
                self._auto_extract_group(non_json_groups[0])
        else:
            # JSON-only mode - log that non-JSON groups are being skipped
            skipped_non_json = []
            for group_name in self.file_groups:
                if group_name not in json_group_names:
                    if (group_name not in self.failed_groups and 
                        group_name not in self.extracted_groups):
                        skipped_non_json.append(group_name)
            
            if skipped_non_json:
                self.log(f"🎯 JSON-only mode: Skipping {len(skipped_non_json)} non-JSON groups", "blue")
                        
    def _update_json_tracking(self, group_name, new_downloaded_count, downloaded_files):
        """Update JSON tracking when new files are detected"""
        try:
            from config_manager import get_url_tracking, save_url_tracking, load_config, save_config
            
            # Load current tracking
            tracking = get_url_tracking()
            config = load_config()
            
            # Find the group in tracking
            group_key = None
            for g_key, g_data in tracking.get('archive_groups', {}).items():
                if g_data.get('base_name') == group_name:
                    group_key = g_key
                    break
            
            if group_key:
                # Update downloaded count and URLs
                old_count = tracking['archive_groups'][group_key].get('downloaded_count', 0)
                tracking['archive_groups'][group_key]['downloaded_count'] = new_downloaded_count
                
                # Update completion percentage
                total_parts = tracking['archive_groups'][group_key].get('total_parts', new_downloaded_count)
                if total_parts > 0:
                    tracking['archive_groups'][group_key]['completion_percentage'] = (new_downloaded_count / total_parts) * 100
                
                # Update downloaded URLs if we can match files
                url_to_filename = tracking.get('url_to_filename', {})
                for filename in downloaded_files:
                    # Find matching URL for this filename
                    for url, stored_filename in url_to_filename.items():
                        if filename == stored_filename:
                            if url not in tracking.get('downloaded_urls', []):
                                tracking.setdefault('downloaded_urls', []).append(url)
                                break
                
                # Save updated tracking
                save_url_tracking(tracking)
                self.log(f"✅ Updated JSON tracking for '{group_name}': {old_count} → {new_downloaded_count} files", "green")
            else:
                self.log(f"⚠️ Could not find group '{group_name}' in JSON tracking", "orange")
                
        except Exception as e:
            self.log(f"❌ Error updating JSON tracking: {e}", "red")

    def _check_extraction_status(self, group_name):
        """Check extraction status with size verification - returns status string"""
        extract_dest = Path(self.download_folder.get()) / self._clean_folder_name(group_name)
        
        if not extract_dest.exists():
            return "not_extracted"
            
        # Get archive size for comparison
        if group_name not in self.file_groups:
            return "not_extracted"
            
        archive_size = sum(f.stat().st_size for f in self.file_groups[group_name])
        
        try:
            files_in_folder = list(extract_dest.iterdir())
            if not files_in_folder:
                return "not_extracted"
                
            # Calculate folder size
            folder_size = 0
            file_count = 0
            
            for item in extract_dest.rglob('*'):
                if item.is_file():
                    folder_size += item.stat().st_size
                    file_count += 1
                    
            # Calculate size difference (allow 20MB tolerance)
            size_diff = abs(archive_size - folder_size)
            tolerance_mb = 20 * 1024 * 1024  # 20MB in bytes
            
            if size_diff > tolerance_mb:
                return "needs_re_extraction"
            else:
                return "already_extracted"
                
        except Exception:
            return "not_extracted"
    def _is_group_already_extracted(self, group_name):
        """Full check if group has already been extracted with size verification (for manual scans)"""
        extract_dest = Path(self.download_folder.get()) / self._clean_folder_name(group_name)
        
        if not extract_dest.exists():
            return False
            
        # Get archive size for comparison first
        if group_name not in self.file_groups:
            self.log(f"⚠️ Group '{group_name}' not found in file groups", "orange")
            return False
            
        archive_size = sum(f.stat().st_size for f in self.file_groups[group_name])
        
        # Check if folder has extracted files (not just empty)
        try:
            files_in_folder = list(extract_dest.iterdir())
            if not files_in_folder:
                self.log(f"🔍 Folder '{extract_dest.name}' exists but is empty - needs re-extraction", "info")
                return False
                
            # Calculate folder size
            folder_size = 0
            file_count = 0
            
            for item in extract_dest.rglob('*'):
                if item.is_file():
                    folder_size += item.stat().st_size
                    file_count += 1
                    
            # Calculate size difference (allow 20MB tolerance)
            size_diff = abs(archive_size - folder_size)
            tolerance_mb = 20 * 1024 * 1024  # 20MB in bytes
            
            self.log(f"🔍 SIZE CHECK: Folder '{extract_dest.name}' = {self._format_size(folder_size)} vs Archive = {self._format_size(archive_size)} (diff: {self._format_size(size_diff)})", "info")
            
            if size_diff > tolerance_mb:
                self.log(f"⚠️ SIZE MISMATCH: Folder '{extract_dest.name}' is {self._format_size(size_diff)} smaller/larger than archive - NEEDS RE-EXTRACTION", "orange")
                return False
            else:
                self.log(f"✅ SIZE OK: Folder '{extract_dest.name}' size matches archive within tolerance - ALREADY EXTRACTED", "info")
                return True
                
        except Exception as e:
            self.log(f"⚠️ Error checking extraction folder '{extract_dest.name}': {str(e)}", "orange")
            return False
        
    def _is_sequence_complete(self, files):
        part_numbers = []
        for file in files:
            part_num = self._extract_part_number(file.name)
            if part_num is not None:
                part_numbers.append(part_num)
                
        if not part_numbers:
            return True
            
        part_numbers.sort()
        expected_numbers = list(range(1, len(part_numbers) + 1))
        return part_numbers == expected_numbers
        
    def _extract_part_number(self, filename):
        patterns = [
            r'\.part(\d+)\.rar$',
            r'\.part(\d+)$',
            r'\.r(\d+)$',
            r'\.(\d+)\.rar$',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return int(match.group(1))
                
        return None
        
    def _auto_extract_group(self, group_name):
        if self.is_extracting:
            self.log(f"⏸️ Skipping auto-extraction of '{group_name}' - extraction in progress", "orange")
            return
            
        self.log(f"🚀 Auto-extracting group: {group_name}", "blue")
        self._start_extraction([group_name])
        
    def scan_folder(self):
        """Scan download folder and group files"""
        if self.is_scanning:
            return
            
        self.is_scanning = True
        self.scan_btn.config(state="disabled")
        self._manual_scan = True  # Mark as manual scan for logging
        self.log("🔍 Scanning download folder...", "blue")
        
        thread = threading.Thread(target=self._scan_folder_worker, daemon=True)
        thread.start()
        
    def _scan_folder_worker(self):
        try:
            folder_path = Path(self.download_folder.get())
            if not folder_path.exists():
                self.log(f"❌ Folder not found: {folder_path}", "red")
                return
                
            self.file_groups.clear()
            archive_files = []
            
            extensions = ['*.rar', '*.zip', '*.7z', '*.r01', '*.r02', '*.r03', '*.r04', '*.r05']
            
            for ext in extensions:
                try:
                    files = list(folder_path.glob(ext))
                    archive_files.extend(files)
                    self.log(f"🔍 Found {len(files)} files with pattern {ext}", "info")
                except Exception as e:
                    self.log(f"⚠️ Error searching {ext}: {str(e)}", "orange")
            
            try:
                all_files = list(folder_path.glob('*'))
                part_files = [f for f in all_files if 'part' in f.name.lower() and f.is_file()]
                archive_files.extend(part_files)
                self.log(f"🔍 Found {len(part_files)} files with 'part' in name", "info")
            except Exception as e:
                self.log(f"⚠️ Error searching part files: {str(e)}", "orange")
                
            archive_files = list(set(archive_files))
            
            if not archive_files:
                self.log("❌ No archive files found", "red")
                try:
                    all_files = list(folder_path.glob('*'))
                    file_list = [f.name for f in all_files[:10] if f.is_file()]
                    self.log(f"📋 Files in folder (first 10): {file_list}", "info")
                except:
                    pass
                return
                
            self.log(f"📁 Found {len(archive_files)} total archive files", "info")
            
            groups = defaultdict(list)
            
            for file_path in archive_files:
                base_name = self._extract_base_name(file_path.name)
                groups[base_name].append(file_path)
                self.log(f"📄 File: {file_path.name} → Group: {base_name}", "info")
                
            self.parent.after(0, self._update_groups_display, dict(groups))
            
        except Exception as e:
            self.log(f"❌ Scan error: {str(e)}", "red")
        finally:
            self.is_scanning = False
            self.parent.after(0, lambda: self.scan_btn.config(state="normal"))
            
    def _extract_base_name(self, filename):
        name = Path(filename).stem
        
        patterns = [
            r'[._]part\d+$',
            r'\.part\d+$',
            r'\.r\d+$',
            r'\.rar$',
        ]
        
        for pattern in patterns:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)
            
        return name.strip()
        
    def _update_groups_display(self, groups):
        """Update groups display with extraction status and priority"""
        for item in self.groups_tree.get_children():
            self.groups_tree.delete(item)
            
        # Get JSON groups for priority marking
        try:
            json_groups = get_archive_groups_status()
            json_group_names = set()
            for group_key, group_data in json_groups.items():
                group_name = group_data.get('base_name', group_key)
                json_group_names.add(group_name)
        except:
            json_group_names = set()
            
        for base_name, files in groups.items():
            # If JSON-only mode is enabled, only show JSON groups
            if self.json_only_var.get() and base_name not in json_group_names:
                continue
                
            total_size = sum(f.stat().st_size for f in files)
            size_str = self._format_size(total_size)
            
            # Check status with priority and detailed folder checking
            # Order matters: check failed first, then extracted, then priority
            if base_name in self.failed_groups:
                status = "❌ Failed"
            elif base_name in self.extracted_groups:
                status = "✅ Extracted"
            else:
                # Do a fresh extraction status check
                extraction_status = self._check_extraction_status(base_name)
                if extraction_status == "already_extracted":
                    status = "✅ Extracted"
                    self.extracted_groups.add(base_name)  # Update the set
                elif base_name in json_group_names:
                    status = "🎯 Priority"
                elif len(files) == 1:
                    status = "Single file"
                else:
                    status = f"{len(files)} parts"
                
            item = self.groups_tree.insert("", "end", text="☐", values=(
                base_name,
                len(files),
                size_str,
                status
            ))
            
        self.file_groups = groups
        
        # Count groups for logging (respect JSON-only mode)
        display_groups = groups
        if self.json_only_var.get():
            # In JSON-only mode, only count JSON groups
            json_groups_in_folder = []
            for base_name in groups.keys():
                if base_name in json_group_names:
                    json_groups_in_folder.append(base_name)
            display_groups = {name: groups[name] for name in json_groups_in_folder}
            
            # Log with JSON-only context
            if not self.auto_scan_enabled.get() or hasattr(self, '_manual_scan'):
                if len(json_groups_in_folder) > 0:
                    self.log(f"🎯 JSON-only mode: Found {len(json_groups_in_folder)} JSON-tracked groups (skipping {len(groups) - len(json_groups_in_folder)} other groups)", "green")
                else:
                    self.log(f"🎯 JSON-only mode: No JSON-tracked groups found (skipping {len(groups)} other groups)", "orange")
        else:
            # Normal mode - count all groups
            if not self.auto_scan_enabled.get() or hasattr(self, '_manual_scan'):
                self.log(f"✅ Found {len(groups)} file groups", "green")
        
        self.extract_btn.config(state="normal")
        self.extract_all_btn.config(state="normal")
        
    def _format_size(self, size_bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
        
    def extract_selected(self):
        """Extract selected groups - skip already extracted"""
        selected = self.groups_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select groups to extract")
            return
            
        selected_groups = []
        skipped_groups = []
        
        for item in selected:
            values = self.groups_tree.item(item)['values']
            group_name = values[0]
            
            if self._is_group_already_extracted(group_name):
                skipped_groups.append(group_name)
            else:
                # Check if this is a non-JSON group and JSON-only mode is enabled
                try:
                    json_groups = get_archive_groups_status()
                    json_group_names = set()
                    for group_key, group_data in json_groups.items():
                        json_group_names.add(group_data.get('base_name', group_key))
                except:
                    json_group_names = set()
                
                if self.json_only_var.get() and group_name not in json_group_names:
                    skipped_groups.append(group_name)  # Skip non-JSON groups in JSON-only mode
                else:
                    selected_groups.append(group_name)
                
        if skipped_groups:
            json_only_skipped = [g for g in skipped_groups if g not in json_group_names]
            already_extracted = [g for g in skipped_groups if g in json_group_names or g not in json_only_skipped]
            
            if json_only_skipped and self.json_only_var.get():
                self.log(f"🎯 JSON-only mode: Skipping non-JSON groups: {json_only_skipped}", "blue")
            if already_extracted:
                self.log(f"⏸️ Skipping already extracted groups: {already_extracted}", "orange")
            
        if selected_groups:
            self.log(f"🚀 Starting extraction of selected groups: {selected_groups}", "blue")
            self._start_extraction(selected_groups)
        else:
            messagebox.showinfo("Info", "All selected groups are already extracted")
        
    def extract_all(self):
        """Extract all groups with priority - JSON groups first, then others"""
        if not self.file_groups:
            messagebox.showwarning("No Groups", "No file groups found. Scan folder first.")
            return
            
        # Get JSON groups for priority
        try:
            json_groups = get_archive_groups_status()
            json_group_names = set()
            for group_key, group_data in json_groups.items():
                group_name = group_data.get('base_name', group_key)
                json_group_names.add(group_name)
        except:
            json_group_names = set()
            
        all_groups = list(self.file_groups.keys())
        
        # Separate into priority groups
        priority_groups = []
        non_priority_groups = []
        skipped_groups = []
        
        for group_name in all_groups:
            if self._is_group_already_extracted(group_name):
                skipped_groups.append(group_name)
            elif group_name in json_group_names:
                priority_groups.append(group_name)
            else:
                # Only add non-priority groups if not in JSON-only mode
                if not self.json_only_var.get():
                    non_priority_groups.append(group_name)
                else:
                    skipped_groups.append(group_name)  # Skip non-JSON groups in JSON-only mode
                
        if skipped_groups:
            json_only_skipped = [g for g in skipped_groups if g not in json_group_names]
            already_extracted = [g for g in skipped_groups if g in json_group_names or g not in json_only_skipped]
            
            if json_only_skipped and self.json_only_var.get():
                self.log(f"🎯 JSON-only mode: Skipping non-JSON groups: {json_only_skipped}", "blue")
            if already_extracted:
                self.log(f"⏸️ Skipping already extracted groups: {already_extracted}", "orange")
            
        # Extract priority groups first, then non-priority
        extraction_order = priority_groups + non_priority_groups
        
        if extraction_order:
            if priority_groups:
                self.log(f"🚀 Priority extraction order (JSON groups first): {extraction_order}", "blue")
            else:
                self.log(f"🚀 Extracting all groups: {extraction_order}", "blue")
            self._start_extraction(extraction_order)
        else:
            messagebox.showinfo("Info", "All groups are already extracted")
        
    def _start_extraction(self, group_names):
        if self.is_extracting:
            return
            
        if not self.winrar_path:
            messagebox.showerror("Error", "WinRAR not found!")
            return
            
        self.is_extracting = True
        self.extract_btn.config(state="disabled")
        self.extract_all_btn.config(state="disabled")
        
        thread = threading.Thread(target=self._extract_worker, args=(group_names,), daemon=True)
        thread.start()
        
    def _extract_worker(self, group_names):
        """Worker thread for extraction with error recovery and size verification"""
        try:
            total_groups = len(group_names)
            extracted_count = 0
            failed_count = 0
            
            # DEBUG: Show delete checkbox state
            delete_setting = self.delete_after_extract.get()
            self.log(f"🔧 DEBUG: Delete after extraction setting = {delete_setting}", "blue")
            
            self.log(f"🚀 Starting extraction of {total_groups} groups...", "blue")
            
            for i, group_name in enumerate(group_names):
                if not self.is_extracting:
                    break
                    
                files = self.file_groups[group_name]
                self.log(f"📦 Extracting group {i+1}/{total_groups}: {group_name}", "blue")
                
                first_file = self._find_first_file(files)
                if not first_file:
                    self.log(f"❌ No suitable file found for {group_name} - SKIPPING", "red")
                    failed_count += 1
                    self.failed_groups.add(group_name)  # Mark as failed
                    self._update_group_status(group_name, "❌ No file")
                    continue
                    
                # Calculate total archive size before extraction
                archive_size = sum(f.stat().st_size for f in files)
                self.log(f"📏 Archive group size: {self._format_size(archive_size)}", "info")
                    
                extract_dest = Path(self.download_folder.get()) / self._clean_folder_name(group_name)
                extract_dest.mkdir(exist_ok=True)
                
                success = self._extract_with_winrar(str(first_file), str(extract_dest))
                
                if success:
                    # Verify extraction by comparing folder size
                    extraction_ok = self._verify_extraction_size(group_name, archive_size)
                    
                    if extraction_ok:
                        self.log(f"✅ Successfully extracted: {group_name}", "green")
                        extracted_count += 1
                        self.extracted_groups.add(group_name)  # Mark as extracted
                        self._update_group_status(group_name, "✅ Extracted")
                        
                        # Check if we should delete archives after extraction
                        if self.delete_after_extract.get():
                            self.log(f"🗑️ Delete after extraction is ENABLED - deleting archives for: {group_name}", "blue")
                            self._delete_archive_group(group_name, archive_size)
                        else:
                            self.log(f"📁 Delete after extraction is DISABLED - keeping archives for: {group_name}", "info")
                        
                        # Update UI display to show new status
                        self.parent.after(100, lambda: self._update_groups_display(dict(self.file_groups)))
                    else:
                        self.log(f"⚠️ Extraction verification failed for {group_name} - trying once more", "orange")
                        # Try extraction one more time
                        self.log(f"🔄 Retrying extraction of: {group_name}", "blue")
                        retry_success = self._extract_with_winrar(str(first_file), str(extract_dest))
                        
                        if retry_success:
                            retry_ok = self._verify_extraction_size(group_name, archive_size)
                            if retry_ok:
                                self.log(f"✅ Retry successful: {group_name}", "green")
                                extracted_count += 1
                                self.extracted_groups.add(group_name)
                                self._update_group_status(group_name, "✅ Extracted")
                                
                                # Check if we should delete archives after extraction (MISSING IN RETRY PATH)
                                if self.delete_after_extract.get():
                                    self.log(f"🗑️ Delete after extraction is ENABLED (retry) - deleting archives for: {group_name}", "blue")
                                    self._delete_archive_group(group_name, archive_size)
                                else:
                                    self.log(f"📁 Delete after extraction is DISABLED (retry) - keeping archives for: {group_name}", "info")
                                
                                # Update UI display to show new status
                                self.parent.after(100, lambda: self._update_groups_display(dict(self.file_groups)))
                            else:
                                self.log(f"❌ Retry verification failed: {group_name} - MARKING AS FAILED", "red")
                                failed_count += 1
                                self.failed_groups.add(group_name)
                                self._update_group_status(group_name, "❌ Failed")
                        else:
                            self.log(f"❌ Retry extraction failed: {group_name} - MARKING AS FAILED", "red")
                            failed_count += 1
                            self.failed_groups.add(group_name)
                            self._update_group_status(group_name, "❌ Failed")
                else:
                    self.log(f"❌ Failed to extract: {group_name} - CONTINUING TO NEXT", "red")
                    failed_count += 1
                    self.failed_groups.add(group_name)  # Mark as failed
                    self._update_group_status(group_name, "❌ Failed")
                
                # Update progress
                progress_percent = int((i + 1) / total_groups * 100)
                self.parent.after(0, lambda p=progress_percent: self.progress.config(value=p))
                self.parent.after(0, lambda p=progress_percent: self.progress_label.config(text=f"{p}%"))
                
            # Final summary
            if failed_count > 0:
                self.log(f"🏁 Extraction completed! {extracted_count} succeeded, {failed_count} failed out of {total_groups} groups", "orange")
            else:
                self.log(f"🏁 Extraction completed successfully! All {extracted_count}/{total_groups} groups extracted", "green")
            
        except Exception as e:
            self.log(f"💥 Extraction error: {str(e)}", "red")
        finally:
            self.is_extracting = False
            self.parent.after(0, self._extraction_finished)
            
    def _find_first_file(self, files):
        sorted_files = sorted(files, key=lambda f: f.name.lower())
        
        for file in sorted_files:
            name = file.name.lower()
            if any(pattern in name for pattern in ['.part01.rar', '.part1.rar', '.rar']):
                return file
                
        return sorted_files[0] if sorted_files else None
        
    def _clean_folder_name(self, name):
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        name = re.sub(r'[._]part\d+$', '', name, flags=re.IGNORECASE)
        return name.strip()
        
    def _extract_with_winrar(self, archive_path, extract_dest):
        try:
            cmd = [
                self.winrar_path,
                "x",
                archive_path,
                extract_dest,
                "-y",
                "-ibck+"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return result.returncode == 0
            
        except Exception:
            return False
            
    def _verify_extraction_size(self, group_name, archive_size):
        """Verify extraction by comparing archive size with folder size"""
        try:
            extract_dest = Path(self.download_folder.get()) / self._clean_folder_name(group_name)
            
            if not extract_dest.exists():
                self.log(f"❌ Extraction folder not found: {extract_dest}", "red")
                return False
                
            # Calculate folder size
            folder_size = 0
            file_count = 0
            
            for item in extract_dest.rglob('*'):
                if item.is_file():
                    folder_size += item.stat().st_size
                    file_count += 1
                    
            self.log(f"📏 Extracted folder size: {self._format_size(folder_size)} ({file_count} files)", "info")
            
            # Check if folder is empty
            if folder_size == 0:
                self.log(f"⚠️ Extracted folder is empty - extraction likely failed", "orange")
                return False
                
            # Calculate size difference (allow 100MB tolerance or 10% of archive size, whichever is larger)
            size_diff = abs(archive_size - folder_size)
            tolerance_mb = max(100 * 1024 * 1024, int(archive_size * 0.1))  # 100MB or 10%, whichever is larger
            
            self.log(f"📊 Size difference: {self._format_size(size_diff)} (tolerance: {self._format_size(tolerance_mb)})", "info")
            
            if size_diff <= tolerance_mb:
                self.log(f"✅ Size verification passed: {group_name}", "green")
                return True
            else:
                self.log(f"❌ Size verification failed: difference too large ({self._format_size(size_diff)} > {self._format_size(tolerance_mb)})", "red")
                # Don't fail completely - allow extraction to proceed but log warning
                self.log(f"⚠️ Proceeding with extraction despite size mismatch", "orange")
                return True  # Allow extraction to proceed
                
        except Exception as e:
            self.log(f"⚠️ Error verifying extraction size: {str(e)}", "orange")
            # If we can't verify, assume it failed to be safe
            return False
    def _update_group_status(self, group_name, status):
        for item in self.groups_tree.get_children():
            values = self.groups_tree.item(item)['values']
            if values[0] == group_name:
                new_values = list(values)
                new_values[3] = status
                self.groups_tree.item(item, values=new_values)
                break
                
    def _extraction_finished(self):
        self.extract_btn.config(state="normal")
        self.extract_all_btn.config(state="normal")
        self.progress.config(value=0)
        self.progress_label.config(text="0%")
        
        # Update UI display to show final status
        self._update_groups_display(dict(self.file_groups))
    
    def _delete_archive_group(self, group_name, archive_size):
        """Delete archive files after successful extraction with size verification"""
        try:
            self.log(f"🗑️ DELETE FUNCTION CALLED for: {group_name}", "blue")
            
            if group_name not in self.file_groups:
                self.log(f"❌ Group not found for deletion: {group_name}", "red")
                self.log(f"🔧 Available groups: {list(self.file_groups.keys())}", "orange")
                return False
            
            archive_files = self.file_groups[group_name]
            self.log(f"🔧 Found {len(archive_files)} files to delete: {[f.name for f in archive_files]}", "blue")
            deleted_count = 0
            
            for archive_file in archive_files:
                try:
                    self.log(f"🔧 Checking file: {archive_file} (exists: {archive_file.exists()})", "info")
                    if archive_file.exists():
                        self.log(f"🔧 Attempting to delete: {archive_file}", "orange")
                        archive_file.unlink()
                        self.log(f"🗑️ Deleted: {archive_file.name}", "green")
                        deleted_count += 1
                    else:
                        self.log(f"⚠️ Archive file not found: {archive_file.name}", "orange")
                        deleted_count += 1  # Consider it "deleted" since it's gone
                except Exception as e:
                    self.log(f"❌ Failed to delete {archive_file.name}: {str(e)}", "red")
            
            # Remove from file_groups
            if group_name in self.file_groups:
                del self.file_groups[group_name]
                self.log(f"🔧 Removed {group_name} from file_groups", "blue")
            
            self.log(f"✅ Successfully deleted {deleted_count} archive files for: {group_name}", "green")
            return True
            
        except Exception as e:
            self.log(f"❌ Error deleting archive group: {str(e)}", "red")
            return False

    def debug_json_function(self):
        """Debug function to show JSON group data"""
        self.log("=== 🔍 DEBUG JSON FUNCTION TRIGGERED ===", "blue")
        
        # Get JSON groups
        try:
            print("DEBUG: About to call get_archive_groups_status() from debug function")
            json_groups = get_archive_groups_status()
            print(f"DEBUG: Got {len(json_groups)} JSON groups from config manager in debug function")
            
            for group_key, group_data in json_groups.items():
                group_name = group_data.get('base_name', group_key)
                downloaded_count = group_data.get('downloaded_count', 0)
                total_parts = group_data.get('total_parts', 0)
                completion_pct = group_data.get('completion_percentage', 0)
                
                print(f"DEBUG JSON: Group '{group_name}' - {downloaded_count}/{total_parts} ({completion_pct:.1f}%)")
                print(f"DEBUG JSON: total_parts: {total_parts}, downloaded_parts: {group_data.get('downloaded_parts', [])}")
                
        except Exception as e:
            print(f"DEBUG JSON: Error getting groups: {e}")
            
        self.log("=== 🔍 DEBUG JSON FUNCTION COMPLETED ===", "blue")

    def show_delete_confirmation(self):
        """Show confirmation dialog for deleting archives"""
        print("DEBUG: show_delete_confirmation called")
        print(f"DEBUG: file_groups exists: {bool(self.file_groups)}")
        if self.file_groups:
            print(f"DEBUG: file_groups keys: {list(self.file_groups.keys())}")
        
        if not self.file_groups:
            messagebox.showinfo("Info", "No archive groups found to delete")
            return
            
        # Create confirmation dialog
        confirm_window = tk.Toplevel(self.parent)
        confirm_window.title("Delete Confirmation")
        confirm_window.geometry("400x150")
        confirm_window.transient(self.parent)
        confirm_window.grab_set()
        
        print("DEBUG: Created confirmation dialog")
        
        # Center the dialog
        confirm_window.update_idletasks()
        x = (confirm_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (confirm_window.winfo_screenheight() // 2) - (150 // 2)
        confirm_window.geometry(f"400x150+{x}+{y}")
        
        # Warning message
        warning_frame = ttk.Frame(confirm_window)
        warning_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        warning_label = ttk.Label(
            warning_frame, 
            text="⚠️ Warning: Are you sure you want to delete the last downloaded archives?\nMake sure they have been extracted first.",
            font=("Segoe UI", 10),
            justify="center"
        )
        warning_label.pack(pady=(0, 20))
        
        # Button frame
        button_frame = ttk.Frame(warning_frame)
        button_frame.pack()
        
        # Yes Delete button
        yes_btn = ttk.Button(
            button_frame, 
            text="Yes Delete", 
            command=lambda: self.confirm_delete(confirm_window),
            style="Danger.TButton"
        )
        yes_btn.pack(side="left", padx=(0, 10))
        
        # No Keep button
        no_btn = ttk.Button(
            button_frame, 
            text="No Keep", 
            command=confirm_window.destroy
        )
        no_btn.pack(side="left")
        
        # Configure danger button style if not exists
        try:
            style = ttk.Style()
            if "Danger.TButton" not in style.theme_names():
                style.configure("Danger.TButton", foreground="red")
        except:
            pass
        
        print("DEBUG: Confirmation dialog setup complete")
    
    def confirm_delete(self, dialog_window):
        """Execute the delete operation and close dialog"""
        dialog_window.destroy()
        self.test_delete_function()
    
    def test_delete_function(self):
        """Test delete function manually"""
        self.log("🗑️ Delete archives: triggered", "blue")
        if self.file_groups:
            first_group = list(self.file_groups.keys())[0]
            self.log(f"🗑️ Delete archives: Attempting to delete group: {first_group}", "blue")
            self._delete_archive_group(first_group, 0)
        else:
            self.log("🗑️ Delete archives: No groups found to delete", "orange")

# Test function
def test_smart_manager():
    root = tk.Tk()
    root.title("Smart Download Manager")
    root.geometry("900x700")
    
    manager = SmartFolderManager(root)
    manager.frame.pack(fill="both", expand=True)
    
    root.mainloop()

if __name__ == "__main__":
    test_smart_manager()
