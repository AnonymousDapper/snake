# MIT License
#
# Copyright (c) 2016-2023 AnonymousDapper
#


from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING

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


async def setup(bot):
    await bot.add_cog(Misc(bot))
