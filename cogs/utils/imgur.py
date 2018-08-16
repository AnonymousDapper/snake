# MIT License
#
# Copyright (c) 2018 AnonymousDapper
#
# Permission is hereby granted
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

__all__ = ["ImgurApiError", "PostRequestLimitError", "ApiCreditLimitError", "ImgurAPI"]

import asyncio

import aiohttp

from .logger import get_logger

logger = get_logger()

API_BASE = "https://api.imgur.com/3"

class ImgurApiError(Exception):
    pass

class PostRequestLimitError(ImgurApiError):
    pass

class ApiCreditLimitError(ImgurApiError):
    pass


class ImgurAPI:
    def __init__(self, **kwargs):
        self.client_id = kwargs.get("client_id", "")

        self.auth_headers = {
            "Authorization": f"Client-ID {self.client_id}"
        }

        self.loop = asyncio.get_event_loop()

        self.total_credits = 0
        self.remain_credits = 0

        self.post_limit = 0
        self.post_remain = 0

        self.loop.create_task(self.client_init())
        self.loop.create_task(self._check_credits())

    # Start up client session in a coroutine
    async def client_init(self):
        self.client_session = aiohttp.ClientSession()

    # Fetch ratelimit info from headers
    def _save_credits(self, response):
        self.total_credits = response.headers.get("X-RateLimit-ClientLimit")
        self.remain_credits = response.headers.get("X-RateLimit-ClientRemaining")

        self.post_limit = response.headers.get("X-Post-Rate-Limit-Limit")
        self.post_remain = response.headers.get("X-Post-Rate-Limit-Remaining")

    # Base API calling function (POST)
    async def _post(self, endpoint, data):
        async with self.client_session.post(f"{API_BASE}/{endpoint}", headers=self.auth_headers, data=data) as response:
            return response

    # Base API calling function (GET)
    async def _get(self, endpoint):
        async with self.client_session.get(f"{API_BASE}/{endpoint}", headers=self.auth_headers) as response:
            return response

    # Check API credit tally
    async def _check_credits(self):
        credit_response = await self._get("credits")

        self._save_credits(credit_response)

    # Actual API functions

    # Upload an image (image: BytesIO)
    async def upload_image(self, image):
        if self.post_remain == 0:
            raise PostRequestLimitError(f"POST request quota reached (used {self.post_limit} requests)")

        elif self.remain_credits < 10:
            raise ApiCreditLimitError(f"Not enough API credits remain for this (have {self.remain_credits}, need 10)")

        image.seek(0)
        response = await self._post("image", image)

        self._save_credits(response)

        if response.status == 200:
            data = await response.json()
            return data["data"]["link"]

        else:
            raise ImgurApiError(f"Unknown Error: {response.status}")
