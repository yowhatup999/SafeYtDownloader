"""
SafeYtDownloader
Author: yowhatup
Date: 2025-03-08
Description: A professional YouTube Video & Playlist Downloader using yt-dlp with a dynamic progress bar and debug mode.
"""

import os
import subprocess
import sys
import re
import threading
import queue

class SafeYtDownloader:
    """Handles video and playlist downloads with progress tracking and optional debug mode."""

    def __init__(self):
        self.default_path = os.path.expanduser("~/Documents/Music")
        self.save_path = self.default_path
        self.total_videos = 1
        self.completed_videos = 0
        self.progress_queue = queue.Queue()
        self.video_url = ""
        self.debug = False
        self.mode = self.get_user_choice()

    def log(self, message):
        if self.debug:
            print(f"[DEBUG] {message}")

    def get_user_choice(self):
        while True:
            choice = input("Select mode: (1) Single Video (2) Playlist (3) Exit (4) Enable Debugging: ").strip()
            if choice in ["1", "2", "4"]:
                if choice == "4":
                    self.debug = True
                    print("[INFO] Debug mode enabled.")
                return choice if choice != "4" else "1"
            elif choice == "3":
                print("[INFO] Exiting SafeYtDownloader...")
                sys.exit(0)
            print("[ERROR] Invalid input. Please enter 1, 2, 3, or 4.")

    def ensure_save_directory(self):
        os.makedirs(self.save_path, exist_ok=True)
        self.log(f"Save path: {self.save_path}")

    def get_desktop_path(self):
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        return desktop if os.path.isdir(desktop) else None

    def ask_output_path(self):
        desktop_path = self.get_desktop_path()
        print("\nSelect output path:")
        print(f"(1) Default → {self.default_path}")
        if desktop_path:
            print(f"(2) Desktop → {desktop_path}")
        choice = input("Choice (1 or 2): ").strip()
        if choice == "2" and desktop_path:
            self.save_path = desktop_path
        else:
            self.save_path = self.default_path
        self.ensure_save_directory()

    def get_playlist_length(self):
        self.log("Fetching playlist length...")
        info_command = [
            "yt-dlp", "--flat-playlist", "--print", "%(id)s", self.video_url
        ]
        try:
            result = subprocess.run(info_command, capture_output=True, text=True, check=True)
            playlist_length = len(result.stdout.strip().split("\n"))
            self.log(f"Playlist contains {playlist_length} videos.")
            return playlist_length
        except subprocess.CalledProcessError:
            print("[ERROR] Failed to retrieve playlist length.")
            sys.exit(1)

    def update_progress_bar(self):
        bar_length = 50
        while self.completed_videos < self.total_videos:
            self.completed_videos = self.progress_queue.get()
            progress = int((self.completed_videos / self.total_videos) * 100)
            filled_length = int(bar_length * progress / 100)
            bar = "#" * filled_length + "." * (bar_length - filled_length)
            sys.stdout.write(f"\r[INFO] Downloading... [{bar}] {progress}% ({self.completed_videos}/{self.total_videos}) ")
            sys.stdout.flush()
        sys.stdout.write(f"\r[INFO] Downloading... [{'#' * bar_length}] 100% ({self.total_videos}/{self.total_videos}) \n")
        sys.stdout.flush()

    def start_download(self):
        self.video_url = input("Enter YouTube URL: ").strip()
        if not self.video_url:
            print("[ERROR] No URL provided.")
            sys.exit(1)

        self.ask_output_path()

        if self.mode == "2":
            self.total_videos = self.get_playlist_length()

        self.log(f"Starting download for URL: {self.video_url}")
        threading.Thread(target=self.update_progress_bar, daemon=True).start()
        self.download()

    def download(self):
        command = [
            "yt-dlp", "--format", "bestaudio/best",
            "--extract-audio", "--audio-format", "mp3",
            "--audio-quality", "0", "--output",
            os.path.join(self.save_path, "%(title)s.%(ext)s"), self.video_url
        ]

        if self.debug:
            command.insert(1, "--verbose")

        self.log(f"Executing command: {' '.join(command)}")

        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for line in process.stdout:
                if self.debug:
                    self.log(f"yt-dlp output: {line.strip()}")
                if re.search(r"\[download\] Destination: .+", line):
                    self.completed_videos += 1
                    self.progress_queue.put(self.completed_videos)

            process.wait()
            if process.returncode != 0:
                print("[ERROR] Download process failed.")
                sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            sys.exit(1)

        print(f"\n[INFO] Download completed! MP3 files saved in: {self.save_path}")

if __name__ == "__main__":
    print("=== SafeYtDownloader ===")
    SafeYtDownloader().start_download()
