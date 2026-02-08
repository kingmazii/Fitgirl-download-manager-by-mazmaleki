import tkinter as tk
from tkinter import ttk, messagebox
import requests
import threading
import time
from datetime import datetime
import queue
import re
import webbrowser
import json

class GitHubNotificationSystem:
    def __init__(self, background_mode=False):
        # GitHub configuration
        self.github_raw_url = "https://raw.githubusercontent.com/kingmazii/Fitgirl-download-manager-by-mazmaleki/main"
        self.notifications_url = f"{self.github_raw_url}/notifications.json"
        self.images_base_url = f"{self.github_raw_url}/images"
        
        # Use GitHub (not local file)
        self.use_local_file = False
        
        # Background mode - don't show main window automatically
        self.background_mode = background_mode
        
        # Tracking
        self.seen_notifications = set()
        self.notification_queue = queue.Queue()
        self.running = True
        self.last_notification = None  # Store last notification for re-display
        self.last_notification_id = None
        self.current_popup = None  # Track current popup to prevent duplicates
        self.is_startup = True  # Prevent auto-popup on startup
        
        # Setup GUI only if not in background mode
        if not background_mode:
            self.setup_gui()
        else:
            # In background mode, create GUI but make it invisible
            self.setup_gui()
            self.root.withdraw()  # Hide window immediately
            # Start GUI update loop for background mode
            self.update_gui()
        
        # Start checking thread
        self.start_notification_checker()
        
        # Start GUI update checker only if not in background mode
        if not background_mode:
            self.update_gui()
        
    def show_main_window(self):
        """Show the main notification window (for background mode)"""
        if self.root:
            self.root.deiconify()  # Show window if hidden
            self.root.lift()         # Bring to front
            self.root.focus_force()   # Force focus
        
    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("GitHub Notification System")
        self.root.geometry("500x400")
        self.root.resizable(False, False)
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="GitHub Notification Receiver", 
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        # Status
        self.status_label = ttk.Label(main_frame, text="Status: Checking GitHub...", 
                                     font=("Arial", 10))
        self.status_label.pack(pady=5)
        
        # GitHub info
        github_label = ttk.Label(main_frame, text=f"Repo: kingmazii/Fitgirl-download-manager-by-mazmaleki", 
                                   font=("Arial", 9))
        github_label.pack(pady=5)
        
        # Notifications display
        self.notifications_frame = ttk.LabelFrame(main_frame, text="Recent Notifications", padding="5")
        self.notifications_frame.pack(fill="both", expand=True, pady=10)
        
        # Simple text display with larger, bold text and no border
        self.notifications_text = tk.Text(self.notifications_frame, height=10, width=55, 
                                     wrap="word", font=("Arial", 11, "bold"),  # Larger and bold
                                     borderwidth=0,  # No border
                                     relief="flat")
        scrollbar = ttk.Scrollbar(self.notifications_frame, orient="vertical", 
                                  command=self.notifications_text.yview)
        self.notifications_text.configure(yscrollcommand=scrollbar.set)
        
        self.notifications_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        # Show last notification button
        show_last_btn = ttk.Button(button_frame, text="🔔 Show Last Notification", 
                                 command=self.show_last_notification)
        show_last_btn.pack(side="left", padx=5)
        
        # Clear seen notifications button
        clear_btn = ttk.Button(button_frame, text="🔄 Reset Notifications", 
                             command=self.clear_seen_notifications)
        clear_btn.pack(side="left", padx=5)
        
        # Close button
        close_button = ttk.Button(button_frame, text="Close", command=self.hide_main_window)
        close_button.pack(side="left", padx=5)
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self.hide_main_window)
        
    def start_notification_checker(self):
        """Start background thread to check GitHub notifications"""
        self.check_thread = threading.Thread(target=self.check_notifications_loop, daemon=True)
        self.check_thread.start()
        
        # Start GUI update checker
        self.update_gui()
        
    def check_notifications_loop(self):
        """Background thread that continuously check GitHub for new notifications"""
        # First check - get current notifications silently, but process them to store last_notification
        current_notifications = self.get_current_notifications_silently()
        
        # End startup mode after first check
        if self.is_startup:
            self.is_startup = False
            # Process current notifications to store them but don't show popups
            if current_notifications:
                for notification in current_notifications:
                    notification_id = notification.get('id', '')
                    if notification_id:
                        self.seen_notifications.add(notification_id)
                        # Process to store last_notification but don't show popup
                        self.process_notification(notification)
            print(f"DEBUG: Startup mode ended - added {len(current_notifications)} existing notifications to seen set")
            self.update_status("Ready - monitoring for NEW notifications only")
        
        # Continue checking for new notifications
        while self.running:
            try:
                self.check_github_notifications()
                time.sleep(10)  # Check every 10 seconds for GitHub updates
            except Exception as e:
                self.update_status(f"Error: {str(e)}")
                time.sleep(30)  # Wait longer on error
                
    def get_current_notifications_silently(self):
        """Get current notifications without showing popups"""
        try:
            response = requests.get(self.notifications_url, timeout=10)
            
            if response.status_code == 200:
                notifications_data = response.json()
                if 'notifications' in notifications_data:
                    return notifications_data['notifications']
            return []
        except Exception as e:
            print(f"DEBUG: Error getting current notifications silently: {e}")
            return []
        
    def check_github_notifications(self):
        """Check GitHub for new notifications"""
        try:
            self.update_status("Fetching notifications from GitHub...")
            
            # Fetch notifications JSON
            response = requests.get(self.notifications_url, timeout=10)
            
            if response.status_code == 200:
                notifications_data = response.json()
                print(f"DEBUG: Fetched {len(notifications_data.get('notifications', []))} notifications")
            else:
                self.update_status(f"GitHub error: HTTP {response.status_code}")
                return
            
            if 'notifications' in notifications_data:
                notifications = notifications_data['notifications']
                
                # Process each notification
                for notification in notifications:
                    notification_id = notification.get('id', '')
                    
                    # Only show if we haven't seen it AND it's not the initial load
                    if notification_id not in self.seen_notifications:
                        print(f"DEBUG: NEW notification found: {notification_id}")
                        # Clear seen notifications when we find a NEW one
                        self.seen_notifications.clear()
                        print(f"DEBUG: Cleared seen notifications for NEW notification")
                        self.process_notification(notification)
                        self.seen_notifications.add(notification_id)
                    else:
                        print(f"DEBUG: Already seen notification {notification_id}")
            
            self.update_status(f"Found {len(notifications)} notifications")
                
        except requests.exceptions.RequestException as e:
            self.update_status(f"Network error: {str(e)}")
        except json.JSONDecodeError as e:
            self.update_status(f"JSON error: {str(e)}")
        except Exception as e:
            self.update_status(f"Error fetching notifications: {str(e)}")
            print(f"DEBUG: Error in check_github_notifications: {e}")
            
    def process_notification(self, notification):
        """Process a single notification"""
        try:
            print(f"DEBUG: Processing notification: {notification.get('id', 'unknown')}")
            
            # Create notification object
            notification_obj = {
                'title': notification.get('title', 'No Title'),
                'message': notification.get('message', ''),
                'improvements': notification.get('improvements', ''),  # Extract improvements field
                'url': notification.get('url', ''),  # Extract URL field
                'time': datetime.now().strftime("%H:%M:%S"),
                'id': notification.get('id', '')
            }
            
            # Store last notification for re-display (ALWAYS store)
            self.last_notification = notification_obj
            print(f"DEBUG: Stored last notification: {notification_obj.get('id', 'unknown')}")
            
            # Only show popup if it's not startup time
            if not self.is_startup:
                # Add to queue for GUI display
                self.notification_queue.put(notification_obj)
                print(f"DEBUG: Added notification to queue: {notification_obj.get('id', 'unknown')}")
            else:
                print(f"DEBUG: Startup - storing notification but not showing popup: {notification_obj.get('id', 'unknown')}")
            
        except Exception as e:
            print(f"Error processing notification: {e}")
            
    def update_status(self, message):
        """Update status label in main thread"""
        if self.root is not None:
            try:
                self.root.after(0, lambda: self.status_label.config(text=message))
            except RuntimeError:
                # Can't call after from background thread, just print
                print(f"STATUS: {message}")
        else:
            # In background mode, just print to console
            print(f"STATUS: {message}")
        
    def update_gui(self):
        """Update GUI with new notifications from queue"""
        # Don't update GUI if no root window
        if self.root is None:
            return
            
        try:
            while True:
                try:
                    # Get notification from queue
                    notification = self.notification_queue.get_nowait()
                    
                    # Display notification
                    self.display_notification(notification)
                    
                except queue.Empty:
                    pass
                    
                # Schedule next update
                if self.running:
                    self.root.after(500, self.update_gui)  # Check every 0.5 seconds for instant popups
                    return  # Exit this call, will be called again by after()
                    
        except Exception as e:
            print(f"Error in update_gui: {e}")
            if self.running and self.root:
                self.root.after(1000, self.update_gui)  # Check every 0.5 seconds for instant popups
            
    def display_notification(self, notification):
        """Display a new notification in GUI"""
        # Store last notification for re-display
        self.last_notification = notification
        
        # Add to notifications display
        timestamp = notification['time']
        title = notification['title']
        message = notification['message']
        
        # Simple notification text
        notification_text = f"[{timestamp}] {title}\n{message}\n" + "-"*40 + "\n"
        
        # Insert at top of text widget
        self.notifications_text.insert("1.0", notification_text)
        
        # Keep only last 10 notifications
        lines = self.notifications_text.get("1.0", "end").split('\n')
        if len(lines) > 80:  # Rough estimate
            self.notifications_text.delete("end-20l", "end")
            
        # Show popup immediately for new notifications
        self.show_simple_popup(notification)
        
    def show_simple_popup(self, notification):
        """Show a simple popup window with notification"""
        # Check if popup is already open
        if self.current_popup and self.current_popup.winfo_exists():
            return  # Don't open duplicate popup
        
        popup = tk.Toplevel(self.root)
        self.current_popup = popup  # Track this popup
        
        popup.title("🔔 New Notification")
        popup.geometry("500x400")  # Taller window
        popup.resizable(False, False)
        
        # Make popup stay on top and flash like alert
        popup.attributes('-topmost', True)
        popup.attributes('-alpha', 0.95)  # Slightly transparent
        
        # Center popup
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - (500 // 2)
        y = (popup.winfo_screenheight() // 2) - (400 // 2)
        popup.geometry(f"500x400+{x}+{y}")
        
        # Alert-style background
        popup.configure(bg='#f0f0f0')  # Dark alert background
        
        # Handle popup closing
        def on_popup_close():
            self.current_popup = None  # Clear popup reference
            # Don't clear seen_notifications here - let it be cleared only when NEW notification arrives
            print(f"DEBUG: Popup closed - keeping seen notifications, will only clear on NEW notification")
            popup.destroy()
        
        popup.protocol("WM_DELETE_WINDOW", on_popup_close)
        
        # Content frame
        content_frame = ttk.Frame(popup, padding="20")
        content_frame.pack(fill="both", expand=True)
        
        # Title with blue color and lamp icon
        title_label = tk.Label(content_frame, text=f"💡 {notification['title']}",  # Lamp icon
                                 font=("Arial", 14, "bold"), 
                                 fg="blue",  # Blue color
                                 bg='#f0f0f0',  # Dark background
                                 highlightthickness=0)
        title_label.pack(pady=(0, 15))
        
        # Separator
        separator = ttk.Separator(content_frame, orient="horizontal")
        separator.pack(fill="x", pady=(0, 10))
        
        # Message with larger, bold text and black color
        message_text = tk.Text(content_frame, height=3, width=50, wrap="word", 
                           font=("Arial", 11, "bold"),  # Larger and bold
                           borderwidth=0,  # No border
                           relief="flat",
                           bg='#f0f0f0',  # Dark background
                           fg='black',  # Black text
                           highlightthickness=0)
        message_text.insert("1.0", notification['message'])
        message_text.config(state="disabled")
        message_text.pack(pady=(0, 5))
        
        # Improvements as bullet points with larger text
        improvements = notification.get('improvements', '')
        if improvements:
            # Split improvements by comma and create bullet points
            improvement_list = [item.strip() for item in improvements.split(',') if item.strip()]
            
            if improvement_list:
                improvements_text = tk.Text(content_frame, height=len(improvement_list) + 1, width=50, wrap="word", 
                                       font=("Arial", 10, "normal"),  # Larger text (was 9pt)
                                       borderwidth=0,  # No border
                                       relief="flat",
                                       bg='#f0f0f0',  # Dark background
                                       fg='#333333',  # Darker gray text
                                       highlightthickness=0)
                
                improvements_text.insert("1.0", "📋 Improvements:\n")
                for i, improvement in enumerate(improvement_list, 1):
                    improvements_text.insert(f"{i+1}.0", f"  • {improvement}\n")
                
                improvements_text.config(state="disabled")
                improvements_text.pack(pady=(0, 10))
        
        # Find and create link-style buttons (from URL field) - Under improvements
        notification_url = notification.get('url', '')  # Get URL from separate field
        if notification_url:
            links_frame = ttk.Frame(content_frame)
            links_frame.pack(fill="x", pady=(5, 10))  # Under improvements, with padding
            
            # Show more of the URL (up to 50 characters)
            display_url = notification_url if len(notification_url) <= 50 else notification_url[:47] + "..."
            
            link_btn = tk.Button(
                links_frame,
                text=f"🔗 {display_url}",  # Show more of URL
                command=lambda u=notification_url: webbrowser.open(u),
                bg='#0078d7',  # Link blue
                fg='white',
                font=("Arial", 10, "underline"),  # Underlined like link
                relief="flat",
                borderwidth=0,
                cursor="hand2",  # Hand cursor
                activebackground='#0056b3',  # Darker blue on hover
                width=40  # Wider button for more text
            )
            link_btn.pack(pady=2)  # Centered under improvements
        
        # Close button at very bottom below everything
        close_btn = ttk.Button(content_frame, text="✓ Close Notification", 
                              command=on_popup_close,  # Use the same close function
                              width=20)
        close_btn.pack(pady=(10, 5), side="bottom")  # More padding, at very bottom
        
    def extract_urls(self, text):
        """Extract URLs from text"""
        url_pattern = r'https?://[^\s\)]+'
        urls = re.findall(url_pattern, text)
        return urls
        
    def show_last_notification(self):
        """Show the last notification popup again"""
        if self.last_notification:
            print(f"DEBUG: Showing last notification: {self.last_notification.get('id', 'unknown')}")
            self.show_simple_popup(self.last_notification)
            self.update_status(f"🔔 Showing notification: {self.last_notification.get('title', 'No Title')}")
        else:
            print("DEBUG: No last notification available")
            self.update_status("ℹ️ No notifications received yet")
        
    def clear_seen_notifications(self):
        """Clear seen notifications to show them again"""
        self.seen_notifications.clear()
        self.update_status("🔄 Cleared seen notifications - will show latest again")
        print("DEBUG: Manually cleared seen notifications")
        
    def hide_main_window(self):
        """Hide the main notification window (don't close the app)"""
        if self.root:
            self.root.withdraw()  # Hide window instead of destroying
        
    def close_app(self):
        """Close the application"""
        self.running = False
        if self.root:
            self.root.quit()
            self.root.destroy()
        
    def run(self):
        """Start the application"""
        if not self.background_mode and self.root:
            self.root.mainloop()
        else:
            # In background mode, just keep the thread alive
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.running = False

if __name__ == "__main__":
    app = GitHubNotificationSystem()
    app.run()
