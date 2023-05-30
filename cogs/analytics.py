# MIT License
#
# Copyright (c) 2016-2023 AnonymousDapper
#


from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from .utils.colors import Colorize as C
from .utils.logger import get_logger

if TYPE_CHECKING:
    from ..snake import SnakeBot

log = get_logger()


class Analytics(commands.Cog):
    def __init__(self, bot: SnakeBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        if ctx.guild:
            destination = f"[{ctx.guild.name} #{ctx.channel.name}]"
        else:
            destination = "DM"

        if ctx.invoked_subcommand:
            command = ctx.invoked_subcommand.qualified_name

        elif ctx.command:
            command = ctx.command.qualified_name

        else:
            command = ctx.invoked_with or "unknown command"

        log.info(
            f"{destination}: {ctx.author.name}: {command} {' '.join(map(str, ctx.args[2:]))} {' '.join(f'{k!s}={v!r}' for k,v in ctx.kwargs.items())}"
        )

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send(
                "\N{NO ENTRY} You cannot use that command in a private channel"
            )

        elif isinstance(error, commands.CommandNotFound):
            # later
            ...

        elif isinstance(error, commands.CheckFailure):
            log.debug(
                f"Check failed for '{ctx.invoked_with}' (Author: {ctx.author.name})"
            )

        elif isinstance(error, commands.DisabledCommand):
            await self.bot.post_reaction(ctx.message)

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"{ctx.author.mention} slow down! Try that again in {error.retry_after:.1f} seconds"
            )

        elif isinstance(
            error, (commands.MissingRequiredArgument, commands.BadArgument)
        ):
            await ctx.send(f"\N{WARNING SIGN}\N{VARIATION SELECTOR-16} {error}")

        elif isinstance(error, discord.Forbidden):
            log.warn(f"{ctx.command.qualified_name} failed: Forbidden.")

        elif isinstance(error, commands.CommandInvokeError):
            if isinstance(error.original, discord.Forbidden):
                log.warn(f"{ctx.command.qualified_name} failed: Forbidden.")

            original_name = error.original.__class__.__name__
            print(f"In {C(ctx.command.qualified_name).red().bold()}:")
            traceback.print_tb(error.original.__traceback__)
            print(f"{C(original_name).red().bold()}: {error.original}")

        else:
            print(f"{C(type(error).__name__).red().bold()}: {error}")


async def setup(bot):
    await bot.add_cog(Analytics(bot))
