import customtkinter as ctk
import yt_dlp
import os
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox
from PIL import Image
import requests
from io import BytesIO
import subprocess
import platform
import re
import json

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")
SKY_BLUE, DARK_SKY_BLUE, LIGHT_SKY_BLUE, WHITE, LIGHT_GRAY, MEDIUM_GRAY, DARK_GRAY, BLUE_ACCENT = "#87CEEB", "#4682B4", "#B0E0E6", "#FFFFFF", "#F5F5F5", "#E0E0E0", "#808080", "#1E90FF"

class DownloadItem:
    def __init__(self, parent, url, title, quality, download_path, speed_limit=0, download_subtitles=False, file_pattern="%(title)s.%(ext)s"):
        self.url, self.title, self.quality, self.download_path, self.speed_limit, self.download_subtitles, self.file_pattern = url, title, quality, download_path, speed_limit, download_subtitles, file_pattern
        self.status, self.progress, self.speed, self.downloaded, self.total = "Waiting", 0.0, 0, 0, 0
        self.frame, self.ydl, self.download_thread, self.paused, self.cancelled, self.file_path = None, None, None, False, False, None
        self.create_widgets(parent)
    
    def create_widgets(self, parent):
        self.frame = ctk.CTkFrame(parent)
        self.frame.pack(fill="x", padx=4, pady=2)
        left_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True, padx=8, pady=6)
        self.status_icon = ctk.CTkLabel(left_frame, text="⏸", width=24, font=ctk.CTkFont(size=14))
        self.status_icon.pack(side="left", padx=(0, 8))
        title_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        title_frame.pack(side="left", fill="both", expand=True)
        self.title_label = ctk.CTkLabel(title_frame, text=self.title[:50] + "..." if len(self.title) > 50 else self.title, font=ctk.CTkFont(size=11), anchor="w")
        self.title_label.pack(anchor="w")
        self.details_label = ctk.CTkLabel(title_frame, text=f"Quality: {self.quality}", font=ctk.CTkFont(size=9), text_color="gray", anchor="w")
        self.details_label.pack(anchor="w")
        right_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        right_frame.pack(side="right", padx=8, pady=6)
        self.progress_label = ctk.CTkLabel(right_frame, text="0%", font=ctk.CTkFont(size=10, weight="bold"), width=50)
        self.progress_label.pack(side="right", padx=(8, 0))
        self.speed_label = ctk.CTkLabel(right_frame, text="0 KB/s", font=ctk.CTkFont(size=10), text_color=DARK_SKY_BLUE, width=80)
        self.speed_label.pack(side="right", padx=(8, 0))
        self.progress_bar = ctk.CTkProgressBar(self.frame)
        self.progress_bar.pack(fill="x", padx=8, pady=(0, 6))
        self.progress_bar.set(0)
        action_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        action_frame.pack(fill="x", padx=8, pady=(0, 6))
        self.pause_btn = ctk.CTkButton(action_frame, text="⏸ Pause", width=70, height=24, font=ctk.CTkFont(size=9), command=self.pause_download, fg_color="gray", hover_color="darkgray")
        self.pause_btn.pack(side="left", padx=2)
        self.resume_btn = ctk.CTkButton(action_frame, text="▶ Resume", width=70, height=24, font=ctk.CTkFont(size=9), command=self.resume_download, fg_color="green", hover_color="darkgreen")
        self.resume_btn.pack(side="left", padx=2)
        self.resume_btn.pack_forget()
        self.cancel_btn = ctk.CTkButton(action_frame, text="✖ Cancel", width=70, height=24, font=ctk.CTkFont(size=9), command=self.cancel_download, fg_color="red", hover_color="darkred")
        self.cancel_btn.pack(side="left", padx=2)
        self.retry_btn = ctk.CTkButton(action_frame, text="🔄 Retry", width=70, height=24, font=ctk.CTkFont(size=9), command=self.retry_download, fg_color="orange", hover_color="darkorange")
        self.retry_btn.pack(side="left", padx=2)
        self.retry_btn.pack_forget()
        self.open_location_btn = ctk.CTkButton(action_frame, text="📁 Open", width=70, height=24, font=ctk.CTkFont(size=9), command=self.open_location, fg_color=DARK_SKY_BLUE, hover_color=BLUE_ACCENT)
        self.open_location_btn.pack(side="left", padx=2)
        self.open_location_btn.pack_forget()
    
    def pause_download(self): self.paused, self.status = True, "Paused"; self.update_status("Paused"); self.pause_btn.pack_forget(); self.resume_btn.pack(side="left", padx=2)
    def resume_download(self): self.paused, self.status = False, "Downloading"; self.update_status("Downloading"); self.resume_btn.pack_forget(); self.pause_btn.pack(side="left", padx=2)
    def cancel_download(self):
        self.cancelled, self.paused = True, False
        if self.ydl:
            try: self.ydl.cancel()
            except: pass
        self.update_status("Cancelled")
        self.frame.pack_forget()
    def retry_download(self):
        self.cancelled, self.paused, self.progress = False, False, 0.0
        self.progress_bar.set(0)
        self.progress_label.configure(text="0%")
        self.update_status("Waiting")
        self.retry_btn.pack_forget()
        self.pause_btn.pack(side="left", padx=2)
        if hasattr(self, 'app'): self.app.start_download(self)
    def open_location(self):
        folder = os.path.dirname(self.file_path) if self.file_path and os.path.exists(self.file_path) else self.download_path
        if os.path.exists(folder):
            if platform.system() == "Windows": os.startfile(folder)
            elif platform.system() == "Darwin": subprocess.Popen(["open", folder])
            else: subprocess.Popen(["xdg-open", folder])
    def update_progress(self, percent, speed, downloaded, total):
        if self.cancelled or self.paused: return
        self.progress, self.speed, self.downloaded, self.total = percent, speed, downloaded, total
        self.progress_bar.set(percent)
        self.progress_label.configure(text=f"{percent * 100:.1f}%")
        speed_mb = speed / 1024 / 1024
        self.speed_label.configure(text=f"{speed_mb:.2f} MB/s" if speed_mb >= 1 else f"{speed / 1024:.0f} KB/s")
    def update_status(self, status):
        self.status = status
        icons = {"Waiting": "⏸", "Downloading": "⬇️", "Completed": "✅", "Error": "❌", "Paused": "⏸", "Cancelled": "🚫"}
        self.status_icon.configure(text=icons.get(status, "⏸"))
        for btn in [self.pause_btn, self.resume_btn, self.cancel_btn, self.retry_btn, self.open_location_btn]: btn.pack_forget()
        if status == "Completed": self.open_location_btn.pack(side="left", padx=2)
        elif status == "Error": self.retry_btn.pack(side="left", padx=2)
        elif status == "Paused": self.resume_btn.pack(side="left", padx=2)
        elif status == "Downloading": self.pause_btn.pack(side="left", padx=2)

class PlaylistSelectionWindow:
    def __init__(self, parent, playlist_url, app_instance):
        self.parent, self.playlist_url, self.app, self.video_checkboxes, self.playlist_info = parent, playlist_url, app_instance, {}, None
        self.window = ctk.CTkToplevel(parent)
        self.window.title("Select Videos from Playlist")
        self.window.geometry("1100x750")
        self.window.minsize(1000, 650)
        main_frame = ctk.CTkFrame(self.window)
        main_frame.pack(fill="both", expand=True, padx=8, pady=8)
        header_frame = ctk.CTkFrame(main_frame)
        header_frame.pack(fill="x", padx=8, pady=8)
        self.playlist_title_label = ctk.CTkLabel(header_frame, text="Loading playlist...", font=ctk.CTkFont(size=14, weight="bold"))
        self.playlist_title_label.pack(side="left", padx=8)
        selection_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        selection_frame.pack(side="right", padx=8)
        ctk.CTkButton(selection_frame, text="Select All", width=90, height=28, command=self.select_all, font=ctk.CTkFont(size=10)).pack(side="left", padx=2)
        ctk.CTkButton(selection_frame, text="Deselect All", width=90, height=28, command=self.deselect_all, font=ctk.CTkFont(size=10)).pack(side="left", padx=2)
        list_frame = ctk.CTkFrame(main_frame)
        list_frame.pack(fill="both", expand=True, padx=8, pady=8)
        self.video_list = ctk.CTkScrollableFrame(list_frame)
        self.video_list.pack(fill="both", expand=True, padx=4, pady=4)
        self.status_label = ctk.CTkLabel(main_frame, text="Fetching playlist videos...", font=ctk.CTkFont(size=11), text_color="gray")
        self.status_label.pack(pady=8)
        action_frame = ctk.CTkFrame(main_frame)
        action_frame.pack(fill="x", padx=8, pady=8)
        ctk.CTkButton(action_frame, text="Cancel", width=100, height=32, command=self.window.destroy, font=ctk.CTkFont(size=11)).pack(side="right", padx=8)
        self.download_btn = ctk.CTkButton(action_frame, text="Download Selected", width=150, height=32, command=self.download_selected, font=ctk.CTkFont(size=11, weight="bold"), fg_color="#1f6aa5", hover_color="#144870", state="disabled")
        self.download_btn.pack(side="right", padx=8)
        threading.Thread(target=self.fetch_playlist, daemon=True).start()
    
    def fetch_playlist(self):
        try:
            ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': True, 'extractor_args': {'youtube': {'player_client': ['android']}}}
            self.app._add_cookie_options(ydl_opts)
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(self.playlist_url, download=False)
            except Exception as e:
                if 'cookie' in str(e).lower() or 'cookiesfrombrowser' in str(e).lower():
                    ydl_opts.pop('cookiesfrombrowser', None)
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(self.playlist_url, download=False)
                else: raise
            self.playlist_info = {'title': info.get('title', 'Playlist'), 'entries': info.get('entries', [])}
            self.window.after(0, lambda: self.display_videos(self.playlist_info['title'], self.playlist_info['entries']))
        except: pass
    
    def display_videos(self, playlist_title, entries):
        self.playlist_title_label.configure(text=f"Playlist: {playlist_title}")
        self.status_label.configure(text=f"Found {len(entries)} videos")
        for idx, entry in enumerate(entries):
            if not entry: continue
            video_id, title, duration = entry.get('id', ''), entry.get('title', 'Unknown'), entry.get('duration', 0)
            url = f"https://www.youtube.com/watch?v={video_id}" if video_id else entry.get('url', '')
            if not url or 'youtube.com' not in url: continue
            video_frame = ctk.CTkFrame(self.video_list)
            video_frame.pack(fill="x", padx=4, pady=2)
            var = ctk.BooleanVar(value=True)
            ctk.CTkCheckBox(video_frame, text="", variable=var, width=20).pack(side="left", padx=8, pady=8)
            info_frame = ctk.CTkFrame(video_frame, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=8, pady=8)
            ctk.CTkLabel(info_frame, text=f"{idx + 1}. {title}", font=ctk.CTkFont(size=11), anchor="w").pack(anchor="w")
            duration_str = f"Duration: {duration // 60}:{duration % 60:02d}" if duration else "Duration: Unknown"
            ctk.CTkLabel(info_frame, text=duration_str, font=ctk.CTkFont(size=9), text_color="gray", anchor="w").pack(anchor="w")
            self.video_checkboxes[url] = {'var': var, 'title': title, 'frame': video_frame}
        self.download_btn.configure(state="normal")
    
    def select_all(self): [data['var'].set(True) for data in self.video_checkboxes.values()]
    def deselect_all(self): [data['var'].set(False) for data in self.video_checkboxes.values()]
    def download_selected(self):
        selected_videos = [{'url': url, 'title': data['title']} for url, data in self.video_checkboxes.items() if data['var'].get()]
        if not selected_videos: return
        quality, base_path = self.app.quality_var.get(), self.app.path_entry.get().strip() or self.app.download_path
        playlist_folder = os.path.join(base_path, re.sub(r'[<>:"/\\|?*]', '', self.playlist_info['title'] if self.playlist_info else "Playlist"))
        os.makedirs(playlist_folder, exist_ok=True)
        for video in selected_videos:
            download_item = DownloadItem(self.app.download_list_frame, video['url'], video['title'], quality, playlist_folder, float(self.app.speed_limit_var.get().strip() or "0"), self.app.subtitle_var.get(), self.app.file_pattern_var.get().strip() or "%(title)s.%(ext)s")
            download_item.app = self.app
            self.app.download_queue.append(download_item)
            if self.app.auto_start_var.get(): self.app.start_download(download_item)
        self.window.destroy()

class SettingsWindow:
    def __init__(self, parent, app_instance):
        self.parent, self.app, self.settings_file = parent, app_instance, os.path.join(Path.home(), ".youtube_downloader_settings.json")
        self.speed_modes = {"Normal": 0, "Slow": 1, "Moderate": 5, "Snail": 0.5}
        self.window = ctk.CTkToplevel(parent)
        self.window.title("Settings")
        self.window.geometry("600x700")
        self.window.minsize(550, 650)
        main_frame = ctk.CTkFrame(self.window)
        main_frame.pack(fill="both", expand=True, padx=12, pady=12)
        ctk.CTkLabel(main_frame, text="Settings", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(10, 20))
        speed_mode_frame = ctk.CTkFrame(main_frame)
        speed_mode_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(speed_mode_frame, text="Download Speed Mode", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(12, 8))
        ctk.CTkLabel(speed_mode_frame, text="Select a speed mode to control download bandwidth", font=ctk.CTkFont(size=10), text_color="gray").pack(pady=(0, 10))
        mode_buttons_frame = ctk.CTkFrame(speed_mode_frame, fg_color="transparent")
        mode_buttons_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.speed_mode_var = ctk.StringVar(value="Normal")
        modes = [("Normal", "Unlimited speed", "#1f6aa5"), ("Slow", "1 MB/s", "#7a4d2b"), ("Moderate", "5 MB/s", "#2b7a47"), ("Snail", "0.5 MB/s", "#7a2b2b")]
        self.mode_buttons = {}
        for mode, desc, color in modes:
            mode_frame = ctk.CTkFrame(mode_buttons_frame)
            mode_frame.pack(fill="x", padx=5, pady=5)
            radio = ctk.CTkRadioButton(mode_frame, text=f"{mode} - {desc}", variable=self.speed_mode_var, value=mode, font=ctk.CTkFont(size=11), command=lambda m=mode: self.apply_speed_mode(m))
            radio.pack(side="left", padx=10, pady=8)
            self.mode_buttons[mode] = radio
        custom_speed_frame = ctk.CTkFrame(main_frame)
        custom_speed_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(custom_speed_frame, text="Custom Speed Limit", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(12, 8))
        custom_speed_input_frame = ctk.CTkFrame(custom_speed_frame, fg_color="transparent")
        custom_speed_input_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.custom_speed_var = ctk.StringVar(value="0")
        custom_speed_entry = ctk.CTkEntry(custom_speed_input_frame, textvariable=self.custom_speed_var, width=120, height=32, font=ctk.CTkFont(size=11), placeholder_text="MB/s")
        custom_speed_entry.pack(side="left", padx=(0, 10))
        custom_speed_entry.bind("<KeyRelease>", lambda e: self.apply_custom_speed())
        ctk.CTkLabel(custom_speed_input_frame, text="(0 = unlimited, overrides speed mode)", font=ctk.CTkFont(size=10), text_color="gray").pack(side="left")
        concurrent_frame = ctk.CTkFrame(main_frame)
        concurrent_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(concurrent_frame, text="Maximum Concurrent Downloads", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(12, 8))
        ctk.CTkLabel(concurrent_frame, text="Number of downloads that can run simultaneously", font=ctk.CTkFont(size=10), text_color="gray").pack(pady=(0, 10))
        concurrent_input_frame = ctk.CTkFrame(concurrent_frame, fg_color="transparent")
        concurrent_input_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.max_concurrent_var = ctk.StringVar(value=str(self.app.max_concurrent))
        concurrent_entry = ctk.CTkEntry(concurrent_input_frame, textvariable=self.max_concurrent_var, width=80, height=32, font=ctk.CTkFont(size=11))
        concurrent_entry.pack(side="left", padx=(0, 10))
        concurrent_entry.bind("<KeyRelease>", lambda e: self.apply_max_concurrent())
        ctk.CTkLabel(concurrent_input_frame, text="simultaneous downloads (1-10 recommended)", font=ctk.CTkFont(size=10), text_color="gray").pack(side="left")
        autostart_frame = ctk.CTkFrame(main_frame)
        autostart_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(autostart_frame, text="Auto-start Downloads", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(12, 8))
        self.auto_start_var = ctk.BooleanVar(value=self.app.auto_start_var.get())
        ctk.CTkCheckBox(autostart_frame, text="Automatically start downloads when added to queue", variable=self.auto_start_var, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10, pady=(0, 10))
        location_frame = ctk.CTkFrame(main_frame)
        location_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(location_frame, text="Default Download Location", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(12, 8))
        location_input_frame = ctk.CTkFrame(location_frame, fg_color="transparent")
        location_input_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.default_location_var = ctk.StringVar(value=self.app.download_path)
        location_entry = ctk.CTkEntry(location_input_frame, textvariable=self.default_location_var, height=32, font=ctk.CTkFont(size=10))
        location_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(location_input_frame, text="Browse", width=100, height=32, command=self.browse_location, font=ctk.CTkFont(size=10)).pack(side="left")
        action_frame = ctk.CTkFrame(main_frame)
        action_frame.pack(fill="x", padx=10, pady=20)
        ctk.CTkButton(action_frame, text="Cancel", width=120, height=36, command=self.window.destroy, font=ctk.CTkFont(size=11)).pack(side="right", padx=10)
        ctk.CTkButton(action_frame, text="Save Settings", width=120, height=36, command=self.save_settings, font=ctk.CTkFont(size=11, weight="bold"), fg_color=DARK_SKY_BLUE, hover_color=BLUE_ACCENT).pack(side="right")
        self.load_settings()
    
    def apply_speed_mode(self, mode):
        speed_limit = self.speed_modes[mode]
        self.custom_speed_var.set("0" if speed_limit == 0 else str(speed_limit))
        self.app.speed_limit_var.set(str(speed_limit))
    def apply_custom_speed(self):
        speed = float(self.custom_speed_var.get() or "0")
        self.app.speed_limit_var.set(str(speed))
        if speed > 0: self.speed_mode_var.set("Normal")
    def apply_max_concurrent(self):
        max_val = max(1, min(10, int(self.max_concurrent_var.get() or "3")))
        self.max_concurrent_var.set(str(max_val))
        self.app.max_concurrent_var.set(str(max_val))
        self.app.max_concurrent = max_val
    def browse_location(self):
        folder = filedialog.askdirectory(initialdir=self.default_location_var.get())
        if folder: self.default_location_var.set(folder)
    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
                self.speed_mode_var.set(settings.get('speed_mode', 'Normal'))
                self.apply_speed_mode(self.speed_mode_var.get())
                self.custom_speed_var.set(str(settings.get('custom_speed', '0')))
                max_concurrent = settings.get('max_concurrent', 3)
                self.max_concurrent_var.set(str(max_concurrent))
                self.app.max_concurrent_var.set(str(max_concurrent))
                self.app.max_concurrent = max_concurrent
                self.auto_start_var.set(settings.get('auto_start', True))
                self.app.auto_start_var.set(self.auto_start_var.get())
                location = settings.get('default_location', str(Path.home() / "Downloads"))
                self.default_location_var.set(location)
                self.app.download_path = location
                self.app.path_entry.delete(0, "end")
                self.app.path_entry.insert(0, location)
    def save_settings(self):
        settings = {'speed_mode': self.speed_mode_var.get(), 'custom_speed': self.custom_speed_var.get(), 'max_concurrent': int(self.max_concurrent_var.get() or "3"), 'auto_start': self.auto_start_var.get(), 'default_location': self.default_location_var.get()}
        with open(self.settings_file, 'w') as f: json.dump(settings, f, indent=2)
        self.apply_custom_speed()
        self.apply_max_concurrent()
        self.app.auto_start_var.set(self.auto_start_var.get())
        self.app.download_path = self.default_location_var.get()
        self.app.path_entry.delete(0, "end")
        self.app.path_entry.insert(0, self.default_location_var.get())
        self.window.destroy()

class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader")
        self.root.geometry("1100x750")
        self.root.minsize(1000, 650)
        self.root.resizable(True, True)
        self.download_path, self.download_queue, self.active_downloads, self.video_cache, self.max_concurrent, self.auto_start = str(Path.home() / "Downloads"), [], {}, {}, 3, True
        self.create_toolbar()
        main_container = ctk.CTkFrame(root)
        main_container.pack(fill="both", expand=True, padx=4, pady=4)
        left_panel = ctk.CTkFrame(main_container)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 4))
        list_header = ctk.CTkFrame(left_panel)
        list_header.pack(fill="x", padx=4, pady=4)
        ctk.CTkLabel(list_header, text="Downloads", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=8)
        batch_frame = ctk.CTkFrame(list_header, fg_color="transparent")
        batch_frame.pack(side="right", padx=8)
        ctk.CTkButton(batch_frame, text="⏸ Pause All", width=80, height=26, font=ctk.CTkFont(size=9), command=self.pause_all, fg_color=MEDIUM_GRAY, hover_color=DARK_GRAY).pack(side="left", padx=2)
        ctk.CTkButton(batch_frame, text="▶ Resume All", width=80, height=26, font=ctk.CTkFont(size=9), command=self.resume_all, fg_color="#4CAF50", hover_color="#45a049").pack(side="left", padx=2)
        ctk.CTkButton(batch_frame, text="🗑 Clear Completed", width=110, height=26, font=ctk.CTkFont(size=9), command=self.clear_completed, fg_color="#FF9800", hover_color="#F57C00").pack(side="left", padx=2)
        self.download_list_frame = ctk.CTkScrollableFrame(left_panel)
        self.download_list_frame.pack(fill="both", expand=True, padx=4, pady=4)
        right_panel = ctk.CTkFrame(main_container, width=320)
        right_panel.pack(side="right", fill="y", padx=(4, 0))
        right_panel.pack_propagate(False)
        self.create_details_panel(right_panel)
        self.create_status_bar(root)
        self.load_settings_on_startup()
    
    def create_toolbar(self):
        toolbar = ctk.CTkFrame(self.root, height=50)
        toolbar.pack(fill="x", padx=4, pady=4)
        toolbar.pack_propagate(False)
        url_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        url_frame.pack(side="left", fill="x", expand=True, padx=8, pady=8)
        ctk.CTkLabel(url_frame, text="URL:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 6))
        self.url_entry = ctk.CTkEntry(url_frame, placeholder_text="Paste YouTube URL here...", height=32, font=ctk.CTkFont(size=11))
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.url_entry.bind("<Return>", lambda e: self.add_download())
        self.url_entry.bind("<KeyRelease>", lambda e: self.check_playlist_url())
        btn_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        btn_frame.pack(side="right", padx=8, pady=8)
        ctk.CTkButton(btn_frame, text="⚙️", width=40, height=32, command=self.open_settings, font=ctk.CTkFont(size=16), fg_color=SKY_BLUE, hover_color=DARK_SKY_BLUE, corner_radius=8).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="Preview", width=80, height=32, command=self.preview_video, font=ctk.CTkFont(size=10), fg_color=LIGHT_SKY_BLUE, hover_color=SKY_BLUE, text_color="#000000").pack(side="left", padx=4)
        self.playlist_btn = ctk.CTkButton(btn_frame, text="📋 Playlist Download", width=140, height=32, command=self.open_playlist_window, font=ctk.CTkFont(size=10, weight="bold"), fg_color=BLUE_ACCENT, hover_color=DARK_SKY_BLUE)
        self.playlist_btn.pack(side="left", padx=4)
        self.playlist_btn.pack_forget()
        self.mp3_btn = ctk.CTkButton(btn_frame, text="🎵 MP3", width=70, height=32, command=self.add_mp3_download, font=ctk.CTkFont(size=10, weight="bold"), fg_color="#9C27B0", hover_color="#7B1FA2")
        self.mp3_btn.pack(side="left", padx=4)
        self.download_btn = ctk.CTkButton(btn_frame, text="Download", width=100, height=32, command=self.add_download, font=ctk.CTkFont(size=11, weight="bold"), fg_color=DARK_SKY_BLUE, hover_color=BLUE_ACCENT)
        self.download_btn.pack(side="left", padx=4)
    
    def create_details_panel(self, parent):
        info_frame = ctk.CTkFrame(parent)
        info_frame.pack(fill="x", padx=8, pady=8)
        ctk.CTkLabel(info_frame, text="Video Information", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(8, 6))
        self.thumbnail_label = ctk.CTkLabel(info_frame, text="No preview", width=300, height=150, font=ctk.CTkFont(size=9), fg_color=LIGHT_SKY_BLUE, corner_radius=6, text_color=DARK_GRAY)
        self.thumbnail_label.pack(padx=8, pady=4)
        self.video_info_label = ctk.CTkLabel(info_frame, text="", font=ctk.CTkFont(size=9), wraplength=290, justify="left")
        self.video_info_label.pack(padx=8, pady=(4, 8))
        quality_frame = ctk.CTkFrame(parent)
        quality_frame.pack(fill="x", padx=8, pady=8)
        ctk.CTkLabel(quality_frame, text="Quality", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(8, 6))
        self.quality_var = ctk.StringVar(value="best")
        self.quality_container = ctk.CTkScrollableFrame(quality_frame, height=120)
        self.quality_container.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        ctk.CTkLabel(self.quality_container, text="Click Preview", font=ctk.CTkFont(size=9), text_color="gray").pack(pady=8)
        subtitle_frame = ctk.CTkFrame(parent)
        subtitle_frame.pack(fill="x", padx=8, pady=8)
        ctk.CTkLabel(subtitle_frame, text="Subtitles", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(8, 6))
        self.subtitle_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(subtitle_frame, text="Download subtitles (if available)", variable=self.subtitle_var, font=ctk.CTkFont(size=10)).pack(anchor="w", padx=8, pady=(0, 8))
        speed_frame = ctk.CTkFrame(parent)
        speed_frame.pack(fill="x", padx=8, pady=8)
        ctk.CTkLabel(speed_frame, text="Speed Limit", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(8, 6))
        speed_input_frame = ctk.CTkFrame(speed_frame, fg_color="transparent")
        speed_input_frame.pack(fill="x", padx=8, pady=(0, 8))
        self.speed_limit_var = ctk.StringVar(value="0")
        ctk.CTkEntry(speed_input_frame, textvariable=self.speed_limit_var, width=100, height=28, font=ctk.CTkFont(size=10), placeholder_text="MB/s").pack(side="left", padx=(0, 6))
        ctk.CTkLabel(speed_input_frame, text="(0 = unlimited)", font=ctk.CTkFont(size=9), text_color="gray").pack(side="left")
        pattern_frame = ctk.CTkFrame(parent)
        pattern_frame.pack(fill="x", padx=8, pady=8)
        ctk.CTkLabel(pattern_frame, text="File Naming", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(8, 6))
        self.file_pattern_var = ctk.StringVar(value="%(title)s.%(ext)s")
        ctk.CTkEntry(pattern_frame, textvariable=self.file_pattern_var, height=28, font=ctk.CTkFont(size=9), placeholder_text="%(title)s.%(ext)s").pack(fill="x", padx=8, pady=(0, 4))
        ctk.CTkLabel(pattern_frame, text="Variables: %(title)s, %(ext)s, %(id)s", font=ctk.CTkFont(size=8), text_color="gray").pack(anchor="w", padx=8, pady=(0, 8))
        concurrent_frame = ctk.CTkFrame(parent)
        concurrent_frame.pack(fill="x", padx=8, pady=8)
        ctk.CTkLabel(concurrent_frame, text="Max Concurrent Downloads", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(8, 6))
        concurrent_input_frame = ctk.CTkFrame(concurrent_frame, fg_color="transparent")
        concurrent_input_frame.pack(fill="x", padx=8, pady=(0, 8))
        self.max_concurrent_var = ctk.StringVar(value="3")
        ctk.CTkEntry(concurrent_input_frame, textvariable=self.max_concurrent_var, width=60, height=28, font=ctk.CTkFont(size=10)).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(concurrent_input_frame, text="simultaneous downloads", font=ctk.CTkFont(size=9), text_color="gray").pack(side="left")
        autostart_frame = ctk.CTkFrame(parent)
        autostart_frame.pack(fill="x", padx=8, pady=8)
        self.auto_start_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(autostart_frame, text="Auto-start downloads", variable=self.auto_start_var, font=ctk.CTkFont(size=10)).pack(anchor="w", padx=8, pady=(0, 8))
        location_frame = ctk.CTkFrame(parent)
        location_frame.pack(fill="x", padx=8, pady=8)
        ctk.CTkLabel(location_frame, text="Download Location", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(8, 6))
        self.path_entry = ctk.CTkEntry(location_frame, placeholder_text=self.download_path, height=32, font=ctk.CTkFont(size=10))
        self.path_entry.pack(fill="x", padx=8, pady=(0, 6))
        self.path_entry.insert(0, self.download_path)
        ctk.CTkButton(location_frame, text="Browse", width=100, height=28, command=self.browse_folder, font=ctk.CTkFont(size=10)).pack(padx=8, pady=(0, 8))
    
    def create_status_bar(self, parent):
        status_bar = ctk.CTkFrame(parent, height=30)
        status_bar.pack(fill="x", side="bottom", padx=4, pady=4)
        status_bar.pack_propagate(False)
        self.status_label = ctk.CTkLabel(status_bar, text="Ready", font=ctk.CTkFont(size=10), anchor="w")
        self.status_label.pack(side="left", padx=8, pady=6)
        self.total_speed_label = ctk.CTkLabel(status_bar, text="Speed: 0 KB/s", font=ctk.CTkFont(size=10), text_color=DARK_SKY_BLUE)
        self.total_speed_label.pack(side="right", padx=8, pady=6)
    
    def update_max_concurrent(self): self.max_concurrent = max(1, int(self.max_concurrent_var.get() or "3"))
    def pause_all(self): [item.pause_download() for item in self.download_queue if item.status == "Downloading"]
    def resume_all(self):
        for item in self.download_queue:
            if item.status == "Paused":
                item.resume_download()
                if not item.download_thread or not item.download_thread.is_alive():
                    self.start_download(item)
    def clear_completed(self):
        to_remove = [item for item in self.download_queue if item.status == "Completed"]
        for item in to_remove: item.frame.pack_forget(); self.download_queue.remove(item)
        self.update_status_bar()
    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.download_path)
        if folder:
            self.download_path = folder
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, folder)
    def _add_cookie_options(self, ydl_opts):
        ydl_opts['cookiesfrombrowser'] = ('edge',)
    
    def _extract_video_id(self, url):
        try:
            if 'youtu.be/' in url: return url.split('youtu.be/')[1].split('?')[0].split('&')[0]
            elif 'watch?v=' in url: return url.split('watch?v=')[1].split('&')[0].split('?')[0]
        except: pass
        return None
    
    def preview_video(self):
        url = self.url_entry.get().strip()
        if not url: return
        video_id = self._extract_video_id(url)
        if video_id and video_id in self.video_cache:
            self._update_preview(self.video_cache[video_id])
            return
        self.thumbnail_label.configure(text="Loading...", image=None)
        threading.Thread(target=self._fetch_preview_thread, args=(url,), daemon=True).start()
    
    def _fetch_preview_thread(self, url):
        try:
            video_id = self._extract_video_id(url)
            ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True, 'noplaylist': True, 'extractor_args': {'youtube': {'player_client': ['android']}}}
            self._add_cookie_options(ydl_opts)
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
            except Exception as e:
                if 'cookie' in str(e).lower() or 'cookiesfrombrowser' in str(e).lower():
                    ydl_opts.pop('cookiesfrombrowser', None)
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                else: raise
            thumbnail_url = info.get('thumbnail', '') or (info.get('thumbnails', [{}])[0].get('url', '') if info.get('thumbnails') else '')
            title, duration, uploader, views = info.get('title', 'Unknown'), info.get('duration', 0), info.get('uploader', 'Unknown'), info.get('view_count', 0)
            duration_str = f"{duration // 60}:{duration % 60:02d}"
            formats, available_formats = info.get('formats', []), self._parse_formats(formats)
            thumbnail_image = None
            if thumbnail_url:
                try:
                    img = Image.open(BytesIO(requests.get(thumbnail_url, timeout=3, stream=False).content))
                    img.thumbnail((300, 150), Image.Resampling.BILINEAR)
                    thumbnail_image = ctk.CTkImage(light_image=img, dark_image=img, size=(300, 150))
                except: pass
            if video_id:
                self.video_cache[video_id] = {'thumbnail_image': thumbnail_image, 'formats': available_formats, 'info': {'title': title, 'duration': duration_str, 'uploader': uploader, 'views': views}}
                if len(self.video_cache) > 10: del self.video_cache[next(iter(self.video_cache))]
            self.root.after(0, lambda: self._update_preview({'thumbnail_image': thumbnail_image, 'formats': available_formats, 'info': {'title': title, 'duration': duration_str, 'uploader': uploader, 'views': views}}))
        except: pass
    
    def _update_preview(self, data):
        thumbnail_image = data.get('thumbnail_image')
        if thumbnail_image: self.thumbnail_label.configure(image=thumbnail_image, text="")
        else: self.thumbnail_label.configure(text="No preview", image=None)
        info = data.get('info', {})
        title, duration, uploader, views = info.get('title', 'Unknown'), info.get('duration', '0:00'), info.get('uploader', 'Unknown'), info.get('views', 0)
        info_text = f"Title: {title}\nDuration: {duration}\nChannel: {uploader}\n"
        if views: info_text += f"Views: {views:,}" if views < 1000000 else f"Views: {views/1000000:.1f}M"
        self.video_info_label.configure(text=info_text)
        self._update_quality_options(data.get('formats', {}))
    
    def _parse_formats(self, formats):
        available = {'best': {'label': 'Best Quality', 'format_id': 'best', 'height': 0, 'ext': 'mp4'}}
        if any(f.get('acodec') != 'none' and f.get('vcodec') == 'none' for f in formats): available['audio'] = {'label': 'Audio Only (MP3)', 'format_id': 'bestaudio/best', 'height': 0, 'ext': 'mp3'}
        video_formats = {}
        for f in formats:
            vcodec, height = f.get('vcodec', 'none'), f.get('height')
            if vcodec != 'none' and vcodec and height:
                resolution = f"{height}p"
                if resolution not in video_formats:
                    ext, fps = f.get('ext', 'mp4'), f.get('fps', 0)
                    label = resolution + (f' @ {int(fps)}fps' if fps else '') + f' ({ext.upper()})'
                    video_formats[resolution] = {'height': height, 'format_id': f.get('format_id', ''), 'ext': ext, 'fps': fps, 'label': label}
        if video_formats: available.update(dict(sorted(video_formats.items(), key=lambda x: x[1]['height'])))
        return available
    
    def _update_quality_options(self, available_formats):
        for widget in self.quality_container.winfo_children(): widget.destroy()
        if not available_formats: ctk.CTkLabel(self.quality_container, text="No formats", font=ctk.CTkFont(size=9), text_color="gray").pack(pady=8); return
        if 'best' in available_formats: ctk.CTkRadioButton(self.quality_container, text=available_formats['best']['label'], variable=self.quality_var, value='best', font=ctk.CTkFont(size=10)).pack(anchor="w", padx=4, pady=2)
        if 'audio' in available_formats: ctk.CTkRadioButton(self.quality_container, text=available_formats['audio']['label'], variable=self.quality_var, value='audio', font=ctk.CTkFont(size=10)).pack(anchor="w", padx=4, pady=2)
        video_formats = {k: v for k, v in available_formats.items() if k not in ['best', 'audio']}
        for res, details in sorted(video_formats.items(), key=lambda x: x[1].get('height', 0)):
            ctk.CTkRadioButton(self.quality_container, text=details['label'], variable=self.quality_var, value=res, font=ctk.CTkFont(size=10)).pack(anchor="w", padx=4, pady=2)
    
    def add_download(self):
        url = self.url_entry.get().strip()
        if not url: return
        video_id = self._extract_video_id(url)
        title = self.video_cache[video_id]['info'].get('title', 'Video') if video_id and video_id in self.video_cache else "Video"
        download_item = DownloadItem(self.download_list_frame, url, title, self.quality_var.get(), self.path_entry.get().strip() or self.download_path, float(self.speed_limit_var.get().strip() or "0"), self.subtitle_var.get(), self.file_pattern_var.get().strip() or "%(title)s.%(ext)s")
        download_item.app = self
        self.download_queue.append(download_item)
        if self.auto_start_var.get(): self.start_download(download_item)
        self.url_entry.delete(0, "end")
    
    def add_mp3_download(self):
        url = self.url_entry.get().strip()
        if not url: return
        video_id = self._extract_video_id(url)
        title = self.video_cache[video_id]['info'].get('title', 'Video') if video_id and video_id in self.video_cache else "Video"
        pattern = self.file_pattern_var.get().strip() or "%(title)s.%(ext)s"
        if '.%(ext)s' in pattern: pattern = pattern.replace('.%(ext)s', '.mp3')
        download_item = DownloadItem(self.download_list_frame, url, title, "audio", self.path_entry.get().strip() or self.download_path, float(self.speed_limit_var.get().strip() or "0"), False, pattern)
        download_item.app = self
        self.download_queue.append(download_item)
        if self.auto_start_var.get(): self.start_download(download_item)
        self.url_entry.delete(0, "end")
    
    def start_download(self, download_item):
        if sum(1 for item in self.download_queue if item.status == "Downloading") >= self.max_concurrent:
            download_item.update_status("Waiting")
            return
        download_item.update_status("Downloading")
        download_item.download_thread = threading.Thread(target=self.download_video, args=(download_item,), daemon=True)
        download_item.download_thread.start()
    
    def download_video(self, download_item):
        while download_item.paused and not download_item.cancelled: threading.Event().wait(0.5)
        if download_item.cancelled: return
        os.makedirs(download_item.download_path, exist_ok=True)
        ydl_opts = {'outtmpl': os.path.join(download_item.download_path, download_item.file_pattern), 'progress_hooks': [lambda d: self.progress_hook(d, download_item)], 'noplaylist': True, 'concurrent_fragment_downloads': 4, 'http_chunk_size': 10485760}
        self._add_cookie_options(ydl_opts)
        if download_item.speed_limit > 0: ydl_opts['ratelimit'] = int(download_item.speed_limit * 1024 * 1024)
        if download_item.download_subtitles: ydl_opts.update({'writesubtitles': True, 'writeautomaticsub': True, 'subtitleslangs': ['en', 'en-US', 'en-GB'], 'subtitlesformat': 'srt'})
        quality = download_item.quality
        if quality == "best": ydl_opts['format'] = 'best[ext=mp4]/best'
        elif quality == "audio": ydl_opts['format'] = 'bestaudio/best'; ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
        else:
            video_id = self._extract_video_id(download_item.url)
            if video_id and video_id in self.video_cache:
                formats = self.video_cache[video_id].get('formats', {})
                if quality in formats:
                    height, ext = formats[quality].get('height', 0), formats[quality].get('ext', 'mp4')
                    ydl_opts['format'] = f'best[height={height}][ext={ext}]/best[height={height}]/best' if height else 'best[ext=mp4]/best'
                else: ydl_opts['format'] = 'best[ext=mp4]/best'
            else: ydl_opts['format'] = 'best[ext=mp4]/best'
        try:
            download_item.ydl = yt_dlp.YoutubeDL(ydl_opts)
            info = download_item.ydl.extract_info(download_item.url, download=False)
        except Exception as e:
            if 'cookie' in str(e).lower() or 'cookiesfrombrowser' in str(e).lower():
                ydl_opts.pop('cookiesfrombrowser', None)
                download_item.ydl = yt_dlp.YoutubeDL(ydl_opts)
                info = download_item.ydl.extract_info(download_item.url, download=False)
            else: raise
        filename = download_item.file_pattern.replace('%(title)s', info.get('title', 'Video')).replace('%(ext)s', info.get('ext', 'mp4')).replace('%(id)s', info.get('id', ''))
        download_item.file_path = os.path.join(download_item.download_path, filename)
        try:
            download_item.ydl.download([download_item.url])
            if not download_item.cancelled: download_item.update_status("Completed"); self.root.after(0, lambda: self.update_status_bar())
        except:
            if not download_item.cancelled: download_item.update_status("Error")
        finally: download_item.ydl = None
    
    def progress_hook(self, d, download_item):
        if download_item.cancelled: return
        while download_item.paused and not download_item.cancelled: threading.Event().wait(0.1)
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            if total > 0:
                download_item.update_progress(d.get('downloaded_bytes', 0) / total, d.get('speed', 0), d.get('downloaded_bytes', 0), total)
                self.root.after(0, lambda: self.update_status_bar())
        elif d['status'] == 'finished':
            download_item.update_progress(1.0, 0, download_item.total, download_item.total)
            download_item.update_status("Completed")
            self.root.after(0, lambda: self.update_status_bar())
            waiting_items = [item for item in self.download_queue if item.status == "Waiting"]
            if waiting_items: self.start_download(waiting_items[0])
    
    def update_status_bar(self):
        total_speed = sum(item.speed for item in self.download_queue if item.status == "Downloading")
        if total_speed:
            speed_mb = total_speed / 1024 / 1024
            self.total_speed_label.configure(text=f"Speed: {speed_mb:.2f} MB/s" if speed_mb >= 1 else f"Speed: {total_speed / 1024:.0f} KB/s")
        else: self.total_speed_label.configure(text="Speed: 0 KB/s")
        active_count = sum(1 for item in self.download_queue if item.status == "Downloading")
        waiting_count = sum(1 for item in self.download_queue if item.status == "Waiting")
        completed_count = sum(1 for item in self.download_queue if item.status == "Completed")
        status_parts = []
        if active_count > 0: status_parts.append(f"Downloading: {active_count}")
        if waiting_count > 0: status_parts.append(f"Waiting: {waiting_count}")
        if completed_count > 0: status_parts.append(f"Completed: {completed_count}")
        self.status_label.configure(text=" | ".join(status_parts) if status_parts else "Ready")
    
    def is_playlist_url(self, url): return 'list=' in url or '/playlist' in url
    def check_playlist_url(self):
        url = self.url_entry.get().strip()
        if self.is_playlist_url(url): self.playlist_btn.pack(side="left", padx=4, before=self.download_btn)
        else: self.playlist_btn.pack_forget()
    def open_playlist_window(self):
        url = self.url_entry.get().strip()
        if not url: return
        playlist_url = f"https://www.youtube.com/playlist?list={url.split('list=')[1].split('&')[0].split('?')[0]}" if 'list=' in url else url
        PlaylistSelectionWindow(self.root, playlist_url, self)
    def open_settings(self): SettingsWindow(self.root, self)
    def load_settings_on_startup(self):
        settings_file = os.path.join(Path.home(), ".youtube_downloader_settings.json")
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                self.speed_limit_var.set(str(settings.get('custom_speed', '0')))
                self.max_concurrent = settings.get('max_concurrent', 3)
                self.max_concurrent_var.set(str(self.max_concurrent))
                self.auto_start_var.set(settings.get('auto_start', True))
                location = settings.get('default_location', str(Path.home() / "Downloads"))
                self.download_path = location
                self.path_entry.delete(0, "end")
                self.path_entry.insert(0, location)

def download_from_cli(url, download_path=None):
    download_path = download_path or str(Path.home() / "Downloads")
    os.makedirs(download_path, exist_ok=True)
    if 'list=' in url:
        if 'youtu.be/' in url: url = f"https://www.youtube.com/watch?v={url.split('youtu.be/')[1].split('?')[0].split('&')[0]}"
        elif 'watch?v=' in url: url = f"https://www.youtube.com/watch?v={url.split('watch?v=')[1].split('&')[0].split('?')[0]}"
    ydl_opts = {'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'), 'format': 'best[ext=mp4]/best', 'noplaylist': True, 'concurrent_fragment_downloads': 4, 'http_chunk_size': 10485760}
    browsers = ['edge', 'firefox', 'chrome', 'opera', 'brave', 'safari']
    for browser in browsers:
        try: ydl_opts['cookiesfrombrowser'] = (browser,); break
        except: pass
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
    except Exception as e:
        if 'cookie' in str(e).lower() or 'cookiesfrombrowser' in str(e).lower():
            ydl_opts.pop('cookiesfrombrowser', None)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
        else: raise

def main():
    if len(sys.argv) > 1: download_from_cli(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None); return
    root = ctk.CTk()
    app = YouTubeDownloader(root)
    root.mainloop()

if __name__ == "__main__": main()
