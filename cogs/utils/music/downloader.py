""" Discord snake music downloader """
import asyncio, youtube_dl, os, json

from functools import partial
from concurrent.futures import ThreadPoolExecutor

ytdl_options = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    #"ignoreerrors": False,
    #"logtostderr": False,
    #"quiet": False,
    #"no_warnings": False,
    "default_search": "auto",
    "source_address": "0.0.0.0",
}

#youtube_dl.utils.bug_reports_message = lambda: ""

class Downloader:
    def __init__(self, download_folder="youtube_cache"):
        self.thread_pool = ThreadPoolExecutor(max_workers=2)
        self.unsafe_ytdl = youtube_dl.YoutubeDL(ytdl_options)
        self.safe_ytdl = youtube_dl.YoutubeDL(ytdl_options)
        self.safe_ytdl.params["ignoreerrors"] = True
        self.download_folder = os.path.join(os.getcwd(), download_folder)
        self.loop = asyncio.get_event_loop()

        otmpl = self.unsafe_ytdl.params["outtmpl"]
        self.unsafe_ytdl.params["outtmpl"] = os.path.join(self.download_folder, otmpl)
        otmpl = self.safe_ytdl.params["outtmpl"]
        self.safe_ytdl.params["outtmpl"] = os.path.join(self.download_folder, otmpl)

    @property
    def ytdl(self):
        return self.safe_ytdl

    async def extract_info(self, *args, on_error=None, retry_on_error=False, **kwargs):
        if callable(on_error):
            try:
                return await self.loop.run_in_executor(self.thread_pool, partial(self.unsafe_ytdl.extract_info, *args, **kwargs))
            except Exception as e:
                if asyncio.iscoroutinefunction(on_error):
                    asyncio.ensure_future(on_error(e), loop=self.loop)
                elif asyncio.iscourutine(on_error):
                    asyncio.ensure_future(on_error, loop=loop)
                else:
                    loop.call_soon_threadsafe(on_error, e)

                if retry_on_error:
                    return await self.safe_extract_info(loop, *args, **kwargs)

        else:
            return await self.loop.run_in_executor(self.thread_pool, partial(self.unsafe_ytdl.extract_info, *args, **kwargs))

    async def safe_extract_info(self, *args, **kwargs):
        return await self.loop.run_in_executor(self.thread_pool, partial(self.safe_ytdl.extract_info, *args, **kwargs))

    async def download(self, url):
        if not os.path.exists(self.download_folder):
            os.makedirs(self.download_folder)

        print(f"Starting download of {url}")
        video_info = await self.extract_info(url, download=False)

        with open("info.json", 'w') as f:
            f.write(json.dumps(video_info, sort_keys=True, indent=2))

        if "_type" in video_info:
            filename = self.unsafe_ytdl.params["outtmpl"] % video_info.get("entries")[0]
        else:
            filename = self.unsafe_ytdl.params["outtmpl"] % video_info

        if os.path.basename(filename) in os.listdir(self.download_folder):
            print(f"{url} is cached")
            return filename
        else:
            return await self._real_download(url)

    async def _real_download(self, url):
        video_info = await self.extract_info(url, download=False)

        if "_type" in video_info:
            filename = self.unsafe_ytdl.params["outtmpl"] % video_info.get("entries")[0]
        else:
            filename = self.unsafe_ytdl.params["outtmpl"] % video_info

        result = await self.extract_info(url, download=True, extra_info=video_info)
        if result is not None:
            return filename
