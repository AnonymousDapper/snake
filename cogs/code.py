# MIT License
#
# Copyright (c) 2016-2023 AnonymousDapper
#

from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

from .utils.logger import get_logger

if TYPE_CHECKING:
    from ..snake import SnakeBot

log = get_logger()


class Code(commands.Cog):
    def __init__(self, bot: SnakeBot):
        self.bot = bot


async def setup(bot):
    await bot.add_cog(Code(bot))
