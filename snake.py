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

import asyncio
import functools
import os
import subprocess
import sys
import traceback

from datetime import datetime

import aiohttp
import discord
import toml

from discord.ext import commands

from cogs.utils import logger
from cogs.utils import permissions
from cogs.utils import sql
from cogs.utils import time, checks
from cogs.utils.colors import paint
from cogs.utils.imgur import ImgurAPI

# Attempt to load uvloop for improved event loop performance
try:
    import uvloop

except ModuleNotFoundError:
    print("Can't find uvloop, defaulting to standard policy")

else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    print("Using uvloop policy")

_DEBUG = any(arg.lower() == "debug" for arg in sys.argv)

# Logging setup
logger.set_level(debug=_DEBUG)
log = logger.get_logger()

class Builtin:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="quit", brief="exit bot")
    @checks.is_owner()
    async def quit_command(self, ctx):
        self.bot.loop.create_task(self.bot.aio_session.close())
        await self.bot.logout()

    @commands.group(name="cog", brief="manage cogs", invoke_without_command=True)
    @checks.is_owner()
    async def manage_cogs(self, ctx, name: str, action: str):
        print("cogs")

    @manage_cogs.command(name="load", brief="load cog")
    @checks.is_owner()
    async def load_cog(self, ctx, name: str):
        cog_name = "cogs.command_" + name.lower()

        if self.bot.extensions.get(cog_name) is not None:
            await self.bot.post_reaction(ctx.message, emoji="\n{SHRUG}")

        else:
            try:
                self.bot.load_extension(cog_name)

            except Exception as e:
                await ctx.send(f"Failed to load {name}: [{type(e).__name__}]: `{e}`")

            else:
                await self.bot.post_reaction(ctx.message, success=True)

    @manage_cogs.command(name="unload", brief="unload cog")
    @checks.is_owner()
    async def unload_cog(self, ctx, name: str):
        cog_name = "cogs.command_" + name.lower()

        if self.bot.extensions.get(cog_name) is None:
            await self.bot.post_reaction(ctx.message, emoji="\N{SHRUG}")

        else:
            try:
                self.bot.unload_extension(cog_name)

            except Exception as e:
                await ctx.send(f"Failed to unload {name}: [{type(e).__name__}]: `{e}`")

            else:
                await self.bot.post_reaction(ctx.message, success=True)

    @manage_cogs.command(name="reload", brief="reload cog")
    @checks.is_owner()
    async def reload_cog(self, ctx, name: str):
        cog_name = "cogs.command_" + name.lower()

        if self.bot.extensions.get(cog_name) is None:
            await self.bot.post_reaction(ctx.message, emoji="\N{SHRUG}")

        else:
            try:
                self.bot.unload_extension(cog_name)
                self.bot.load_extension(cog_name)

            except Exception as e:
                await ctx.send(f"Failed to reload {name}: [{type(e).__name__}]: `{e}`")

            else:
                await self.bot.post_reaction(ctx.message, success=True)
    @manage_cogs.command(name="list", brief="list loaded cogs")
    @checks.is_owner()
    async def list_cogs(self, ctx, name: str = None):
        if name is None:
            await ctx.send(f"Currently loaded cogs:\n{' '.join('`' + cog_name + '`' for cog_name in self.bot.extensions)}" if len(self.bot.extensions) > 0 else "No cogs loaded")

        else:
            if self.bot.extensions.get("cogs.command_" + name) is None:
                await self.bot.post_reaction(ctx.message, failure=True)

            else:
                await self.bot.post_reaction(ctx.message, success=True)

    @commands.command(name="about", brief="some basic info")
    async def about_command(self, ctx):
        result = await self.bot.loop.run_in_executor(None, functools.partial(subprocess.run, "git log --pretty=format:\"%h by %an %ar (%s)\" -n 1", stdout=subprocess.PIPE, shell=True, universal_newlines=True))

        await ctx.send(f"```md\n# Snake Bot Info\n* Discord.py version {discord.version_info.major}.{discord.version_info.minor}.{discord.version_info.micro}\n* Python version {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}\n* Latest Commit {result.stdout}\n```")

class SnakeBot(commands.Bot):
    # Quick method to read toml configs
    @staticmethod
    def _read_config(filename):
        with open(filename, "r", encoding="utf-8") as cfg:
            return toml.load(cfg)

    # Main init
    def __init__(self, *args, **kwargs):
        self.debug = _DEBUG
        self._session_exists = False

        self.loop = asyncio.get_event_loop()
        # TODO: Permissions init here

        # Load config and in-memory storage
        self.config = self._read_config("config.toml")
        self.socket_log = {}

        self.required_permissions = discord.Permissions(permissions=70380609)
        self.invite_url = discord.utils.oauth_url("181584771510566922", permissions=self.required_permissions)

        # Load credentials
        credentials = self._read_config("credentials.toml")
        self.token = credentials["Discord"]["token"]

        self.start_time = None
        self.resume_time = None

        self.imgur_api = ImgurAPI(client_id=credentials["Imgur"]["client_id"])

        # Init superclass
        super().__init__(
            *args,
            **kwargs,
            description="\nHsss!\n",
            help_attrs=dict(hidden=True),
            command_not_found=None,
            command_has_no_subcommand="\N{WARNING SIGN} Command `{1}` doesn't exist in the `{0.name}` group!",
            command_prefix=self.get_prefix
        )

        # Launch task to initiate HTTP client session
        self.loop.create_task(self.create_client_session())

        # Load database engine
        self.db = sql.SQL(db_name="snake", db_username=os.environ.get("SNAKE_DB_USERNAME"), db_password=os.environ.get("SNAKE_DB_PASSWORD"))

        self.boot_time = datetime.utcnow()

        # Automatic loading of cogs
        for filename in os.listdir("cogs/"):
            if os.path.isfile("cogs/" + filename) and filename.startswith("command_"):
                name = filename[8:-3]
                cog_name = "cogs.command_" + name

                try:
                    self.load_extension(cog_name)
                except Exception as e:
                    print(f"Failed to load {paint(name, 'b_red')}: [{type(e).__name__}]: {e}")

        # Load whitelist check
        self.add_check(self.global_check, call_once=True)

    # Global whitelist/blacklist check
    async def global_check(self, ctx):
        message = ctx.message
        guild = ctx.guild
        author = ctx.author
        channel = ctx.channel

        if author.id in self.config["General"]["owners"]:
            return True

        if await self.check_whitelist("command",
            (sql.Whitelist.user_id == author.id) |
            (sql.Whitelist.guild_id == guild.id) |
            (sql.Whitelist.channel_id == channel.id)
        ):

            return True

        if await self.check_blacklist("command",
            (sql.Blacklist.user_id == author.id) |
            (sql.Blacklist.guild_id == guild.id) |
            (sql.Blacklist.channel_id == channel.id)
        ):

            return False

    # Misc functions

    # Safely create HTTP client session
    async def create_client_session(self):
        log.info("Creating client session for bot")
        self.aio_session = aiohttp.ClientSession()

    # Blacklist
    async def check_blacklist(self, data, condition):
        print("checking blacklist")
        with self.db.session() as session:
            entry = session.query(sql.Blacklist).filter(condition).first()

            if entry is None:
                return False

            else:
                if isinstance(data, str):
                    return entry.data == data

                elif isinstance(data, list):
                    return entry.data in data

    # Whitelist
    async def check_whitelist(self, data, condition):
        print("checking whitelist")
        with self.db.session() as session:
            entry = session.query(sql.Whitelist).filter(condition).first()

            if entry is None:
                return False

            else:
                if isinstance(data, str):
                    return entry.data == data

                elif isinstance(data, list):
                    return entry.data in data

    # Get prefix for guild or default
    async def get_prefix(self, message):
        default_prefix = self.config["General"]["default_prefix"]
        channel = message.channel

        if isinstance(channel, discord.abc.PrivateChannel):
            return default_prefix

        else:
            guild = channel.guild
            with self.db.session() as session:
                prefix_query = session.query(sql.Prefix).filter_by(guild_id=guild.id).first()
                return default_prefix if prefix_query is None else prefix_query.prefix

    # Post a reaction indicating command status
    async def post_reaction(self, message, emoji=None, **kwargs):
        reaction_emoji = ""

        if emoji is None:
            if kwargs.get("success"):
                reaction_emoji = "\N{WHITE HEAVY CHECK MARK}"

            elif kwargs.get("failure"):
                reaction_emoji = "\N{CROSS MARK}"

            elif kwargs.get("warning"):
                reaction_emoji = "\N{WARNING SIGN}"

            else:
                reaction_emoji = "\N{NO ENTRY}"

        else:
            reaction_emoji = emoji

        try:
            await message.add_reaction(reaction_emoji)

        except Exception as e:
            if not kwargs.get("quiet"):
                await message.channel.send(reaction_emoji)

    # Upload long text to personal hastebin
    async def paste_text(self, content):
        async with self.aio_session.post("http://thinking-rock.a-sketchy.site:8000/documents", data=content, headers={"Content-Type": "application/json"}) as response:
            if response.status != 200:
                return f"Could not upload: ({response.status})"

            data = await response.json()
            return f"http://thinking-rock.a-sketchy.site:8000/{data['key']}"

    # Discord events

    # Bot is ready
    async def on_ready(self):
        self.start_time = datetime.utcnow()
        boot_duration = time.get_elapsed_time(self.boot_time, self.start_time)
        print(f"Logged in as {paint(self.user.name, 'green')}#{paint(self.user.discriminator, 'yellow')}{paint(' DEBUG MODE', 'b_magenta') if self.debug else ''}\nLoaded in {paint(boot_duration, 'cyan')}")

    # Bot is resumed
    async def on_resume(self):
        self.resume_time = datetime.utcnow()
        resumed_after = time.get_elapsed_time(self.start_time, self.resume_time)
        print(f"Resumed as {paint(self.user.name, 'green')}#{paint(self.user.discriminator, 'yellow')}{paint(' DEBUG MODE', 'b_magenta') if self.debug else ''}\nResumed in {paint(resumed_after, 'cyan')}")

    # Coommand tossed an error
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send("\N{WARNING SIGN} You cannot use that command in a private channel")

        elif isinstance(error, commands.CommandNotFound):
            await self.post_reaction(ctx.message, emoji="\N{BLACK QUESTION MARK ORNAMENT}", quiet=True)

        elif isinstance(error, commands.DisabledCommand):
            await ctx.send("\N{WARNING SIGN} That command is disabled")

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"{ctx.author.mention} slow down! Try that again in {error.retry_after:.1f} seconds")

        elif isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
            await ctx.send(f"\N{WARNING SIGN} {error}")

        elif isinstance(error, commands.CommandInvokeError):
            original_name = error.original.__class__.__name__
            print(f"In {paint(ctx.command.qualified_name, 'b_red')}:")
            traceback.print_tb(error.original.__traceback__)
            print(f"{paint(original_name, 'red')}: {error.original}")

        else:
            print(f"{paint(type(error).__name__, 'b_red')}: {error}")

    # Reaction added
    async def on_reaction_add(self, reaction, user):
        if not reaction.me and not reaction.custom_emoji:
            message = reaction.message

            if reaction.emoji == "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}":
                await self.on_message(message)

            elif reaction.emoji == "\N{WASTEBASKET}" and message.author == message.guild.me:
                await message.delete()

    # Magic methods for fun code
    def __enter__(self):
        if self.is_ready():
            raise RuntimeError("SnakeBot already started")

        self.add_cog(Builtin(self))

        return self

    def __exit__(self, t, value, tb):
        print(t, value, tb)

        return True


# Running
with SnakeBot() as bot:
    bot.run(bot.token)
