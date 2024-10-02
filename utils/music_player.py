import yt_dlp as youtube_dl
import subprocess

class MusicPlayer:
    def __init__(self):
        self.current_process = None
        self.server_address = "link.zeno.fm"  # Icecast server address
        self.port = "80"  # Icecast server port
        self.mount_point = "irk5uxfloc1tv"  # Updated mount point from your provided URL
        self.username = "source"
        self.password = "zUYZ49Vg"
        self.encoding = "mp3"  # Use 'mp3' or 'aac' based on your requirement

    def play_music(self, url):
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
                print(f"Streaming music from {audio_url} to Zeno FM...")

                # Construct the Icecast streaming URL correctly
                icecast_url = f"icecast://{self.username}:{self.password}@{self.server_address}:{self.port}/{self.mount_point}"

                # If there's an existing streaming process, stop it
                if self.current_process:
                    self.stop_music()

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

                # Monitor the output for troubleshooting
                while True:
                    output = self.current_process.stderr.readline()
                    if output == '' and self.current_process.poll() is not None:
                        break
                    if output:
                        print(output.strip())

        except Exception as e:
            print(f"An error occurred while trying to stream to Zeno FM: {e}")

    def stop_music(self):
        if self.current_process:
            self.current_process.terminate()
            self.current_process = None
            print("Stopped streaming to Zeno FM.")
