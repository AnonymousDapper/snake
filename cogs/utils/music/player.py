""" Song player API """

import asyncio
import shlex
import subprocess
import os

import traceback # TODO: remove later

from discord.player import AudioSource

class FFmpegStreamSource(AudioSource):
    def __init__(self, track):
        self.frame_size = (48 * 20) * 4 # int(SAMPLE_RATE / 1000 * FRAME_LENGTH) * SAMPLE_SIZE

        ffmpeg_args = shlex.split(f"ffmpeg -i {track.download_url} -f s16le -ar 48000 -ac 2 -loglevel warning -vn -b:a 128k pipe:")

        try:
            self.ffmpeg_process = subprocess.Popen(ffmpeg_args, stdin=None, stdout=subprocess.PIPE, stderr=None)
        except:
            traceback.print_exc()

    def read(self):
        ret = self.ffmpeg_process.stdout.read(self.frame_size)
        if len(ret) != self.frame_size:
            return b""

        return ret

    def cleanup(self):
        if self.ffmpeg_process is not None:
            self.ffmpeg_process.kill()

        self.ffmpeg_process = None
