import yt_dlp as youtube_dl
import subprocess
import threading
from queue import Queue
import time

class MusicPlayer:
    def __init__(self):
        self.current_process = None
        self.server_address = "link.zeno.fm"  # Icecast server address
        self.port = "80"  # Icecast server port
        self.mount_point = "y5lyosppxfxvv"  # Updated mount point from your provided URL
        self.username = "source"
        self.password = "zHF3sKWM"
        self.encoding = "mp3"  # Use 'mp3' or 'aac' based on your requirement
        self.song_queue = Queue()  # Queue to hold songs
        self.is_playing = False  # Flag to check if music is currently playing
        self.should_stop = False  # Flag to check if stop has been requested
        self.retries = 3  # Number of reconnection attempts

    def play_music(self, url):
        """Adds a song URL to the queue and starts playing if not already playing."""
        self.song_queue.put(url)
        print(f"Added {url} to the queue.")
        if not self.is_playing:  # Only start playing if no song is currently playing
            self._play_next_song()

    def _play_next_song(self):
        """Internal method to play the next song in the queue."""
        if self.song_queue.empty():
            self.is_playing = False
            print("No more songs in the queue.")
            return

        # Get the next song URL from the queue
        url = self.song_queue.get()
        print(f"Now playing: {url}")
        self.is_playing = True
        self.should_stop = False

        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': True,
        }

        try:
            # Extract the YouTube audio URL
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                audio_url = info['url']

                # Construct the Icecast streaming URL correctly
                icecast_url = f"icecast://{self.username}:{self.password}@{self.server_address}:{self.port}/{self.mount_point}"

                # Start streaming to the Icecast server using ffmpeg
                self.current_process = subprocess.Popen([
                    'ffmpeg',
                    '-re',  # Read input at native frame rate
                    '-i', audio_url,  # Input source
                    '-acodec', 'libmp3lame' if self.encoding == "mp3" else 'aac',  # Audio codec
                    '-ar', '44100',  # Set audio sampling rate to 44.1kHz, common for streaming
                    '-ac', '2',  # Set number of audio channels to 2 (stereo)
                    '-b:a', '128k',  # Audio bitrate
                    '-content_type', f'audio/{self.encoding}',  # Set the content type
                    '-f', 'mp3' if self.encoding == "mp3" else 'adts',  # Output format (mp3 or aac)
                    icecast_url  # Zeno FM Icecast ingest URL
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

                # Monitor the output in a separate thread to handle stop requests and disconnections
                monitor_thread = threading.Thread(target=self._monitor_stream)
                monitor_thread.start()

        except Exception as e:
            print(f"An error occurred while trying to stream to Zeno FM: {e}")
            self.is_playing = False  # Ensure we can continue with the queue even if an error occurs

    def _monitor_stream(self):
        """Monitors the stream and plays the next song after the current one finishes."""
        while True:
            if self.current_process.poll() is not None:  # Process has finished
                break

            # If a stop is requested, terminate the stream and break
            if self.should_stop:
                self.stop_music()
                break

            time.sleep(1)  # Add some delay to avoid excessive CPU usage

        if self.current_process.poll() is not None:  # Process crashed
            print("The stream process terminated unexpectedly.")
            self._retry_stream()

        # After the current song finishes, move to the next one
        if not self.should_stop:  # Only play the next if stop wasn't requested
            self._play_next_song()

    def _retry_stream(self):
        """Handles retrying the stream in case of failure."""
        retries_left = self.retries
        while retries_left > 0:
            print(f"Retrying... {retries_left} retries left.")
            retries_left -= 1
            self._play_next_song()
            if self.is_playing:
                return  # Successfully restarted
            time.sleep(5)  # Add delay between retries
        print("Failed to reconnect after multiple attempts.")

    def stop_music(self):
        """Stops the currently playing music and clears the queue."""
        if self.current_process:
            self.should_stop = True  # Request the stop of the current song
            self.current_process.terminate()  # Terminate the ffmpeg process
            self.current_process = None
            print("Stopped streaming to Zeno FM.")
        else:
            print("No music is currently playing.")

        self.is_playing = False
        with self.song_queue.mutex:
            self.song_queue.queue.clear()  # Clear the queue
