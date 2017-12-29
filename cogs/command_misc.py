import discord
import aiohttp
import re
import traceback

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

    @commands.group(name="role", brief="manage roles", no_pm=True, invoke_without_command=False)
    async def role_group(self, ctx):
        print("Role")

    @role_group.command(name="get", brief="assign yourself a role", no_pm=True)
    async def get_role(self, ctx, *, role_name:str):
        if ctx.guild.id == 224187988593213442:
            role = discord.utils.get(ctx.guild.roles, name=role_name)

            if role is not None:
                try:
                    await ctx.author.add_roles(role, reason="bot command", atomic=True)
                    await self.bot.post_reaction(ctx.message, success=True)

                except Exception as e:
                    traceback.print_exc()
                    await self.bot.post_reaction(ctx.message, failure=True)

    @role_group.command(name="remove", brief="remove an assigned role from yourself", no_pm=True)
    async def remove_role(self, ctx, *, role_name:str):
        if ctx.guild.id == 224187988593213442:
            role = discord.utils.get(ctx.guild.roles, name=role_name)

            if role is not None:
                try:
                    await ctx.author.remove_roles([role.id], reason="bot command", atomic=True)
                    await self.bot.post_reaction(ctx.message, success=True)

                except Exception as e:
                    traceback.print_exc()
                    await self.bot.post_reaction(ctx.message, failure=True)

            else:
                await ctx.send(f"Role '{role_name}' could not be found")

    @role_group.command(name="post", brief="post an update for a role", no_pm=True)
    @checks.is_owner()
    async def role_post(self, ctx, role_name, *, text):
        if ctx.guild.id == 224187988593213442:
            role = discord.utils.get(ctx.guild.roles, name=role_name)

            if role is not None:
                try:
                    await role.edit(mentionable=True)
                    await ctx.send(f"{role.mention} {text}")
                    await role.edit(mentionable=False)
                    await ctx.message.delete()

                except Exception as e:
                    traceback.print_exc()
                    await self.bot.post_reaction(ctx.message, failure=True)

            else:
                await ctx.send(f"Role '{role_name}' could not be found")

def setup(bot):
    bot.add_cog(Misc(bot))