import yt_dlp as youtube_dl
import subprocess
import threading
from queue import Queue
import time

class MusicPlayer:
    def __init__(self):
        self.current_process = None
        self.server_address = "link.zeno.fm" 
        self.port = "80"  
        self.mount_point = "y5lyosppxfxvv" 
        self.username = "source"
        self.password = "zHF3sKWM"
        self.encoding = "mp3" 
        self.song_queue = Queue() 
        self.is_playing = False 
        self.should_stop = False 
        self.retries = 3  

    def play_music(self, url):
        """Adds a song URL to the queue and starts playing if not already playing."""
        self.song_queue.put(url)
        print(f"Added {url} to the queue.")
        if not self.is_playing: 
            self._play_next_song()

    def _play_next_song(self):
        """Internal method to play the next song in the queue."""
        if self.song_queue.empty():
            self.is_playing = False
            print("No more songs in the queue.")
            return

        url = self.song_queue.get()
        print(f"Now playing: {url}")
        self.is_playing = True
        self.should_stop = False

        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': False,  
            'noplaylist': True,
        }

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                audio_url = info['url']
                print(f"Extracted audio URL: {audio_url}")

                icecast_url = f"icecast://{self.username}:{self.password}@{self.server_address}:{self.port}/{self.mount_point}"
                print(f"Icecast URL: {icecast_url}")

                self.current_process = subprocess.Popen([
                    'ffmpeg',
                    '-i', audio_url,  
                    '-vn',  
                    '-acodec', 'libmp3lame', 
                    '-ar', '44100', 
                    '-ac', '2',  
                    '-b:a', '128k',  
                    '-content_type', 'audio/mpeg',  
                    '-f', 'mp3', 
                    icecast_url 
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

                monitor_thread = threading.Thread(target=self._monitor_stream)
                monitor_thread.start()

        except Exception as e:
            print(f"An error occurred while trying to stream to Zeno FM: {e}")
            self.is_playing = False 

    def _monitor_stream(self):
        """Monitors the stream and plays the next song after the current one finishes."""
        while True:
    
            if self.current_process is None:
                break

            if self.current_process.poll() is not None:
                print("Streaming process finished or terminated.")
                break

            if self.should_stop:
                self.stop_music()
                return  

            stdout_line = self.current_process.stdout.readline()
            if stdout_line:
                print(f"FFmpeg output: {stdout_line.strip()}")
            stderr_line = self.current_process.stderr.readline()
            if stderr_line:
                print(f"FFmpeg error: {stderr_line.strip()}")

            time.sleep(1) 

        if self.current_process and not self.should_stop:  
            self._play_next_song()

    def stop_music(self):
        """Stops the currently playing music and clears the queue."""
        self.should_stop = True  

        if self.current_process:
            self.current_process.terminate() 
            self.current_process.wait() 
            print("Stopped streaming to Zeno FM.")
            self.current_process = None

        self.is_playing = False
        self.should_stop = False

        with self.song_queue.mutex:
            self.song_queue.queue.clear()  
        print("Queue cleared.")
