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
from config_manager import get_archive_groups_status, can_extract_group

class SmartFolderManager:
    def __init__(self, parent):
        self.parent = parent
        self.frame = ttk.Frame(parent)
        
        # Variables
        self.download_folder = tk.StringVar(value="D:\\Games\\FitGirl Downloader\\test")
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
        json_only_setting = get_setting("json_only_mode", False)
        self.json_only_var = tk.BooleanVar(value=json_only_setting)
        self.json_only_cb = ttk.Checkbutton(
            options_frame, 
            text="🎯 Extract only JSON-tracked archives (skip existing archives)", 
            variable=self.json_only_var,
            command=self.update_extraction_mode
        )
        self.json_only_cb.pack(anchor="w")
        
        # Mode label
        self.mode_label = ttk.Label(options_frame, text="📁 Current mode: Extract all archives", font=("Segoe UI", 9), foreground="blue")
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
            
        # Get the authoritative group data from JSON
        try:
            json_groups = get_archive_groups_status()
        except Exception as e:
            return  # Silent fail for auto-scan
            
        # Separate JSON groups and non-JSON groups
        json_group_names = set()
        ready_json_groups = []
        
        for group_key, group_data in json_groups.items():
            group_name = group_data.get('base_name', group_key)
            json_group_names.add(group_name)
            
            # Check if this group exists in our scanned files
            if group_name in self.file_groups:
                downloaded_count = group_data.get('downloaded_count', 0)
                total_parts = group_data.get('total_parts', 0)
                completion_pct = group_data.get('completion_percentage', 0)
                
                # Only extract if group is 100% complete and not already extracted/failed
                if completion_pct >= 100.0 and downloaded_count > 0:
                    if (group_name not in self.failed_groups and 
                        group_name not in self.extracted_groups):
                        # Check extraction status with size verification
                        extraction_status = self._check_extraction_status(group_name)
                        if extraction_status == "needs_re_extraction":
                            self.log(f"🔄 JSON group '{group_name}' has size mismatch - re-extracting", "orange")
                            ready_json_groups.append(group_name)
                        elif extraction_status == "already_extracted":
                            self.log(f"⏸️ JSON group '{group_name}' already extracted - skipping", "orange")
                        else:  # not_extracted
                            self.log(f"✅ JSON group '{group_name}' ready for extraction", "green")
                            ready_json_groups.append(group_name)
                    else:
                        self.log(f"⏸️ JSON group '{group_name}' already processed - skipping", "orange")
        
        # Extract ready JSON groups first
        if ready_json_groups:
            for group_name in ready_json_groups:
                self.log(f"✅ JSON group '{group_name}' is 100% complete - starting auto-extraction", "green")
                self._auto_extract_group(group_name)
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
            # Skip non-JSON groups if JSON-only mode is enabled
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
                            self._delete_archive_group(group_name, archive_size)
                        
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
                
            # Calculate size difference (allow 20MB tolerance)
            size_diff = abs(archive_size - folder_size)
            tolerance_mb = 20 * 1024 * 1024  # 20MB in bytes
            
            self.log(f"📊 Size difference: {self._format_size(size_diff)} (tolerance: 20MB)", "info")
            
            if size_diff <= tolerance_mb:
                self.log(f"✅ Size verification passed: {group_name}", "green")
                return True
            else:
                self.log(f"❌ Size verification failed: difference too large ({self._format_size(size_diff)} > 20MB)", "red")
                return False
                
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
            self.log(f"🗑️ Deleting archives after extraction: {group_name}", "blue")
            
            if group_name not in self.file_groups:
                self.log(f"❌ Group not found for deletion: {group_name}", "red")
                return False
            
            archive_files = self.file_groups[group_name]
            deleted_count = 0
            
            for archive_file in archive_files:
                try:
                    if archive_file.exists():
                        archive_file.unlink()
                        self.log(f"🗑️ Deleted: {archive_file.name}", "green")
                        deleted_count += 1
                    else:
                        self.log(f"⚠️ Archive file not found: {archive_file.name}", "orange")
                        deleted_count += 1  # Consider it "deleted" since it's gone
                except Exception as e:
                    self.log(f"❌ Failed to delete {archive_file.name}: {str(e)}", "red")
            
            # Remove from file_groups
            del self.file_groups[group_name]
            
            self.log(f"✅ Successfully deleted {deleted_count} archive files for: {group_name}", "green")
            return True
            
        except Exception as e:
            self.log(f"❌ Error deleting archive group: {str(e)}", "red")
            return False

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
