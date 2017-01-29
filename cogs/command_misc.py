import discord, aiohttp, re

from bs4 import BeautifulSoup as b_soup
from datetime import datetime
from random import choice
from io import BytesIO
from urllib.parse import quote_plus

from discord.ext import commands
from .utils import checks, time

class Misc:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="retro", pass_context=True, brief="make retro banners")
    @checks.permissions(use_retro=True)
    async def make_retro(self, ctx, *, content:str):
        texts = [t.strip() for t in content.split("|")]
        if len(texts) != 3:
            await self.bot.say("\N{CROSS MARK} Sorry! That input couldn't be parsed. Do you have 2 seperators? ( `|` )")
            return

        await self.bot.type()
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
                await self.bot.say("\N{CROSS MARK} Could not connect to server. Please try again later")
                return

            soup = b_soup(await response.text(), "lxml")
            download_url = soup.find("div", class_="downloads-container").ul.li.a["href"]

            result_embed = discord.Embed()
            result_embed.set_image(url=download_url)

            await self.bot.say(embed=result_embed)

    @commands.command(name="xkcd", pass_context=True, brief="fetch xkcd comics")
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
                await self.bot.say("\N{CROSS MARK} Couldn't connect to server.")
                return

            data = await response.json()

            result_embed = discord.Embed(title=f"{data['title']} - {data['num']}", url=comic_url, description=data["alt"])
            result_embed.set_footer(icon_url="https://xkcd.com/favicon.ico", text="Served by XKCD")
            result_embed.set_image(url=data["img"])

            await self.bot.say(embed=result_embed)

    @commands.command(name="uptime", pass_context=True, brief="show bot uptime")
    async def show_uptime(self, ctx):
        await self.bot.say(f"Snake has been running for **{time.get_elapsed_time(self.bot.start_time, datetime.now())}** ({self.bot.start_time:{time.time_format}})")

    @commands.command(name="suggest", pass_context=True, brief="give feedback", no_pm=True)
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def give_feedback(self, ctx, *, message:str):
        author = ctx.message.author
        channel = ctx.message.channel

        if not await self.bot.check_blacklist("suggest", user_id=int(author.id)):
            try:
                result = any(await self.bot.shared.post_suggestion(f"Suggestion from **{author.display_name}**#{author.discriminator} [{author.id}]\n**{channel.server.name}** #**{channel.name}**\n\n{message}"))
            except Exception as e:
                await self.bot.reply(f"Your message could not be delivered. Please report this information to the owners:\n`[{type(e).__name__}]: {e}`")
                return

            await self.bot.say("\N{WHITE HEAVY CHECK MARK} Your message was delivered successfully!")

        else:
            return

    @commands.command(name="emoji", pass_context=True, brief="find emoji")
    @commands.cooldown(1, 15, commands.BucketType.user)
    @checks.permissions(use_emoji=True)
    async def get_emoji(self, ctx, *, query:str):
        async with self.bot.aio_session.get("https://api.getdango.com/api/emoji", params=dict(q=quote_plus(query))) as response:
            if response.status != 200:
                await self.bot.say("Could not connect to server")
                return

            emojis = await response.json()
            await self.bot.say(" ".join(e["text"] for e in emojis["results"]))

    @commands.command(name="invite", pass_context=True, brief="find an invite link")
    async def get_invite(self, ctx):
        permissions = discord.Permissions(permissions=70634561)
        await self.bot.say(f"Invite me with this link!\n{discord.utils.oauth_url('181584771510566922', permissions=permissions)}")

def setup(bot):
    bot.add_cog(Misc(bot))