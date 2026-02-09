#!/usr/bin/env python3
"""
Download Interruption Monitor - Notification System
Monitors downloads and shows notifications when interruptions are detected
NO automatic resumption - user control only
"""

import threading
import time


class DownloadAutoResume:
    def __init__(self, main_app):
        """Initialize download interruption monitor with reference to main app"""
        self.main_app = main_app
        self.monitoring = False
        self.monitor_thread = None
        
        # Simple state tracking
        self.paused_downloads = {}  # {url: pause_time}
        self.resume_timers = {}    # {url: timer_thread}
        self.notification_shown = set()  # {url: boolean} - prevent duplicate notifications
        self.urls_being_removed = set()  # {url: boolean} - track URLs being removed
        self.stop_in_progress = set()  # {url: boolean} - track stop events being processed
        self.stop_all_active = False  # {boolean} - track when Stop All is being used
        
    def start_monitoring(self):
        """Start background monitoring thread"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self.resume_timer_loop, daemon=True)
        self.monitor_thread.start()
        print("FRESH MONITOR: Started download interruption monitoring...")
        
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        # Cancel all timers
        for url, timer in self.resume_timers.items():
            if timer and timer.is_alive():
                # We'll let timers finish naturally
                pass
        
        print("FRESH MONITOR: Stopped monitoring")
        
    def on_download_paused(self, url):
        """Called when download is paused - direct event hook"""
        if url not in self.paused_downloads:
            self.paused_downloads[url] = time.time()
            print(f"FRESH MONITOR: Download paused - will show notification in 5 seconds")
            
            # Start individual timer for this download
            self._start_resume_timer(url)
    
    def mark_url_being_removed(self, url):
        """Mark a URL as being removed to prevent interruption notification"""
        self.urls_being_removed.add(url)
        print(f"FRESH MONITOR: URL marked for removal - no interruption notification: {url[:50]}...")
    
    def start_stop_all_mode(self):
        """Enable Stop All mode - no interruption notifications during Stop All"""
        self.stop_all_active = True
        print("FRESH MONITOR: Stop All mode activated - no interruption notifications")
    
    def end_stop_all_mode(self):
        """Disable Stop All mode"""
        self.stop_all_active = False
        print("FRESH MONITOR: Stop All mode deactivated")
    
    def on_download_stopped(self, url):
        """Called when download is stopped - direct event hook"""
        # Skip if URL is being removed
        if url in self.urls_being_removed:
            self.urls_being_removed.discard(url)  # Clean up
            print(f"FRESH MONITOR: Download stopped due to URL removal - skipping notification")
            return
        
        # Skip if Stop All is active
        if self.stop_all_active:
            print(f"FRESH MONITOR: Download stopped during Stop All - skipping notification")
            return
        
        # Skip if stop event is already being processed for this URL
        if url in self.stop_in_progress:
            print(f"FRESH MONITOR: Stop event already being processed - skipping duplicate")
            return
        
        # Skip if notification already shown for this URL
        if url in self.notification_shown:
            print(f"FRESH MONITOR: Notification already shown - skipping")
            return
        
        # Mark stop event as being processed
        self.stop_in_progress.add(url)
            
        if url not in self.paused_downloads:
            self.paused_downloads[url] = time.time()
            print(f"FRESH MONITOR: Download stopped - will show notification in 5 seconds")
            
            # Start individual timer for this download
            self._start_resume_timer(url)
        
        # Clear the stop in progress flag after a short delay
        def clear_stop_flag():
            time.sleep(2)  # Wait 2 seconds before clearing
            self.stop_in_progress.discard(url)
        
        threading.Thread(target=clear_stop_flag, daemon=True).start()
    
    def on_download_completed(self, url):
        """Called when download completes - cleanup"""
        if url in self.paused_downloads:
            del self.paused_downloads[url]
        if url in self.resume_timers:
            del self.resume_timers[url]
        if url in self.notification_shown:
            self.notification_shown.discard(url)
        if url in self.stop_in_progress:
            self.stop_in_progress.discard(url)
        print(f"FRESH MONITOR: Download completed - removed from tracking")
    
    def on_download_started(self, url):
        """Called when download starts - cleanup any existing timers"""
        if url in self.paused_downloads:
            del self.paused_downloads[url]
        if url in self.resume_timers:
            # Cancel existing timer
            timer = self.resume_timers[url]
            if timer and timer.is_alive():
                # We'll let it finish naturally since threads can't be forcibly killed
                pass
            del self.resume_timers[url]
        if url in self.notification_shown:
            self.notification_shown.discard(url)
        if url in self.stop_in_progress:
            self.stop_in_progress.discard(url)
        print(f"FRESH MONITOR: Download started - cleared any existing timers")
    
    def on_download_resumed(self, url):
        """Called when download is manually resumed by user"""
        if url in self.paused_downloads:
            del self.paused_downloads[url]
        if url in self.resume_timers:
            # Cancel existing timer
            timer = self.resume_timers[url]
            if timer and timer.is_alive():
                # We'll let it finish naturally since threads can't be forcibly killed
                pass
            del self.resume_timers[url]
        if url in self.notification_shown:
            self.notification_shown.discard(url)
        if url in self.stop_in_progress:
            self.stop_in_progress.discard(url)
        print(f"FRESH MONITOR: Download manually resumed by user - {url[:50]}...")
    
    def _start_resume_timer(self, url):
        """Start monitoring timer for a download - 1-second delay then 10-second countdown"""
        def timer_func():
            # Wait 1 second before showing popup
            time.sleep(1)
            if url in self.paused_downloads and url not in self.notification_shown:  # Still paused and notification not shown
                print(f"FRESH MONITOR: Download interruption detected - showing popup after 1 second")
                # Mark notification as shown to prevent duplicates
                self.notification_shown.add(url)
                self._show_interruption_notification(url)
                # Note: Cleanup is now handled in _show_interruption_notification after timeout
        
        timer = threading.Thread(target=timer_func, daemon=True)
        timer.start()
        self.resume_timers[url] = timer
    
    def _show_interruption_notification(self, url):
        """Show popup notification with 10-second countdown, Yes/No buttons, and auto-resume"""
        try:
            from tkinter import messagebox, simpledialog
            import threading as tk_thread
            import tkinter as tk
            
            def show_popup():
                # Get filename for better user experience
                filename = "Unknown file"
                if url in self.main_app.download_states:
                    temp_path = self.main_app.download_states[url].get("temp_path", "")
                    if temp_path:
                        from pathlib import Path
                        filename = Path(temp_path).stem  # Remove .tmp extension
                
                # Create countdown popup
                root = self.main_app.root
                popup = tk.Toplevel(root)
                popup.title("Download Interruption Detected")
                popup.geometry("450x250")  # Made taller and wider
                popup.transient(root)
                popup.grab_set()
                
                # Center the popup
                popup.update_idletasks()
                x = (popup.winfo_screenwidth() // 2) - (450 // 2)
                y = (popup.winfo_screenheight() // 2) - (250 // 2)
                popup.geometry(f"450x250+{x}+{y}")
                
                # Message label
                message = f"Monitoring detected a download interruption:\n\nFile: {filename}\nURL: {url[:50]}...\n\nAre you sure you want to pause this download?"
                message_label = tk.Label(popup, text=message, wraplength=350, justify="left")
                message_label.pack(pady=20)
                
                # Countdown label
                countdown_label = tk.Label(popup, text="Auto-resuming in 10 seconds...", font=("Arial", 12, "bold"))
                countdown_label.pack(pady=10)
                
                # Variable to track if user made choice
                user_choice = {"made": False, "pause": False}
                
                def countdown():
                    for i in range(10, 0, -1):
                        if user_choice["made"]:
                            break
                        countdown_label.config(text=f"Auto-resuming in {i} seconds...")
                        popup.update()
                        time.sleep(1)
                    
                    # Auto-resume if user didn't make choice
                    if not user_choice["made"]:
                        # Auto-resume
                        popup.destroy()
                        print(f"FRESH MONITOR: Auto-resuming download after 10-second timeout - {url[:50]}...")
                        # Clear monitoring state
                        if url in self.paused_downloads:
                            del self.paused_downloads[url]
                        if url in self.resume_timers:
                            del self.resume_timers[url]
                        if url in self.notification_shown:
                            self.notification_shown.discard(url)
                        # Trigger resume
                        self.main_app.start_single_url(url)
                
                def pause_download():
                    user_choice["made"] = True
                    user_choice["pause"] = True
                    popup.destroy()
                    print(f"FRESH MONITOR: User chose to pause download - {url[:50]}...")
                    # Clear monitoring state but keep paused
                    if url in self.resume_timers:
                        del self.resume_timers[url]
                    if url in self.notification_shown:
                        self.notification_shown.discard(url)
                
                def resume_download():
                    user_choice["made"] = True
                    user_choice["pause"] = False
                    popup.destroy()
                    print(f"FRESH MONITOR: User chose to resume download - {url[:50]}...")
                    # Clear monitoring state
                    if url in self.paused_downloads:
                        del self.paused_downloads[url]
                    if url in self.resume_timers:
                        del self.resume_timers[url]
                    if url in self.notification_shown:
                        self.notification_shown.discard(url)
                    # Trigger resume
                    self.main_app.start_single_url(url)
                
                # Buttons
                button_frame = tk.Frame(popup)
                button_frame.pack(pady=10)
                
                pause_btn = tk.Button(button_frame, text="Yes (Pause)", command=pause_download, width=12)
                pause_btn.pack(side="left", padx=5)
                
                resume_btn = tk.Button(button_frame, text="No (Resume)", command=resume_download, width=12)
                resume_btn.pack(side="left", padx=5)
                
                # Start countdown in separate thread
                countdown_thread = threading.Thread(target=countdown, daemon=True)
                countdown_thread.start()
            
            # Show popup in main thread
            if threading.current_thread() is not tk_thread.main_thread():
                # Use after to schedule in main thread
                if hasattr(self.main_app, 'root'):
                    self.main_app.root.after(0, show_popup)
                else:
                    show_popup()  # Fallback
            else:
                show_popup()
                
        except Exception as e:
            print(f"FRESH MONITOR ERROR: Failed to show notification: {e}")
    
    def _force_resume_download(self, url):
        """Auto-resume download after timeout"""
        print(f"FRESH AUTO-RESUME: Auto-resuming download after timeout - {url[:50]}...")
        # Clear monitoring state
        if url in self.paused_downloads:
            del self.paused_downloads[url]
        if url in self.resume_timers:
            del self.resume_timers[url]
        if url in self.notification_shown:
            self.notification_shown.discard(url)
        # Trigger resume
        self.main_app.start_single_url(url)
        return True
    
    def resume_timer_loop(self):
        """Simple background loop - just for cleanup"""
        while self.monitoring:
            try:
                # Clean up old timers (optional cleanup)
                current_time = time.time()
                expired_timers = []
                
                for url, pause_time in self.paused_downloads.items():
                    if current_time - pause_time > 10:  # Clean up after 10 seconds
                        expired_timers.append(url)
                
                for url in expired_timers:
                    if url in self.paused_downloads:
                        del self.paused_downloads[url]
                    if url in self.resume_timers:
                        del self.resume_timers[url]
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                print(f"FRESH MONITOR ERROR: {e}")
                time.sleep(5)
    
    def force_test_resume(self):
        """Test function - automatically pause and resume after 5 seconds"""
        print("=== FRESH AUTO-RESUME TEST ===")
        
        test_count = 0
        for url, state in self.main_app.download_states.items():
            current_status = self.main_app.url_status.get(url, "unknown")
            if current_status in ["downloading"]:
                print(f"TEST: Auto-pausing download for 5-second test")
                # Actually pause it first
                self.main_app.stop_single_url(url)
                # Trigger auto-resume system
                self.on_download_stopped(url)
                test_count += 1
        
        if test_count > 0:
            print(f"=== TEST: Auto-paused {test_count} downloads. They will auto-resume in 5 seconds ===")
        else:
            print("=== TEST: No active downloads to test ===")
        
        return test_count


def integrate_auto_resume(main_app):
    """Integrate download interruption monitor into main application"""
    
    # Create fresh auto-resume instance
    auto_resume = DownloadAutoResume(main_app)
    
    # Store reference in main app
    main_app.auto_resume = auto_resume
    
    # Hook into start/stop events by patching existing methods
    original_start_single_url = main_app.start_single_url
    original_stop_single_url = main_app.stop_single_url
    original_stop_all_simultaneous = getattr(main_app, 'stop_all_simultaneous', None)
    
    def enhanced_stop_single_url(url):
        """Enhanced stop function with monitoring hook"""
        result = original_stop_single_url(url)
        # Notify monitoring system
        auto_resume.on_download_stopped(url)
        return result
    
    def enhanced_stop_all_simultaneous():
        """Enhanced stop all with monitoring hook"""
        # Activate Stop All mode to prevent notifications
        auto_resume.start_stop_all_mode()
        
        result = None
        if original_stop_all_simultaneous:
            result = original_stop_all_simultaneous()
        
        # Notify monitoring system for all stopped downloads (but notifications will be skipped)
        for url in main_app.links:
            if main_app.url_status.get(url) == "paused":
                auto_resume.on_download_stopped(url)
        
        # Deactivate Stop All mode after a short delay
        def deactivate_stop_all():
            time.sleep(1)  # Wait 1 second before deactivating
            auto_resume.end_stop_all_mode()
        
        threading.Thread(target=deactivate_stop_all, daemon=True).start()
        return result
    
    def enhanced_start_single_url(url):
        """Enhanced start function with monitoring hook"""
        result = original_start_single_url(url)
        # Notify monitoring system
        auto_resume.on_download_started(url)
        auto_resume.on_download_resumed(url)
        return result
    
    # Replace methods with enhanced versions
    main_app.stop_single_url = enhanced_stop_single_url
    main_app.start_single_url = enhanced_start_single_url
    if original_stop_all_simultaneous:
        main_app.stop_all_simultaneous = enhanced_stop_all_simultaneous
    
    # Hook into download completion
    original_download_single_completed = getattr(main_app, 'download_single_completed', None)
    
    def enhanced_download_single_completed(url):
        """Enhanced completion with monitoring hook"""
        if original_download_single_completed:
            original_download_single_completed(url)
        # Notify monitoring system
        auto_resume.on_download_completed(url)
    
    main_app.download_single_completed = enhanced_download_single_completed
    
    # Start monitoring
    auto_resume.start_monitoring()
    
    # Add cleanup to force_close method
    original_force_close = main_app.force_close
    
    def enhanced_force_close():
        # Stop monitoring
        if hasattr(main_app, 'auto_resume'):
            main_app.auto_resume.stop_monitoring()
        
        # Call original cleanup
        original_force_close()
    
    # Replace force_close method
    main_app.force_close = enhanced_force_close
    
    print("Download Interruption Monitor integrated successfully!")
    return auto_resume
