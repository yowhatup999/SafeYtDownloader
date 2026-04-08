"""
SafeYtDownloader
Author: yowhatup
Date: 2025-03-08
Description: A professional YouTube Video & Playlist Downloader using yt-dlp with a dynamic progress bar and debug mode.
"""

import subprocess
import sys
import re
import threading
import queue
from pathlib import Path

class SafeYtDownloader:
    """Handles video and playlist downloads with progress tracking and optional debug mode."""

    def __init__(self):
        self.default_path = Path.home() / "Documents" / "Music"
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

    def sanitize_filename(self, name):
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        return name[:100] if name else "Download"

    def get_video_title(self):
        self.log("Fetching video title...")
        command = ["yt-dlp", "--print", "%(title)s", self.video_url]

        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            title = result.stdout.strip().split("\n")[0]
            clean_title = self.sanitize_filename(title)
            self.log(f"Video title: {clean_title}")
            return clean_title
        except subprocess.CalledProcessError:
            print("[ERROR] Failed to retrieve video title.")
            sys.exit(1)

    def get_playlist_title(self):
        self.log("Fetching playlist title...")
        command = ["yt-dlp", "--flat-playlist", "--print", "%(playlist_title)s", self.video_url]

        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            if not lines:
                print("[ERROR] Failed to retrieve playlist title.")
                sys.exit(1)

            playlist_title = self.sanitize_filename(lines[0])
            self.log(f"Playlist title: {playlist_title}")
            return playlist_title
        except subprocess.CalledProcessError:
            print("[ERROR] Failed to retrieve playlist title.")
            sys.exit(1)

    def create_download_subfolder(self):
        if self.mode == "2":
            folder_name = self.get_playlist_title()
            self.save_path = Path(self.save_path) / folder_name
            self.ensure_save_directory()
            self.log(f"Final download folder: {self.save_path}")

    def get_user_choice(self):
        while True:
            choice = input("Select mode:\n(1) Single Video\n(2) Playlist\n(3) Exit\n(4) Toggle Debug\n: ").strip()

            if choice == "4":
                self.debug = not self.debug
                print(f"[INFO] Debug mode {'enabled' if self.debug else 'disabled'}.")
                continue

            if choice in ["1", "2"]:
                return choice

            if choice == "3":
                print("[INFO] Exiting SafeYtDownloader...")
                sys.exit(0)

            print("[ERROR] Invalid input. Please enter 1, 2, 3, or 4.")

    def ensure_save_directory(self):
        Path(self.save_path).mkdir(parents=True, exist_ok=True)
        self.log(f"Save path: {self.save_path}")

    def get_desktop_path(self):
        desktop = Path.home() / "Desktop"
        return desktop if desktop.is_dir() else None

    def ask_output_path(self):
        desktop_path = self.get_desktop_path()

        print("\nSelect output path:")
        print(f"(1) Default → {self.default_path}")
        if desktop_path:
            print(f"(2) Desktop → {desktop_path}")
        print("(3) Custom Path")

        while True:
            choice = input("Choice (1, 2, or 3): ").strip()

            if choice == "1":
                self.save_path = self.default_path
                break

            elif choice == "2" and desktop_path:
                self.save_path = desktop_path
                break

            elif choice == "3":
                custom_path = input("Paste full path: ").strip().strip('"')
                if not custom_path:
                    print("[ERROR] No custom path provided.")
                    continue

                self.save_path = Path(custom_path)
                break

            else:
                print("[ERROR] Invalid choice. Please enter 1, 2, or 3.")

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
        current = 0

        while current < self.total_videos:
            current = self.progress_queue.get()
            progress = int((current / self.total_videos) * 100)
            filled_length = int(bar_length * progress / 100)
            bar = "#" * filled_length + "." * (bar_length - filled_length)
            sys.stdout.write(f"\r[INFO] Downloading... [{bar}] {progress}% ({current}/{self.total_videos}) ")
            sys.stdout.flush()

        sys.stdout.write(
            f"\r[INFO] Downloading... [{'#' * bar_length}] 100% ({self.total_videos}/{self.total_videos}) \n")
        sys.stdout.flush()

    def start_download(self):
        self.video_url = input("Enter YouTube URL: ").strip()
        if not self.video_url:
            print("[ERROR] No URL provided.")
            sys.exit(1)

        self.ask_output_path()

        if self.mode == "2":
            self.total_videos = self.get_playlist_length()

        self.create_download_subfolder()

        self.log(f"Starting download for URL: {self.video_url}")
        sys.stdout.write(f"Starting download for URL: {self.video_url}")

        threading.Thread(target=self.update_progress_bar, daemon=True).start()
        self.download()

    def download(self):
        command = [
            "yt-dlp",
            "--ignore-errors",
            "--no-abort-on-error",
            "--format", "bestaudio",
            "--extract-audio", "--audio-format", "mp3",
            "--audio-quality", "0",
            "--output", str(Path(self.save_path) / "%(title)s.%(ext)s"),
            self.video_url
        ]

        if self.debug:
            command.insert(1, "--verbose")

        self.log(f"Executing command: {' '.join(command)}")

        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:

                line = line.strip()
                if "Downloading item" in line:
                    print(f"[INFO] {line}")
                if "ERROR:" in line:
                    print(f"[YT-DLP ERROR] {line}")
                if "WARNING:" in line:
                    print(f"[YT-DLP WARNING] {line}")

                if self.debug:
                    self.log(f"yt-dlp output: {line}")
                if "[ExtractAudio]" in line:
                    self.completed_videos += 1
                    self.progress_queue.put(self.completed_videos)

            process.wait()

            if process.returncode != 0:
                print("\n[WARNING] Some playlist items failed. Check messages above.")
            else:
                print(f"\n[INFO] Download completed! MP3 files saved in: {self.save_path}")
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    print("=== SafeYtDownloader ===")
    SafeYtDownloader().start_download()
