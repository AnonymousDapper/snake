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

import re
from datetime import datetime
from random import choice
from urllib.parse import quote, quote_plus

import aiohttp
import discord
from bs4 import BeautifulSoup as b_soup
from discord.ext import commands
from PIL import ImageColor

from .utils import checks, time
from .utils.logger import get_logger

HEX_MATCH = re.compile(r"^#?([a-f0-9]{1,6})$", re.I)

MATERIAL_COLORS = [
    "B71C1C", # Red
    "880E4F", # Pink
    "4A148C", # Purple
    "311B92", # Deep Purple
    "1A237E", # Indigo
    "0D47A1", # Blue
    "01579B", # Light Blue
    "006064", # Cyan
    "004D40", # Teal
    "1B5E20", # Green
    "33691E", # Light Green
    "827717", # Lime
    "F57F17", # Yellow
    "FF6F00", # Amber
    "E65100", # Orange
    "BF360C", # Deep Orange
    "3E2723", # Brown
    "212121", # Grey
    "263238", # Blue Grey
]

log = get_logger()

class Images(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def parse_color(self, color_name):
        hex_match = HEX_MATCH.match(color_name)

        if hex_match:
            colorname = hex_match.group(1)
            colorname = f"{colorname}{'0' * (6 - len(colorname))}"

            color = tuple([int(colorname[i:i + 2], 16) for i in range(0, len(colorname), 2)])

        else:
            try:
                color = ImageColor.getrgb(color_name)

            except ValueError:
                return None

        return color

    @commands.command(name="retro", brief="retro text template")
    async def make_retro(self, ctx, *, content:str):
        texts = [t.strip() for t in content.split("|")]

        if len(texts) != 3:
            await ctx.send("\N{CROSS MARK} Couldn't parse 3 lines. Make sure your input follows the format `A|B|C`")
            return

        async with ctx.typing():
            data = dict(
                bg=choice((1, 2, 3, 4)),
                txt=choice((1, 2, 3, 4)),
                text1=texts[0],
                text2=texts[1],
                text3=texts[2]
            )

            async with self.bot.aio_session.post("https://photofunia.com/effects/retro-wave", data=data) as response:
                if response.status != 200:
                    await ctx.send("\N{CROSS MARK} Could not connect to server. Please try again later")
                    return

                soup = b_soup(await response.text(), "lxml")
                download_url = soup.find("div", class_="downloads-container").ul.li.a["href"]

                result_embed = discord.Embed()
                result_embed.set_image(url=download_url)

                await ctx.send(embed=result_embed)

    @commands.command(name="xkcd", brief="xkcd comics")
    async def get_xkcd(self, ctx, comic_id : int = None):
        comic_url = None

        if comic_id is None:
            async with self.bot.aio_session.get("https://c.xkcd.com/random/comic", allow_redirects=False) as header_response:
                comic_url = header_response.headers["Location"]

        else:
            comic_url = f"https://xkcd.com/{comic_id}/"

        if comic_url is None:
            await ctx.send("\N{CROSS MARK} URL could not be parsed. This should not happen and has been reported.")
            log.error(f"XKCD comic url: {comic_url} ({type(comic_url)}")
            return

        async with ctx.typing():
            async with self.bot.aio_session.get(f"{comic_url}info.0.json") as response:
                if response.status != 200:
                    if response.status == 404:
                        await ctx.send("\N{CROSS MARK} That comic could not be found")

                    else:
                        await ctx.send("\N{CROSS MARK} Could not connect to server. Please try again later.")

                    return

                data = await response.json()

                result_embed = discord.Embed(title=f"{data['title']} - {data['num']}", url=comic_url, description=data["alt"])
                result_embed.set_footer(icon_url="https://xkcd.com/s/919f27.ico", text="Served by XKCD")
                result_embed.set_image(url=data["img"])

                await ctx.send(embed=result_embed)

    @commands.command(name="emoji", brief="translate english to emoji")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def get_emoji(self, ctx, *, text:str):
        async with self.bot.aio_session.get("https://api.getdango.com/api/emoji", params=dict(q=quote_plus(text))) as response:
            if response.status != 200:
                await ctx.send("\N{CROSS MARK} Could not connect to server. Please try again later.")
                return

            emojis = await response.json()
            await ctx.send(" ".join(e["text"] for e in emojis["results"]))

    @commands.command(name="showcolor", brief="preview color swatches", aliases=["show", "color"])
    async def get_color(self, ctx, *, color_name:str):
        color = self.parse_color(color_name)

        if color is None:
            await ctx.send(f"\N{CROSS MARK} Can't parse `{color_name}` as a color")
            return

        new_color_name = f"{color[0]:0>2X}{color[1]:0>2X}{color[2]:0>2X}"

        image_url = f"https://via.placeholder.com/256/{new_color_name}/{new_color_name}"

        embed = discord.Embed(title=f"`{color_name}` : **#{new_color_name}**", url=image_url, color=int(new_color_name, 16))
        embed.set_image(url=image_url)

        await ctx.send(embed=embed)

    @commands.group(name="structure", brief="skeletal structure", invoke_without_command=True)
    async def skeletal_structure(self, ctx, *, chem_name:str):
        async with ctx.typing():
            safe_name = quote(chem_name)
            safe_title = quote(chem_name.title())

            async with self.bot.aio_session.get(f"https://avogadr.io/api/name/exists/{safe_name}") as response:

                if await response.text() == "true":
                    color = choice(MATERIAL_COLORS)

                    embed = discord.Embed(title=chem_name, url=f"https://avogadr.io/?background={color}&foreground=c5c5c5&compound={safe_name}&label={safe_title}", color=int(color, 16))
                    embed.set_image(url=f"https://avogadr.io/api/name/1080/1080/{color}/c5c5c5/{safe_name}?label={safe_title}")

                    await ctx.send(embed=embed)

                else:
                    await ctx.send(f"\N{CROSS MARK} '{chem_name}' could not be found")

    @skeletal_structure.command(name="smiles", brief="SMILES structure format")
    async def smiles_structure(self, ctx, *, smiles_format:str):
        with ctx.typing():
            smiles = quote(smiles_format)
            color = choice(MATERIAL_COLORS)
            embed = discord.Embed(title=f"`{smiles_format}`", url=f"https://avogadr.io/?background={color}&foreground=c5c5c5&smiles={smiles}", color=int(color, 16))
            embed.set_image(url=f"https://avogadr.io/api/smiles/1080/1080/{color}/c5c5c5/{smiles}")

            await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Images(bot))
