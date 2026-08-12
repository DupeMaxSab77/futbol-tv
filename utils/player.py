import subprocess
import signal
import os
import sys


class MPVPlayer:
    """Wrapper around mpv for m3u8 playback."""

    def __init__(self):
        self.process = None

    def play(self, url: str, title: str = ""):
        """Play an m3u8 stream using mpv."""
        self.stop()

        cmd = [
            "mpv",
            "--no-cache",
            "--no-terminal",
            f"--title={title}",
            "--ontop",
            "--fullscreen",
            url,
        ]

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid,
            )
        except FileNotFoundError:
            print("[player] mpv not found. Install with: sudo apt install mpv")
            raise
        except Exception as e:
            print(f"[player] Error starting mpv: {e}")
            raise

    def stop(self):
        """Stop the current playback."""
        if self.process and self.process.poll() is None:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except Exception:
                pass
        self.process = None

    def is_playing(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def __del__(self):
        self.stop()
