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

__all__ = ["ImgurApiError", "PostRequestLimitError", "DailyApiCreditLimitError", "HourlyApiCreditLimitError", "ImgurAPI"]

import asyncio

from datetime import datetime

import aiohttp

from .logger import get_logger

logger = get_logger()

API_BASE = "https://api.imgur.com/3"

class ImgurApiError(Exception):
    pass

class PostRequestLimitError(ImgurApiError):
    pass

class DailyApiCreditLimitError(ImgurApiError):
    pass

class HourlyApiCreditLimitError(ImgurApiError):
    pass


class ImgurAPI:
    def __init__(self, **kwargs):
        self.client_id = kwargs.get("client_id", "")

        self.auth_headers = {
            "Authorization": f"Client-ID {self.client_id}",
        }

        self.client_session = None

        self.loop = asyncio.get_event_loop()

        self.total_credits = 0
        self.remain_credits = 0

        self.hourly_credits = 0
        self.hourly_credits_remain = 0
        self.hourly_credit_reset = datetime.now()

        self.post_limit = 0
        self.post_remain = 0
        self.post_reset = 0

        self.loop.create_task(self.client_init())

    # Start up client session in a coroutine
    async def client_init(self):
        self.client_session = aiohttp.ClientSession()
        await asyncio.sleep(0.25)

        await self._check_credits()

    # Fetch ratelimit info from headers
    def _save_credits(self, response):
        headers = response["headers"]

        self.total_credits = int(headers.get("X-RateLimit-ClientLimit"))
        self.remain_credits = int(headers.get("X-RateLimit-ClientRemaining"))

        self.hourly_credits = int(headers.get("X-RateLimit-UserLimit"))
        self.hourly_credits_remain = int(headers.get("X-RateLimit-UserRemaining"))
        self.hourly_credit_reset = datetime.fromtimestamp(int(headers.get("X-RateLimit-UserReset")))

        self.post_limit = int(headers.get("X-Post-Rate-Limit-Limit"))
        self.post_remain = int(headers.get("X-Post-Rate-Limit-Remaining"))
        self.post_reset = int(headers.get("X-Post-Rate-Limit-Reset"))

    # Base API calling function (POST)
    async def _post(self, endpoint, data, **kwargs):
        async with self.client_session.post(f"{API_BASE}/{endpoint}", headers=self.auth_headers, data=data) as response:

            result = dict(
                status=response.status,
                headers=response.headers,
                data=await getattr(response, kwargs.get("type", "text"))()
            )

            return result

    # Base API calling function (GET)
    async def _get(self, endpoint, **kwargs):
        async with self.client_session.get(f"{API_BASE}/{endpoint}", headers=self.auth_headers) as response:

            result = dict(
                status=response.status,
                headers=response.headers,
                data=await getattr(response, kwargs.get("type", "text"))()
            )

            return result

    # Check API credit tally
    async def _check_credits(self):
        response = await self._get("credits", type="json")
        data = response["data"]["data"]

        self.total_credits = data.get("ClientLimit")
        self.remain_credits = data.get("ClientRemaining")

        self.hourly_credits = data.get("UserLimit")
        self.hourly_credits_remain = data.get("UserRemaining")
        self.hourly_credit_reset = datetime.fromtimestamp(data.get("UserReset"))

        self.post_limit = data.get("ClientLimit")
        self.post_remain = data.get("ClientRemaining")
        self.post_reset = 0


    # Actual API functions

    # Upload an image (image: BytesIO)
    async def upload_image(self, image):
        if self.post_remain == 0:
            raise PostRequestLimitError(f"POST request quota reached (used {self.post_limit} requests, will reset in {int(self.post_limit / 60)} mins)")

        elif self.remain_credits < 10:
            raise DailyApiCreditLimitError(f"Not enough daily API credits remain for this (have {self.remain_credits}, need 10, will reset tomorrow)")

        elif self.hourly_credits_remain < 10:
            raise HourlyApiCreditLimitError(f"Not enough hourly API credits remain for this (have {self.hourly_credits_remain}, need 10, will reset in {int(abs(datetime.now() - self.hourly_credit_reset).seconds / 60)} mins)")

        image.seek(0)
        response = await self._post("image", image, type="json")

        self._save_credits(response)

        if response["status"] == 200:
            return response["data"]["data"]["link"]

        else:
            raise ImgurApiError(f"Unknown Error: {response.status}")
