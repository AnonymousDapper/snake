# MIT License
#
# Copyright (c) 2016-2023 AnonymousDapper
#


from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Literal, Optional, Union

import aiohttp
import arrow
import discord
import mystbin
import tomli
from discord.ext import commands

from cogs.utils import logger
from cogs.utils.colors import Colorize as C
from cogs.utils.sql import SQL, Channel, Emote

clogger = logger.get_console_logger("snake")

# Attempt to load uvloop for improved event loop performance
try:
    import uvloop

except ModuleNotFoundError:
    clogger.warn("Can't find uvloop, defaulting to standard policy")

else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    clogger.info("Using uvloop policy")

_DEBUG = any(arg.lower() == "-d" for arg in sys.argv)


def _read_config(filename):
    with open(filename, "rb") as cfg:
        return tomli.load(cfg)


_CREDS = _read_config("credentials.toml")

logger.set_level(debug=_DEBUG)


class Builtin(commands.Cog):
    def __init__(self, bot: SnakeBot):
        self.bot = bot

    @commands.command(name="quit", brief="exit bot", aliases=["×"])
    @commands.is_owner()
    async def quit_command(self, ctx: commands.Context):
        await self.bot.myst_client.close()
        await self.bot.aio_session.close()
        await self.bot.db.close()
        await self.bot.close()

    @commands.group(
        name="cog", brief="manage cogs", invoke_without_command=True, aliases=["±"]
    )
    @commands.is_owner()
    async def manage_cogs(self, ctx: commands.Context, name: str, action: str):
        print("cogs")

    @manage_cogs.command(name="load", brief="load cog", aliases=["^"])
    @commands.is_owner()
    async def load_cog(self, ctx: commands.Context, name: str):
        cog_name = "cogs." + name.lower()

        if self.bot.extensions.get(cog_name) is not None:
            await self.bot.post_reaction(ctx.message, unknown=True)

        else:
            try:
                await self.bot.load_extension(cog_name)

            except Exception as e:
                await ctx.send(f"Failed to load {name}: [{type(e).__name__}]: `{e}`")

            else:
                await self.bot.post_reaction(ctx.message, success=True)

    @manage_cogs.command(name="unload", brief="unload cog", aliases=["-"])
    @commands.is_owner()
    async def unload_cog(self, ctx: commands.Context, name: str):
        cog_name = "cogs." + name.lower()

        if self.bot.extensions.get(cog_name) is None:
            await self.bot.post_reaction(ctx.message, unknown=True)

        else:
            try:
                await self.bot.unload_extension(cog_name)

            except Exception as e:
                await ctx.send(f"Failed to unload {name}: [{type(e).__name__}]: `{e}`")

            else:
                await self.bot.post_reaction(ctx.message, success=True)

    @manage_cogs.command(name="reload", brief="reload cog", aliases=["*"])
    @commands.is_owner()
    async def reload_cog(self, ctx: commands.Context, name: str):
        cog_name = "cogs." + name.lower()

        if self.bot.extensions.get(cog_name) is None:
            await self.bot.post_reaction(ctx.message, unknown=True)

        else:
            try:
                await self.bot.unload_extension(cog_name)
                await self.bot.load_extension(cog_name)

            except Exception as e:
                await ctx.send(f"Failed to reload {name}: [{type(e).__name__}]: `{e}`")

            else:
                await self.bot.post_reaction(ctx.message, success=True)

    @manage_cogs.command(name="list", brief="list loaded cogs", aliases=["~"])
    @commands.is_owner()
    async def list_cogs(self, ctx: commands.Context, name: Optional[str] = None):
        if name is None:
            await ctx.send(
                f"Currently loaded cogs:\n{' '.join('`' + cog_name + '`' for cog_name in self.bot.extensions)}"
                if len(self.bot.extensions) > 0
                else "No cogs loaded"
            )

        else:
            if self.bot.extensions.get("cogs." + name) is None:
                await self.bot.post_reaction(ctx.message, failure=True)

            else:
                await self.bot.post_reaction(ctx.message, success=True)

    @commands.command(name="sync", brief="sync slash commands", aliases=["§"])
    @commands.guild_only()
    @commands.is_owner()
    async def sync_tree(
        self,
        ctx: commands.Context,
        guilds: commands.Greedy[discord.Object],
        spec: Optional[Literal["~", "*", "^"]] = None,
    ):
        if not guilds:
            if spec == "~":
                synced = await self.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                self.bot.tree.copy_global_to(guild=ctx.guild)  # type: ignore
                synced = await self.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                self.bot.tree.clear_commands(guild=ctx.guild)
                await self.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await self.bot.tree.sync()

            await ctx.send(
                f"Synced {len(synced)} commands {'globally' if spec is None else 'to ' + ctx.guild.name}"
            )
            return

        ret = 0
        for guild in guilds:
            try:
                await self.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        await ctx.send(f"Synced global tree to {ret}/{len(guilds)}.")


class SnakeBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        self.debug = _DEBUG
        self.loop = asyncio.get_event_loop()

        self.log = clogger

        self.config = _read_config("config.toml")

        self.db = SQL(db_file=Path(self.config["SQLite"]["file_path"]))

        # Load credentials
        self.token = _CREDS["Discord"]["token"]

        self.start_time = None
        self.resume_time = None

        help_cmd = commands.DefaultHelpCommand(
            command_attrs=dict(hidden=True),
        )

        # Init superclass
        super().__init__(
            *args,
            **kwargs,
            help_command=help_cmd,
            description="\nHsss!\n",
            command_prefix=self.get_prefix,  # type: ignore
            intents=discord.Intents.all(),
        )

        self.boot_time = arrow.utcnow()

    async def setup_hook(self):
        await self.db._setup()

        self.aio_session = aiohttp.ClientSession()

        self.myst_client = mystbin.Client(session=self.aio_session)

        await self.add_cog(Builtin(self))

        for file in Path("cogs/").iterdir():
            if (
                file.is_file()
                and file.suffix == ".py"
                and not file.stem.startswith("_")
            ):
                stem = file.stem
                try:
                    await self.load_extension(f"cogs.{stem}")
                except Exception as e:
                    self.log.warn(
                        f"Failed to load cog {C(stem).bright_red()}: [{type(e).__name__}]: {e}",
                        exc_info=True,
                    )
                else:
                    self.log.info(f"Loaded cog {C(stem).green()}")

    # Post a reaction indicating command status
    async def post_reaction(
        self, message: discord.Message, emoji: Optional[Emote] = None, **kwargs
    ):
        reaction_emoji = ""

        if emoji is None:
            if kwargs.get("success"):
                reaction_emoji = "\N{WHITE HEAVY CHECK MARK}"

            elif kwargs.get("failure"):
                reaction_emoji = "\N{CROSS MARK}"

            elif kwargs.get("warning"):
                reaction_emoji = "\N{WARNING SIGN}\N{VARIATION SELECTOR-16}"

            elif kwargs.get("unknown"):
                reaction_emoji = "\N{BLACK QUESTION MARK ORNAMENT}"

            else:
                reaction_emoji = "\N{NO ENTRY}"

        else:
            reaction_emoji = emoji

        try:
            await message.add_reaction(reaction_emoji)

        except Exception:
            if not kwargs.get("quiet"):
                await message.channel.send(str(reaction_emoji))

    async def resolve_message(
        self, channel_id: int, message_id: int
    ) -> Optional[discord.Message]:
        try:
            channel = await self.fetch_channel(channel_id)
        except:
            return

        if not isinstance(channel, Channel):
            return

        try:
            message = await channel.fetch_message(message_id)
        except:
            return

        return message

    async def get_prefix(self, message: discord.Message):
        prefixes = [self.config["General"]["default_prefix"]] + self.config[
            "General"
        ].get("extra_prefixes", [])

        if await self.is_owner(message.author):
            prefixes += ["s ", "Σ "]

        return prefixes

    async def on_ready(self):
        self.start_time = arrow.utcnow()
        boot_duration = self.start_time.humanize(self.boot_time)

        self.log.info(
            f"Logged in as {C(self.user.name).yellow()}{C(' DEBUG MODE').bright_magenta() if self.debug else ''}\nLoaded {C(boot_duration).cyan()}"
        )

        emote = {"animated": False, "id": 357268510759714816, "name": "blobpeek"}

        act = discord.Activity(name="for `snake help`", state="state", details="details", type=discord.ActivityType.watching, emoji=emote)

        await self.change_presence(activity=act)


    async def on_resume(self):
        self.resume_time = arrow.utcnow()
        boot_duration = self.resume_time.humanize(
            self.start_time,
        )

        self.log.info(
            f"Resumed as {C(self.user.name).yellow()}{C(' DEBUG MODE').bright_magenta() if self.debug else ''}\Resumed {C(boot_duration).cyan()}"
        )

    # Message handler to block bots
    async def on_message(self, message: discord.Message):
        if not message.author.bot:
            await self.process_commands(message)

    # Reaction added
    async def on_reaction_add(
        self, reaction: discord.Reaction, user: Union[discord.User, discord.Member]
    ):
        if user != self.user and not reaction.is_custom_emoji():
            message = reaction.message

            if (
                reaction.emoji
                == "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}"
                and message.author == user
            ):
                await self.on_message(message)

            elif (
                reaction.emoji == "\N{WASTEBASKET}\N{VARIATION SELECTOR-16}"
                and message.author == self.user
            ):
                await message.delete()


def main():
    bot = SnakeBot()
    bot.run(bot.token)


if __name__ == "__main__":
    main()
