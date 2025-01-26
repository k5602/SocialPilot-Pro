import datetime
import threading
import calendar
import json
import random
import os
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw
import schedule
import pytz
from textblob import TextBlob
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from dateutil.relativedelta import relativedelta
import pandas as pd
import keyring
import tweepy
from facebook import GraphAPI
from TikTokApi import TikTokApi
from linkedin_api import Linkedin

PLATFORMS = ["Facebook", "Instagram", "X (Twitter)", "LinkedIn", "TikTok", "Snapchat"]
MEDIA_TEMP = Path.home() / ".socialpilot_media"
API_KEYS = {
    "facebook": ("APP_ID", "APP_SECRET"),
    "twitter": ("API_KEY", "API_SECRET"),
    "linkedin": ("CLIENT_ID", "CLIENT_SECRET"),
    "tiktok": ("ACCESS_TOKEN",),
    "snapchat": ("AD_ACCOUNT_ID", "CLIENT_SECRET")
}
CATEGORIES = {
    "Documents": [".pdf", ".docx", ".txt", ".xlsx", ".pptx"],
    "Images": [".jpg", ".png", ".webp", ".gif", ".svg"]
}

class SocialMediaManager:
    """Handles all social media operations and data management"""
    
    def __init__(self):
        self.scheduled_posts = []
        self.comments = []
        self.clients = {}
        self._setup_temp_storage()
        self._start_scheduler()

    def _setup_temp_storage(self):
        """Create temporary media storage directory"""
        MEDIA_TEMP.mkdir(exist_ok=True)

    def _load_credentials(self):
        """Load API credentials from secure storage"""
        self.credentials = {}
        for platform in PLATFORMS:
            keys = API_KEYS.get(platform.lower(), [])
            self.credentials[platform] = {
                key: keyring.get_password(f"socialpilot_{platform}", key)
                for key in keys
            }

    def _setup_clients(self):
        """Initialize API clients for all platforms"""
        self.clients = {
            "Facebook": GraphAPI(
                access_token=self.credentials["Facebook"]["APP_ID"]
            ) if self.credentials["Facebook"]["APP_ID"] else None,
            "X (Twitter)": tweepy.Client(
                consumer_key=self.credentials["X (Twitter)"]["API_KEY"],
                consumer_secret=self.credentials["X (Twitter)"]["API_SECRET"]
            ) if self.credentials["X (Twitter)"]["API_KEY"] else None,
            "LinkedIn": Linkedin(
                username=self.credentials["LinkedIn"]["CLIENT_ID"],
                password=self.credentials["LinkedIn"]["CLIENT_SECRET"]
            ) if self.credentials["LinkedIn"]["CLIENT_ID"] else None,
            "TikTok": TikTokApi().get_instance(
                custom_verifyFp=self.credentials["TikTok"]["ACCESS_TOKEN"]
            ) if self.credentials["TikTok"]["ACCESS_TOKEN"] else None
        }

    def setup_credentials(self):
        """Load credentials and setup clients"""
        self._load_credentials()
        self._setup_clients()
        return bool(any(self.clients.values()))

    def schedule_post(self, platform, content, media_path=None, schedule_time=None):
        """Queue post with validation and media processing"""
        post = {
            "platform": platform,
            "content": self._process_content(platform, content),
            "media": self._process_media(platform, media_path),
            "scheduled_time": schedule_time or datetime.datetime.now(),
            "status": "Queued"
        }
        self.scheduled_posts.append(post)
        return post

    def _process_content(self, platform, text):
        """Apply platform-specific formatting rules"""
        char_limit = {
            "Facebook": 2200,
            "X (Twitter)": 280,
            "LinkedIn": 3000,
            "TikTok": 150,
            "Snapchat": 100
        }.get(platform, 2000)
        
        return text[:char_limit] + " " + self._generate_hashtags(text)

    def _process_media(self, platform, media_path):
        """Handle image processing only"""
        if not media_path:
            return None
            
        try:
            if media_path.suffix.lower() in [".jpg", ".png"]:
                return self._process_image(platform, media_path)
            return None
        except Exception as e:
            print(f"Media processing error: {str(e)}")
            return None

    def _generate_hashtags(self, text, n=5):
        """Generate AI-powered hashtag suggestions"""
        keywords = ["socialmedia", "marketing", "tech", "business", "innovation"]
        return " ".join(f"#{kw}" for kw in keywords[:n])

    def _start_scheduler(self):
        """Background task to check scheduled posts"""
        def scheduler_loop():
            while True:
                now = datetime.datetime.now(pytz.utc)
                for post in self.scheduled_posts:
                    if post["status"] == "Queued" and post["scheduled_time"] <= now:
                        self._publish_post(post)
                time.sleep(60)
        
        threading.Thread(target=scheduler_loop, daemon=True).start()

    def _publish_post(self, post):
        """Execute platform-specific posting"""
        try:
            client = self.clients.get(post["platform"])
            if not client:
                raise Exception("Client not configured")

            if post["platform"] == "X (Twitter)":
                client.create_tweet(
                    text=post["content"],
                    media_ids=[self._upload_media(post["platform"], post["media"])]
                )
            elif post["platform"] == "Facebook":
                client.put_object(
                    parent_object="me",
                    connection_name="feed",
                    message=post["content"],
                    attached_media=[post["media"]]
                )
            post["status"] = "Published"
        except Exception as e:
            post["status"] = f"Failed: {str(e)}"

    def get_scheduled_posts(self, month=None):
        """Get posts filtered by month"""
        if not month:
            month = datetime.datetime.now().month
        return [p for p in self.scheduled_posts 
                if p['scheduled_time'].month == month]

    def analyze_sentiment(self, text):
        """Perform sentiment analysis using TextBlob"""
        analysis = TextBlob(text)
        if analysis.sentiment.polarity > 0.1:
            return "positive"
        elif analysis.sentiment.polarity < -0.1:
            return "negative"
        return "neutral"

class SocialPilotApp(ctk.CTk):
    """Modern Social Media Management Dashboard"""
    
    def __init__(self):
        super().__init__()
        self.manager = SocialMediaManager()
        self.current_month = datetime.datetime.now()
        
        self.title("SocialPilot Pro 🚀")
        self.geometry("1400x900")
        ctk.set_appearance_mode("Dark")
        
        self.status_bar = ctk.CTkLabel(self, text="Ready")
        self.status_bar.pack(side="bottom", fill="x", padx=5, pady=2)
        
        self._create_main_notebook()
        self._create_schedule_tab()
        self._create_calendar_tab()
        self._create_analytics_tab()
        self._create_credentials_tab()
        self._create_menu()

    def _create_main_notebook(self):
        """Create tabbed interface"""
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        
        self.schedule_frame = ctk.CTkFrame(self.notebook)
        self.calendar_frame = ctk.CTkFrame(self.notebook)
        self.analytics_frame = ctk.CTkFrame(self.notebook)
        self.credentials_frame = ctk.CTkFrame(self.notebook)  # New frame
        
        self.notebook.add(self.schedule_frame, text="Scheduling")
        self.notebook.add(self.calendar_frame, text="Content Calendar")
        self.notebook.add(self.analytics_frame, text="Analytics")
        self.notebook.add(self.credentials_frame, text="API Credentials")

    def _create_credentials_tab(self):
        """Create credentials management interface"""
        main_frame = ctk.CTkScrollableFrame(self.credentials_frame)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.credential_entries = {}
        for platform, keys in API_KEYS.items():
            frame = ctk.CTkFrame(main_frame)
            frame.pack(fill="x", pady=10)
            
            ctk.CTkLabel(frame, text=platform.title(), 
                        font=("Arial", 14, "bold")).pack()
            
            self.credential_entries[platform] = {}
            for key in keys:
                key_frame = ctk.CTkFrame(frame)
                key_frame.pack(fill="x", pady=2)
                
                ctk.CTkLabel(key_frame, text=key).pack(side="left", padx=5)
                entry = ctk.CTkEntry(key_frame, show="*")
                entry.pack(side="right", expand=True, fill="x", padx=5)
                
                saved_value = keyring.get_password(f"socialpilot_{platform}", key)
                if saved_value:
                    entry.insert(0, saved_value)
                    
                self.credential_entries[platform][key] = entry
        
        ctk.CTkButton(self.credentials_frame, 
                     text="Save & Apply Credentials",
                     command=self._save_credentials).pack(pady=10)
        
        self.status_label = ctk.CTkLabel(self.credentials_frame, 
                                        text="Status: Not connected")
        self.status_label.pack(pady=5)

    def _save_credentials(self):
        """Save and apply new credentials"""
        for platform, keys in self.credential_entries.items():
            for key, entry in keys.items():
                value = entry.get().strip()
                if value:
                    keyring.set_password(f"socialpilot_{platform}", key, value)
        
        if self.manager.setup_credentials():
            self.status_label.configure(
                text="Status: Connected successfully",
                text_color="green")
        else:
            self.status_label.configure(
                text="Status: Connection failed - check credentials",
                text_color="red")

    def _create_schedule_tab(self):
        self.platform_selector = ctk.CTkSegmentedButton(
            self.schedule_frame,
            values=PLATFORMS,
            command=self._change_platform
        )
        self.platform_selector.pack(pady=10, padx=20, fill="x")
        
        editor_panel = ctk.CTkFrame(self.schedule_frame)
        editor_panel.pack(fill="both", expand=True, padx=20)
        
        self.media_preview = ctk.CTkLabel(editor_panel, text="", width=300)
        self.media_preview.pack(side="left", padx=10)

        self.text_editor = ctk.CTkTextbox(editor_panel, wrap="word", font=("Arial", 12))
        self.text_editor.pack(side="right", fill="both", expand=True)

        self.platform_selector.set("X (Twitter)")
        
        control_frame = ctk.CTkFrame(self.schedule_frame)
        control_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkButton(
            control_frame,
            text="📁 Add Media",
            command=self._upload_media
        ).pack(side="left", padx=5)

        schedule_control_frame = ctk.CTkFrame(control_frame)
        schedule_control_frame.pack(side="right", padx=5)
        
        self.date_entry = ctk.CTkEntry(schedule_control_frame, placeholder_text="YYYY-MM-DD")
        self.date_entry.pack(side="left", padx=2)
        
        self.time_entry = ctk.CTkEntry(schedule_control_frame, placeholder_text="HH:MM")
        self.time_entry.pack(side="left", padx=2)
        
        ctk.CTkButton(
            schedule_control_frame,
            text="⏰ Schedule Post",
            command=self._schedule_post
        ).pack(side="left", padx=2)

    def _create_calendar_tab(self):
        """Content Calendar components"""
        # Calendar Controls
        control_frame = ctk.CTkFrame(self.calendar_frame)
        control_frame.pack(fill="x", padx=20, pady=10)
        
        self.prev_month_btn = ctk.CTkButton(
            control_frame,
            text="←",
            width=30,
            command=lambda: self._change_month(-1)
        )
        self.prev_month_btn.pack(side="left")
        
        self.month_label = ctk.CTkLabel(
            control_frame,
            text=self.current_month.strftime("%B %Y"),
            font=("Arial", 16)
        )
        self.month_label.pack(side="left", padx=20)
        
        self.next_month_btn = ctk.CTkButton(
            control_frame,
            text="→",
            width=30,
            command=lambda: self._change_month(1)
        )
        self.next_month_btn.pack(side="right")

        self.grid_frame = ctk.CTkFrame(self.calendar_frame)
        self.grid_frame.pack(fill="both", expand=True, padx=20, pady=10)
        self._draw_calendar()

    def _create_analytics_tab(self):
        """Analytics components"""
        sentiment_frame = ctk.CTkFrame(self.analytics_frame)
        sentiment_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.chart_canvas = ctk.CTkCanvas(sentiment_frame)
        self.chart_canvas.pack(fill="both", expand=True)
        
        ctk.CTkButton(
            sentiment_frame,
            text="🔄 Analyze Sentiment",
            command=self._run_sentiment_analysis
        ).pack(pady=10)

    def _create_menu(self):
        """Create main menu"""
        self.menu = tk.Menu(self)
        
        file_menu = tk.Menu(self.menu, tearoff=0)
        file_menu.add_command(label="Export Analytics", command=self._export_analytics)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        
        tools_menu = tk.Menu(self.menu, tearoff=0)
        tools_menu.add_command(label="AI Caption Generator", command=self._generate_ai_caption)
        tools_menu.add_command(label="Hashtag Optimizer", command=self._optimize_hashtags)
        
        self.menu.add_cascade(label="File", menu=file_menu)
        self.menu.add_cascade(label="Tools", menu=tools_menu)
        self.config(menu=self.menu)

    def _draw_calendar(self):
        """Draw calendar grid with posts"""
        for widget in self.grid_frame.winfo_children():
            widget.destroy()
            
        days = ["Sat", "Sun","Mon", "Tue", "Wed", "Thu", "Fri"]
        for col, day in enumerate(days):
            ctk.CTkLabel(self.grid_frame, text=day, width=100, height=30).grid(
                row=0, column=col, padx=2, pady=2
            )
            
        cal = calendar.monthcalendar(self.current_month.year, self.current_month.month)
        for week_num, week in enumerate(cal):
            for day_num, day in enumerate(week):
                if day == 0:
                    continue
                
                frame = ctk.CTkFrame(self.grid_frame, width=100, height=80)
                frame.grid(row=week_num+1, column=day_num, padx=2, pady=2)
                frame.grid_propagate(False)
                
                ctk.CTkLabel(frame, text=str(day)).pack()
                
                posts = self.manager.get_scheduled_posts(self.current_month.month)
                date_posts = [p for p in posts if p['scheduled_time'].day == day]
                
                if date_posts:
                    ctk.CTkLabel(frame, 
                               text=f"{len(date_posts)} posts",
                               font=("Arial", 10)).pack()

    def _change_month(self, delta):
        """Navigate between months"""
        self.current_month += relativedelta(months=delta)
        self.month_label.configure(text=self.current_month.strftime("%B %Y"))
        self._draw_calendar()

    def _schedule_post(self):
        """Handle post scheduling"""
        platform = self.platform_selector.get()
        content = self.text_editor.get("1.0", "end")
        schedule_time = self._parse_datetime()
        
        post = self.manager.schedule_post(
            platform=platform,
            content=content,
            schedule_time=schedule_time
        )
        self._update_status(f"Scheduled post for {platform} at {post['scheduled_time']}")

    def _parse_datetime(self):
        """Parse date and time from inputs"""
        date_str = self.date_entry.get() or datetime.date.today().isoformat()
        time_str = self.time_entry.get() or "12:00"
        return datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

    def _upload_media(self):
        """Handle media file selection"""
        filetypes = (
            ("Media Files", "*.jpg *.png *.mp4 *.mov"),
            ("All Files", "*.*")
        )
        
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            self._preview_media(path)

    def _preview_media(self, path):
        """Preview images only"""
        try:
            image = Image.open(path)
            image.thumbnail((300, 300))
            photo = ctk.CTkImage(light_image=image, dark_image=image, size=(300, 300))
            self.media_preview.configure(image=photo)
            self.media_preview.image = photo  # Keep reference
        except Exception as e:
            self._update_status(f"Error previewing media: {str(e)}")

    def _run_sentiment_analysis(self):
        """Analyze comment sentiment"""
        mock_comments = [
            "Fantastic content! Keep it up! 👍",
            "This could be improved",
            "Not my favorite post 😕",
            "Extremely useful information!",
            "Poor quality content 👎"
        ]
        
        results = {"positive": 0, "negative": 0, "neutral": 0}
        for comment in mock_comments:
            sentiment = self.manager.analyze_sentiment(comment)
            results[sentiment] += 1
            
        self._update_sentiment_chart(results)

    def _update_sentiment_chart(self, data):
        """Display sentiment analysis results"""
        fig = plt.Figure(figsize=(6, 4), dpi=100)
        ax = fig.add_subplot(111)
        ax.pie(
            data.values(),
            labels=data.keys(),
            autopct='%1.1f%%',
            colors=['#4CAF50', '#FF5252', '#FFC107'],
            startangle=90
        )
        ax.set_title("Comment Sentiment Analysis")
        
        for widget in self.chart_canvas.winfo_children():
            widget.destroy()
            
        canvas = FigureCanvasTkAgg(fig, self.chart_canvas)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def _generate_ai_caption(self):
        samples = [
            "Elevate your social presence with cutting-edge content! 💡",
            "Where innovation meets social engagement 🚀",
            "Crafting digital experiences that matter 🌐"
        ]
        self.text_editor.delete("1.0", "end")
        self.text_editor.insert("end", random.choice(samples))

    def _optimize_hashtags(self):
        """Optimize hashtags for current content"""
        current_text = self.text_editor.get("1.0", "end").strip()
        if current_text:
            hashtags = self.manager._generate_hashtags(current_text, n=5)
            if not any(tag in current_text for tag in hashtags.split()):
                self.text_editor.insert("end", f"\n\n{hashtags}")
        self._update_status("Hashtags optimized")

    def _update_status(self, message):
        """Update status bar with timestamp"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.status_bar.configure(text=f"[{timestamp}] {message}")

    def _export_analytics(self):
        """Export data to CSV"""
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")]
        )
        if path:
            df = pd.DataFrame(self.manager.scheduled_posts)
            df.to_csv(path, index=False)
            self._update_status(f"Exported analytics to {path}")

    def _change_platform(self, platform):
        """Handle platform change and update UI accordingly"""
        if hasattr(self, 'text_editor'):  
            self.text_editor.delete("1.0", "end")
        if hasattr(self, 'media_preview'):  
            self.media_preview.configure(image=None) 
        
        char_limits = {
            "Facebook": 2200,
            "X (Twitter)": 280,
            "LinkedIn": 3000,
            "TikTok": 150,
            "Snapchat": 100
        }
        limit = char_limits.get(platform, 2000)
        if hasattr(self, 'text_editor'):
            self.text_editor.configure(placeholder_text=f"Enter your content (max {limit} characters)...")

        media_supported = platform in ["Facebook", "X (Twitter)", "Instagram", "LinkedIn"]
        for widget in self.schedule_frame.winfo_children():
            if isinstance(widget, ctk.CTkFrame): 
                for child in widget.winfo_children():
                    if isinstance(child, ctk.CTkButton) and "Add Media" in str(child.cget("text")):
                        child.configure(state="normal" if media_supported else "disabled")

    def run(self):
        """Start the application"""
        try:
            self.mainloop()
        except Exception as e:
            print(f"Application error: {str(e)}")
            self.destroy()

if __name__ == "__main__":
    try:
        app = SocialPilotApp()
        app.run()
    except Exception as e:
        print(f"Failed to start application: {str(e)}")