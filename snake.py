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


import aiohttp
import asyncio
import discord
import functools
import os
import subprocess
import sys
import toml
import traceback

from contextlib import contextmanager
from datetime import datetime
from inspect import isawaitable
from io import StringIO

from cogs.utils import logger
from cogs.utils import permissions
from cogs.utils import sql
from cogs.utils import time, checks
from cogs.utils.colors import paint, back, attr
from cogs.utils.imgur import ImgurAPI

from discord.ext import commands

# Attempt to load uvloop for improved event loop performance
try:
    import uvloop

except ModuleNotFoundError:
    print("Can't find uvloop, defaulting to standard policy")

else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    print("Using uvloop policy")

_DEBUG = any("debug" == arg.lower() for arg in sys.argv)

# Logging setup
logger.set_level(_DEBUG)
log = logger.get_logger()

class Builtin:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="quit", brief="exit bot")
    @checks.is_owner()
    async def quit_command(self, ctx):
        asyncio.ensure_future(self.bot.aio_session.close())
        await self.bot.logout()

    @commands.group(name="cog", brief="manage cogs", invoke_without_command=True)
    @checks.is_owner()
    async def manage_cogs(self, ctx, name:str, action:str):
        name = name.lower()
        action = action.lower()
        cog_name = "cogs.command_" + name

        if action == "load":
            if self.bot.extensions.get(cog_name) is not None:
                await self.bot.post_reaction(ctx.message, emoji="\N{SHRUG}")

            else:
                try:
                    self.bot.load_extension(cog_name)

                except Exception as e:
                    await ctx.send(f"Failed to load {name}: [{type(e).__name__}]: `{e}`")
                    return

                else:
                    await self.bot.post_reaction(ctx.message, success=True)

        elif action == "unload":
            if self.bot.extensions.get(cog_name) is None:
                await self.bot.post_reaction(ctx.message, emoji="\N{SHRUG}")

            else:
                try:
                    self.bot.unload_extension(cog_name)

                except Exception as e:
                    await ctx.send(f"Failed to unload {name}: [{type(e).__name__}]: `{e}`")
                    return

                else:
                    await self.bot.post_reaction(ctx.message, success=True)

        elif action == "reload":
            if self.bot.extensions.get(cog_name) is None:
                await self.bot.post_reaction(ctx.message, emoji="\N{SHRUG}")

            else:
                try:
                    self.bot.unload_extension(cog_name)
                    self.bot.load_extension(cog_name)



                except Exception as e:
                    await ctx.send(f"Failed to reload {name}: [{type(e).__name__}]: `{e}`")
                    return

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
    # stderr wrapper
    @contextmanager
    def stderr_wrapper(self):
        old_err = sys.stderr

        new_err = StringIO()

        sys.stderr = new_err

        yield new_err

        sys.stderr = old_err

    # stdout wrapper
    @contextmanager
    def stdout_wrapper(self):
        old_out = sys.stdout

        new_out = StringIO()

        sys.stdout = new_out

        yield new_out

        sys.stdout = old_out

    # Quick method to read toml configs
    def _read_config(self, filename):
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
        self.invite_url = discord.utils.oauth_url("181584771510566922", permissions=discord.Permissions(permissions=70380609))

        # Load credentials
        credentials = self._read_config("credentials.toml")
        self.token = credentials["Discord"]["token"]

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

    # Logging

    # Messages
    async def log_message(self, message, action):
        author = message.author
        channel = message.channel
        guild = channel.guild

        with self.db.session() as session:
            msg_author = session.query(sql.User).filter_by(id=author.id).first()

            if msg_author is None:
                msg_author = sql.User(
                    id=author.id,
                    name=author.name,
                    bot=author.bot,
                    discrim=author.discriminator
                )
                session.add(msg_author)

            if msg_author.name != author.name:
                msg_author.name = author.name

            if msg_author.discrim != author.discriminator:
                msg_author.discrim = author.discriminator

            new_message = sql.Message(
                id=message.id,
                timestamp=message.created_at.strftime(self.config["Format"]["msg_time"]),
                author_id=author.id,
                channel_id=channel.id,
                guild_id=guild.id,
                content=message.content,
                action=action
            )
            session.add(new_message)

    # Socket data
    async def log_socket_data(self, data):
        if "t" in data:
            t_type = data.get("t")

            if t_type is not None:
                if t_type in self.socket_log:
                    self.socket_log[t_type] += 1

                else:
                    self.socket_log[t_type] = 1

    # Commands
    async def log_command_use(self, command_name):
        with self.db.session() as session:
            command = session.query(sql.Command).filter_by(command_name=command_name).first()
            if command is None:
                command = sql.Command(command_name=command_name, uses=0)
                session.add(command)

            command.uses += 1

    # Misc functions

    # Safely create HTTP client session
    async def create_client_session(self):
        log.info("Creating client session for bot")
        self.aio_session = aiohttp.ClientSession()

    # Blacklist
    async def check_blacklist(self, data, condition):
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
        print(f"Resumed as {paint(self.user.name, 'green')}#{paint(self.user.discriminator, 'yellow')}{paint(' DEBUG MODE', 'b_magenta') if self.debug else ''}\nResumed in {paint(boot_duration, 'cyan')}")

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

        elif isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.BadArgument):
            await ctx.send(f"\N{WARNING SIGN} {error}")

        elif isinstance(error, commands.CommandInvokeError):
            original_name = error.original.__class__.__name__
            print(f"In {paint(ctx.command.qualified_name, 'b_red')}:")
            traceback.print_tb(error.original.__traceback__)
            print(f"{paint(original_name, 'red')}: {error.original}")

        else:
            print(f"{paint(type(error).__name__, 'b_red')}: {error}")

    # Command was triggered
    async def on_command(self, ctx):
        message = ctx.message
        destination = None

        if isinstance(message.channel, discord.abc.PrivateChannel):
            destination = "Private Message"

        else:
            destination = f"[{message.guild.name} #{message.channel.name}]"

        log.info(f"{destination}: {message.author.name}: {message.clean_content}")

        await self.log_command_use(ctx.command.qualified_name)

    # Message arrived
    async def on_message(self, message):
        channel = message.channel
        author = message.author

        if not isinstance(channel, discord.abc.PrivateChannel):
            if author.bot or await self.check_blacklist("command", (sql.Blacklist.guild_id == channel.guild.id) | (sql.Blacklist.channel_id == channel.id)):
                return

            if isinstance(author, discord.Member):
                await self.log_message(message, "create")

        if not await self.check_blacklist("command", sql.Blacklist.user_id == author.id):
            # TODO: role permission checking

            await self.process_commands(message)

        else:
            self.log.info(f"Failed blacklist check for {author.name} ({author.id})")

    # Message deleted
    async def on_message_delete(self, message):
        channel = message.channel
        author = message.author
        if not isinstance(channel, discord.abc.PrivateChannel) and isinstance(author, discord.Member):
            await self.log_message(message, "delete")

    # Messaged edited
    async def on_message_edit(self, old_message, new_message):
        channel = new_message.channel
        author = new_message.author
        if old_message.content != new_message.content:
            if not isinstance(channel, discord.abc.PrivateChannel) and isinstance(author, discord.Member):
                await self.log_message(new_message, "edit")

    # Reaction added
    async def on_reaction_add(self, reaction, user):
        if not reaction.me and not reaction.custom_emoji:
            message = reaction.message

            if reaction.emoji == "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}":
                await self.on_message(message)

            elif reaction.emoji == "\N{WASTEBASKET}" and message.author == message.guild.me:
                await message.delete()

    # Socket event arrived
    async def on_socket_response(self, payload):
        if self.debug:
            await self.log_socket_data(payload)

# Running
bot = SnakeBot()

bot.add_cog(Builtin(bot))

bot.run(bot.token)