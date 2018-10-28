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
import os
import sys

from datetime import datetime

import aiohttp
import discord
import toml

from discord.ext import commands
from pympler.tracker import SummaryTracker

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
log = None

class Builtin:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="quit", brief="exit bot")
    @checks.is_developer()
    async def quit_command(self, ctx):
        await self.bot.aio_session.close()
        await self.bot.db.close()

        await self.bot.logout()

    @commands.group(name="cog", brief="manage cogs", invoke_without_command=True)
    @checks.is_developer()
    async def manage_cogs(self, ctx, name: str, action: str):
        print("cogs")

    @manage_cogs.command(name="load", brief="load cog")
    @checks.is_developer()
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
    @checks.is_developer()
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
    @checks.is_developer()
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
    @checks.is_developer()
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
        output = discord.Embed(title="About snake", color=0x1DE9B6, description=f"You can invite snake from the [botlist page](https://bots.discord.pw/bots/181584790980526081) or directly [here]({self.bot.invite_url})")

        output.set_thumbnail(url=self.bot.user.avatar_url)

        # TODO: support server and whatnot

        await ctx.send(embed=output)


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

        if self.debug:
            self.tracker = SummaryTracker()

        self.loop = asyncio.get_event_loop()
        # TODO: Permissions init here

        # Load config and in-memory storage
        self.config = self._read_config("config.toml")
        self.socket_log = {}

        self.required_permissions = discord.Permissions(permissions=70380609)
        self.invite_url = discord.utils.oauth_url(self.config["General"]["client_id"], permissions=self.required_permissions)

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
        logger.set_database(self.db)

        global log
        log = logger.get_logger()

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
        author = ctx.author
        channel = ctx.channel

        if author.id in self.config["General"]["owners"]:
            return True

        return False

    # Misc functions

    # Safely create HTTP client session
    async def create_client_session(self):
        log.info("Creating client session for bot")
        self.aio_session = aiohttp.ClientSession()

    # Get prefix for guild or default
    async def get_prefix(self, message):
        default_prefix = self.config["General"]["default_prefix"]

        return default_prefix

        # channel = message.channel

        # if not hasattr(channel, "guild"):
        #     return default_prefix

        # else:
        #     guild = channel.guild
        #     with self.db.session() as session:
        #         prefix_query = session.query(sql.Prefix).filter_by(guild_id=guild.id).first()
        #         return default_prefix if prefix_query is None else prefix_query.prefix

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
        async with self.aio_session.post("https://paste.a-sketchy.site/documents", data=content, headers={"Content-Type": "application/json"}) as response:
            if response.status != 200:
                return f"Could not upload: ({response.status})"

            data = await response.json()
            return f"https://paste.a-sketchy.site/{data['key']}"

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

    # Message handler to block bots
    async def on_message(self, message):
        if not message.author.bot:
            await self.process_commands(message)

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
        print("Exiting..")

        return True


# Running
with SnakeBot() as bot:
    bot.run(bot.token)
