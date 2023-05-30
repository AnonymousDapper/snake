# MIT License
#
# Copyright (c) 2016-2023 AnonymousDapper
#


from __future__ import annotations

import inspect
import unicodedata
from os import path
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands

from .utils.logger import get_logger

if TYPE_CHECKING:
    from ..snake import SnakeBot

log = get_logger()


class Misc(commands.Cog):
    def __init__(self, bot: SnakeBot):
        self.bot = bot

    @commands.command(name="charinfo", brief="unicode info")
    async def get_char(self, ctx: commands.Context, *, string: str):
        if len(string) < 100:
            result_embed = discord.Embed(color=0x1DE9B6)
            for char in string:
                unicode_name = unicodedata.name(char)
                unicode_value = hex(ord(char))
                result_embed.add_field(
                    name=unicode_name,
                    value=f"[`{unicode_value}`](http://www.fileformat.info/info/unicode/char/{unicode_value[2:]}) -> {char}",
                    inline=True,
                )
            await ctx.send(embed=result_embed)

    # modified from R. Danny source code (copyright Rapptz https://github.com/Rapptz/RoboDanny)
    # under the Mozilla Public License 2.0 (https://choosealicense.com/licenses/mpl-2.0/)
    @commands.command(name="source", brief="view command source")
    async def get_source(self, ctx: commands.Context, *, command: Optional[str] = None):
        source_url = "https://gitlab.a-sketchy.site/AnonymousDapper/snake"
        branch = "master"

        if command is None:
            return await ctx.send(source_url)

        if command == "help":
            src = type(self.bot.help_command)
            module = src.__module__
            filename = inspect.getsourcefile(src)
        else:
            if not (obj := self.bot.get_command(command.replace(".", " "))):
                return await self.bot.post_reaction(ctx.message, unknown=True)

            src = obj.callback
            module = obj.callback.__module__
            filename = src.__code__.co_filename

        lines, firstline = inspect.getsourcelines(src)
        if not module.startswith("discord"):
            if filename is None:
                return await self.bot.post_reaction(ctx.message, unknown=True)

            location = path.relpath(filename).replace("\\", "/")
        else:
            location = module.replace(".", "/") + ".py"
            source_url = "https://github.com/Rapptz/discord.py"
            # maybe change branch later

        await ctx.send(
            f"<{source_url}/blob/{branch}/{location}#L{firstline}-L{firstline + len(lines) - 1}>"
        )


async def setup(bot):
    await bot.add_cog(Misc(bot))
