import discord
import aiohttp
import re
import unicodedata
import traceback

from bs4 import BeautifulSoup as b_soup
from datetime import datetime
from random import choice
from io import BytesIO
from PIL import Image, ImageColor
from urllib.parse import quote_plus, quote

from discord.ext import commands
from .utils import checks, time

from cogs.utils.tag_manager import math_handler

HEX_MATCH = re.compile(r"^#?([a-f0-9]{1,8})$", re.I)

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

class Misc:
    def __init__(self, bot):
        self.bot = bot

    def parse_color(self, color_name):
        hex_match = HEX_MATCH.match(color_name)
        if hex_match:
            colorname = hex_match.group(1)
            colorname = f"{colorname}{'0' * (6 - len(colorname))}"
            color = tuple([int(colorname[i:i+2], 16) for i in range(0, len(colorname), 2)])
        else:
            try:
                color = ImageColor.getrgb(color_name)
            except ValueError:
                return None

        if len(color) < 4:
            color += (255,)

        return color

    @commands.command(name="retro", brief="make retro banners")
    @checks.permissions(use_retro=True)
    async def make_retro(self, ctx, *, content:str):
        texts = [t.strip() for t in content.split("|")]
        if len(texts) != 3:
            await ctx.send("\N{CROSS MARK} Sorry! That input couldn't be parsed. Do you have 2 seperators? ( `|` )")
            return

        async with ctx.channel.typing():
            _tmp_choice = choice([1, 2, 3, 4])

            data = dict(
                bg=_tmp_choice,
                txt=_tmp_choice,
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

    @commands.command(name="xkcd", brief="fetch xkcd comics")
    @checks.permissions(use_xkcd=True)
    async def get_xkcd(self, ctx, id : str = None):
        comic_url = ""

        if id is None:
            async with self.bot.aio_session.get("https://c.xkcd.com/random/comic", allow_redirects=False) as header_response:
                comic_url = header_response.headers["Location"]
        else:
            comic_url = f"https://xkcd.com/{id}/"
        comic_data_url = f"{comic_url}info.0.json"

        async with self.bot.aio_session.get(comic_data_url) as response:
            if response.status != 200:
                await ctx.send("\N{CROSS MARK} Couldn't connect to server.")
                return

            data = await response.json()

            result_embed = discord.Embed(title=f"{data['title']} - {data['num']}", url=comic_url, description=data["alt"])
            result_embed.set_footer(icon_url="https://xkcd.com/favicon.ico", text="Served by XKCD")
            result_embed.set_image(url=data["img"])

            await ctx.send(embed=result_embed)

    @commands.command(name="uptime", brief="show bot uptime")
    async def show_uptime(self, ctx):
        await ctx.send(f"Snake has been running for **{time.get_elapsed_time(self.bot.start_time, datetime.now())}** ({self.bot.start_time:{time.time_format}})")

    @commands.command(name="emoji", brief="find emoji")
    @commands.cooldown(1, 15, commands.BucketType.user)
    @checks.permissions(use_emoji=True)
    async def get_emoji(self, ctx, *, query:str):
        async with self.bot.aio_session.get("https://api.getdango.com/api/emoji", params=dict(q=quote_plus(query))) as response:
            if response.status != 200:
                await ctx.send("Could not connect to server")
                return

            emojis = await response.json()
            await ctx.send(" ".join(e["text"] for e in emojis["results"]))

    @commands.command(name="calc", brief="do math")
    async def run_calc(self, ctx, *, expr:str):
        parser = math_handler.MathParser(expr, debug=self.bot._DEBUG)
        try:
            result = parser()
        except Exception as e:
            result = f"[{e.__class__.__name__}]: {e}"

        await ctx.send(result)

    @commands.command(name="showcolor", brief="preview a color", aliases=["show", "color"])
    async def get_color(self, ctx, *, color_name:str):
        color = self.parse_color(color_name)
        if color is None:
            await ctx.send(f"\N{CROSS MARK} Can't parse `{color_name}` as a color")
            return

        temp = BytesIO()
        image = Image.new("RGBA", (256, 256), color)
        image.save(temp, format="PNG")
        image_url = await self.bot.upload_to_imgur(temp)
        new_color_name = f"#{color[0]:0>2X}{color[1]:0>2X}{color[2]:0>2X}{color[3]:0>2X}"
        embed = discord.Embed(title=f"`{color_name}` : **{new_color_name}**", url=image_url, color=int(new_color_name[1:-2], 16))
        embed.set_image(url=image_url)

        await ctx.send(embed=embed)
        temp.close()

    @commands.command(name="charinfo", brief="unicode info")
    async def get_char(self, ctx, *, string:str):
        if len(string) < 100:
            result_embed = discord.Embed(color=0x1DE9B6)
            for char in string:
                unicode_name = unicodedata.name(char)
                unicode_value = hex(ord(char))
                result_embed.add_field(name=unicode_name, value=f"[`{unicode_value}`](http://www.fileformat.info/info/unicode/char/{unicode_value[2:]}) -> {char}", inline=True)
            await ctx.send(embed=result_embed)

    @commands.group(name="structure", brief="skeletal structure", invoke_without_command=True)
    async def skeletal_structure(self, ctx, *, chem_name:str):
        with ctx.typing():
            safe_name = quote(chem_name)

            async with self.bot.aio_session.get(f"https://avogadr.io/api/name/exists/{chem_name}") as response:

                if await response.text() == "true":
                    color = choice(MATERIAL_COLORS)

                    embed = discord.Embed(title=chem_name, url=f"https://avogadr.io/?background={color}&foreground=c5c5c5&compound={safe_name}&label={safe_name}", color=int(color, 16))
                    embed.set_image(url=f"https://avogadr.io/api/name/1080/1080/{color}/c5c5c5/{safe_name}?label={quote(chem_name.title())}")
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

    @commands.command(name="clean", brief="remove snake's messages")
    @commands.cooldown(2, 60, commands.BucketType.guild)
    async def self_clean(self, ctx):
        async for message in ctx.history(limit=30, before=ctx.message):
            if message.author == ctx.guild.me:
                await message.delete()

def setup(bot):
    bot.add_cog(Misc(bot))