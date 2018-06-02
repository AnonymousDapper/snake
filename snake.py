""" Discord API snake bot """

"""
MIT License

Copyright (c) 2016 AnonymousDapper

Permission is hereby granted
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import discord
import asyncio
import os
import logging
import sys
import functools
import traceback
import aiohttp
import json
import subprocess

from bs4 import BeautifulSoup as bs4
from datetime import datetime
from contextlib import contextmanager
from io import StringIO
from inspect import isawaitable

from cogs.utils import time, checks
from cogs.utils.colors import paint, back, attr
from cogs.utils import sql
from cogs.utils import permissions

from cogs.utils.boxy import Boxy

from discord.ext import commands

try:
    import uvloop
except ModuleNotFoundError:
    print("Can't find uvloop, defaulting to standard event loop")
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    print("Using uvloop policy")

class Builtin:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="quit", brief="exit")
    @checks.is_owner()
    async def quit_command(self, ctx):
        asyncio.ensure_future(self.bot.aio_session.close())
        await self.bot.logout()

    @commands.group(name="cog", invoke_without_command=True, brief="manage cogs")
    @checks.is_owner()
    async def manage_cogs(self, ctx, name:str, action:str):
        name = name.lower()
        action = action.lower()
        cog_name = "cogs.command_" + name

        if action == "load":
            if self.bot.extensions.get(cog_name) is not None:
                await ctx.send(f"Cog `{name}` is already loaded")
            else:
                try:
                    self.bot.load_extension(cog_name)
                except Exception as e:
                    await ctx.send(f"Failed to load `{name}`: [{type(e).__name__}]: {e}")
                    return

                finally:
                    await ctx.send(f"Loaded `{name}`")

        elif action == "unload":
            if self.bot.extensions.get(cog_name) is None:
                await ctx.send(f"Cog `{name}` is not loaded")
            else:
                try:
                    self.bot.unload_extension(cog_name)
                except Exception as e:
                    await ctx.send(f"Failed to unload `{name}`: [{type(e).__name__}]: {e}")
                    return

                finally:
                    await ctx.send(f"Unloaded `{name}`")

        elif action == "reload":
            if self.bot.extensions.get(cog_name) is None:
                await ctx.send(f"Cog `{name}` is not loaded")
            else:
                try:
                    self.bot.unload_extension(cog_name)
                    self.bot.load_extension(cog_name)
                except Exception as e:
                    await ctx.send(f"Failed to reload `{name}`: [{type(e).__name__}]: {e}")
                    return

                finally:
                    await ctx.send(f"Reloaded `{name}`")

    @manage_cogs.command(name="list", brief="list cogs")
    @checks.is_owner()
    async def list_cogs(self, ctx, name:str = None):
        if name is None:
            await ctx.send(f"Currently loaded cogs:\n{' '.join('`' + cog_name + '`' for cog_name in self.bot.extensions)}" if len(self.bot.extensions) > 0 else "No cogs loaded")
        else:
            cog_name = "cogs.command_" + name
            await ctx.send(f"`{name}` {'is not' if self.bot.extensions.get(cog_name) is None else 'is'} loaded")

    @commands.command(name="about", brief="some basic info")
    async def about_command(self, ctx):
        result = await self.bot.loop.run_in_executor(None, functools.partial(subprocess.run, 'git log --pretty=format:"%h by %an %ar (%s)" -n 1', stdout=subprocess.PIPE, shell=True, universal_newlines=True))

        await ctx.send(f"```md\n# Snake Bot Info\n* Discord.py {discord.version_info.major}.{discord.version_info.minor}.{discord.version_info.micro}\n* Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}\n* Latest Commit {result.stdout}\n```")

class SnakeBot(commands.Bot):
    @contextmanager
    def db_scope(self): # context manager for database sessions
        session = self.db.Session()
        try:
            yield session
            session.commit()
        except:
            traceback.print_exc()
            session.rollback()
        finally:
            session.close()

    @contextmanager
    def stdout_scope(self): # basically same idea, but for stdout
        old = sys.stdout
        new = StringIO()
        sys.stdout = new
        yield new
        sys.stdout = old

    @contextmanager
    def build_box(self, str_list, **kwargs):
        self.boxer.update(**kwargs)
        box = self.boxer(str_list)
        yield box
        self.boxer.reset()

    def _read_config(self, filename):
        with open(filename, "r", encoding="utf-8") as cfg:
            return json.load(cfg)

    def __init__(self, *args, **kwargs):
        self.log = logging.getLogger()
        self.log.setLevel(logging.INFO)
        self.log.addHandler(
            logging.FileHandler(filename="snake.log", encoding="utf-8", mode="w")
        )

        self._DEBUG = any("debug" == arg.lower() for arg in sys.argv)
        self.loop = asyncio.get_event_loop()
        self.permissions = permissions.Permissions
        self.permissions.bot = self
        self.config = self._read_config("config.json")
        self.invite_url = discord.utils.oauth_url("181584771510566922", permissions=discord.Permissions(permissions=8))

        credentials = self._read_config("credentials.json")
        self.token = credentials["token"]

        self.boxer = Boxy()

        self.newline = "\n"
        self.author_ids = [163521874872107009, 190966952649293824]

        super().__init__(
            *args,
            **kwargs,
            description="\nHsss!\n",
            help_attrs=dict(hidden=True),
            command_not_found="\N{WARNING SIGN} Whoops, '{}' doesn't exist!",
            command_has_no_subcommand="\N{WARNING SIGN} Sorry, '{1}' isn't part of '{0.name}'",
            command_prefix=self.get_prefix
        )

        self.aio_session = aiohttp.ClientSession()
        self.db = sql.SQL(db_name="snake", db_username=os.environ.get("SNAKE_DB_USERNAME"), db_password=os.environ.get("SNAKE_DB_PASSWORD"))
        self.boot_time = datetime.now()

        for filename in os.listdir("cogs"):
            if os.path.isfile("cogs/" + filename) and filename.startswith("command_"):
                name = filename[8:-3]
                cog_name = "cogs.command_" + name
                try:
                    self.load_extension(cog_name)
                except Exception as e:
                    print(f"Failed to load {paint(name, 'b_red')}: [{type(e).__name__}]: {e}")

    async def log_message(self, message, action):
        author = message.author
        channel = message.channel
        guild = channel.guild

        with self.db_scope() as session:
            msg_author = session.query(sql.User).filter_by(id=author.id).first()

            if msg_author is None:
                msg_author = sql.User(
                    id=author.id,
                    name=author.name,
                    bot=author.bot,
                    discrim=author.discriminator
                )
                session.add(msg_author)

            elif msg_author.name != author.name:
                msg_author.name = author.name

            elif msg_author.discrim != author.discriminator:
                msg_author.discrim = author.discriminator

            new_message = sql.Message(
                id=message.id,
                timestamp=message.created_at.strftime(self.config.get("msg_strftime")),
                author_id=author.id,
                author=msg_author,
                channel_id=channel.id,
                guild_id=guild.id,
                content=message.content,
                action=action
            )
            session.add(new_message)

    async def check_blacklist(self, data, **kwargs):
        if kwargs.get("user_id", 0) in self.author_ids:
            return False

        with self.db_scope() as session:
            blacklist_entry = session.query(sql.Blacklist).filter_by(**kwargs).first()
            if blacklist_entry is None:
                return False
            else:
                if isinstance(data, str):
                    return blacklist_entry.data == data
                elif isinstance(data, list):
                    return blacklist_entry.data in data

    async def check_whitelist(self, data, **kwargs):
        if kwargs.get("user_id", 0) in self.author_ids:
            return True

        with self.db_scope() as session:
            whitelist_entry = session.query(sql.Whitelist).filter_by(**kwargs).first()
            if whitelist_entry is None:
                return False
            else:
                if isinstance(data, str):
                    return whitelist_entry.data == data
                elif isinstance(data, list):
                    return whitelist_entry.data in data

    async def get_prefix(self, message):
        default_prefix = self.config.get("default_prefix")
        channel = message.channel

        if isinstance(channel, discord.abc.PrivateChannel):
            return default_prefix
        else:
            guild = channel.guild
            with self.db_scope() as session:
                prefix_query = session.query(sql.Prefix).filter_by(guild_id=guild.id).first()
                return default_prefix if prefix_query is None else prefix_query.prefix

    async def log_command_use(self, command_name):
        with self.db_scope() as session:
            command = session.query(sql.Command).filter_by(command_name=command_name).first()
            if command is None:
                command = sql.Command(command_name=command_name, uses=0)
                session.add(command)

            command.uses = command.uses + 1

    async def run_eval(self, code, ctx):
        vals = globals()
        vals.update(dict(
            bot=self,
            message=ctx.message,
            ctx=ctx,
            guild=ctx.guild,
            channel=ctx.channel,
            author=ctx.author,
            code=code
        ))

        try:
            precompiled = compile(code, "<eval>", "eval")
            vals["compiled"] = precompiled
            result = eval(precompiled, vals)
        except SyntaxError as e:
            return f"```py\n{e.text}\n{'^':>{e.offset}}\n{type(e).__name__}: {e}\n```"
        except Exception as e:
            return f"```diff\n- {type(e).__name__}: {e}\n```"

        if isawaitable(result):
            result = await result

        result = str(result)
        if len(result) > 1900:
            gist = await self.upload_to_gist(result, "eval.py")
            return f"\N{WARNING SIGN} Output too long. View result at {gist}\n"
        else:
            return f"```py\n{result}\n```"

    async def run_exec(self, code, ctx):
        code = "async def coro():\n  " + "\n  ".join(code.split("\n"))
        vals = globals()
        vals.update(dict(
            bot=self,
            message=ctx.message,
            ctx=ctx,
            guild=ctx.guild,
            channel=ctx.channel,
            author=ctx.author,
            code=code
        ))

        with self.stdout_scope() as std:
            try:
                precompiled = compile(code, "<exec>", "exec")
                vals["compiled"] = precompiled
                result = exec(precompiled, vals)
                await vals["coro"]()
            except SyntaxError as e:
                return f"```py\n{e.text}\n{'^':>{e.offset}}\n{type(e).__name__}: {e}\n```"
            except Exception as e:
                return f"```diff\n- {type(e).__name__}: {e}\n```"

        result = str(std.getvalue())
        if len(result) > 1900:
            gist = await self.upload_to_gist(result, "exec.py")
            return f"\N{WARNING SIGN} Output too long. View result at {gist}\n"
        else:
            return f"```py\n{result}\n```"

    async def upload_to_gist(self, content, filename, title="Command Result"):
        payload = {
            "description": title,
            "files": {
                filename: {
                    "content": content
                }
            }
        }

        async with self.aio_session.post("https://api.github.com/gists", data=json.dumps(payload), headers={"Content-Type": "application/json"}) as response:
            if response.status != 201:
                return f"Could not upload: {response.status}"
            else:
                data = await response.json()
                return data["html_url"]

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
            traceback.print_exc(e)
            await message.channel.send(reaction_emoji)


    async def on_ready(self):
        self.start_time = datetime.now()
        self.boot_duration = time.get_elapsed_time(self.boot_time, self.start_time)
        with self.build_box([f"Logged in as {paint(self.user.name, 'green')}#{paint(self.user.discriminator, 'yellow')}" ,f"Loaded in {paint(self.boot_duration, 'cyan')}"], color="yellow", text_color="b_blue", footer_color="b_magenta", footer="DEBUG MODE" if self._DEBUG else "") as msg:
            print(msg)

    async def on_resume(self):
        self.resume_time = datetime.now()
        self.resumed_after = time.get_elapsed_time(self.start_time, self.resume_time)
        with self.build_box([f"Resumed as {paint(self.user.name, 'green')}#{paint(self.user.discriminator, 'yellow')}", f"Resumed in {paint(self.resumed_after, 'cyan')}"], color="yellow", text_color="b_blue", footer_color="b_magenta", footer="DEBUG MODE" if self._DEBUG else "") as msg:
            print(msg)

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send("\N{WARNING SIGN} Sorry, you can't use this command in a private message!")

        elif isinstance(error, commands.CommandNotFound):
            await ctx.send("\N{CROSS MARK} That command doesn't exist!")

        elif isinstance(error, commands.DisabledCommand):
            await ctx.send("\N{WARNING SIGN} Sorry, this command is disabled!")

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

    async def on_command(self, ctx):
        message = ctx.message
        destination = None
        if isinstance(message.channel, discord.abc.PrivateChannel):
            destination = "Private Message"
        else:
            destination = f"[{message.guild.name} #{message.channel.name}]"
        self.log.info(f"{destination}: {message.author.name}: {message.clean_content}")
        await self.log_command_use(ctx.command.qualified_name)

    async def on_message(self, message):
        channel = message.channel
        author = message.author
        if not isinstance(channel, discord.abc.PrivateChannel):
            if author.bot or await self.check_blacklist("command", guild_id=channel.guild.id) or await self.check_blacklist("command", channel_id=channel.id):
                return

            if isinstance(author, discord.Member):
                await self.log_message(message, "create")

        if not await self.check_blacklist("command", user_id=author.id):
            # TODO: implement role permission checking

            await self.process_commands(message)

        else:
            print("Failed user check")

    async def on_message_delete(self, message):
        channel = message.channel
        author = message.author
        if not isinstance(channel, discord.abc.PrivateChannel) and isinstance(author, discord.Member):
            await self.log_message(message, "delete")

    async def on_message_edit(self, old_message, new_message):
        channel = new_message.channel
        author = new_message.author
        if old_message.content != new_message.content:
            if not isinstance(channel, discord.abc.PrivateChannel) and isinstance(author, discord.Member):
                await self.log_message(new_message, "edit")

bot = SnakeBot()

bot.add_cog(Builtin(bot))

bot.run(bot.token)