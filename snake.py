""" Discord API snake bot """

"""
MIT License

Copyright (c) 2016 AnonymousDapper (TickerOfTime)

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

import discord, asyncio, os, logging, sys, traceback, aiohttp, json

from bs4 import BeautifulSoup as bs4
from datetime import datetime
from functools import partial
from contextlib import contextmanager
from io import StringIO
from inspect import isawaitable
from importlib import import_module
from inspect import getmodule as get_module

from cogs.utils import time, checks
from cogs.utils.colors import paint, back, attr
from cogs.utils import sql
from cogs.utils import permissions

from discord.ext import commands

try:
    import uvloop # uvloop is better, but not supported on windows.
except ModuleNotFoundError:
    print("Can't find uvloop, defaulting to standard event loop")
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    print("Using uvloop")


# weird fix for single-process sharding issue
# maybe when rewrite is stable we can stop using this

def cmd_fix(self, instance, owner):
    if instance is not None:
        self.instance = instance
    return self

commands.Command.__get__ = cmd_fix


class Builtin:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="quit", pass_context=True, brief="exit")
    @checks.is_owner()
    async def quit_command(self, ctx):
        await self.bot.shared.close_all()

    @commands.group(name="cog", pass_context=True, invoke_without_command=True, brief="manage cogs")
    @checks.is_owner()
    async def manage_cogs(self, ctx, name:str, action:str):
        cog_name = "cogs.command_" + name
        action = action.lower()

        if action == "load":
            if self.bot.shared.extensions.get(cog_name) is not None:
                await self.bot.say(f"Cog `{name}` is already loaded")
                return
            try:
                self.bot.shared.load_extension(cog_name)
            except Exception as e:
                await self.bot.say(f"Failed to load `{name}`: [{type(e).__name__}]: {e}")
                return
            await self.bot.say(f"Loaded `{name}`")

        elif action == "unload":
            if self.bot.shared.extensions.get(cog_name) is None:
                await self.bot.say(f"Cog `{name}` is not loaded")
                return
            try:
                self.bot.shared.unload_extension(cog_name)
            except Exception as e:
                await self.bot.say(f"Failed to unload `{name}`: [{type(e).__name__}]: {e}")
                return
            await self.bot.say(f"Unloaded `{name}`")

        elif action == "reload":
            if self.bot.shared.extensions.get(cog_name) is None:
                await self.bot.say(f"Cog `{name}` is not loaded")
                return
            try:
                self.bot.shared.unload_extension(cog_name)
                self.bot.shared.load_extension(cog_name)
            except Exception as e:
                await self.bot.say(f"Failed to reload `{name}`: [{type(e).__name__}]: {e}")
                return
            await self.bot.say(f"Reloaded `{name}`")

    @manage_cogs.command(name="list", pass_context=True, brief="list cogs")
    @checks.is_owner()
    async def list_cogs(self, ctx, name:str = None):
        if name is None:
            await self.bot.say(f"Currently loaded cogs:\n{' '.join('`' + cog_name + '`' for cog_name in self.bot.shared.extensions)}" if len(self.bot.extensions) > 0 else "No cogs loaded")
        else:
            cog_name = "cogs.command_" + name
            await self.bot.say(f"`{cog_name}` {'is not' if self.bot.shared.extensions.get(cog_name) is None else 'is'} loaded")

    @commands.command(name="support", pass_context=True, brief="user support")
    async def get_support(self, ctx):
        await self.bot.say(f"```md\n# Owner: Syn-Ack\n# Dev: Steve Harvey Oswald\n\n# Status: We're in the middle of a rewrite folks! (and YouTube is being a pain)\n```\n{self.bot.shared.invite_url}")

class ShareManager:
    def __init__(self, bot_class, *args, **kwargs):
        self.bot_class = bot_class
        self.chat_ids = {}
        self.shards = {}
        self.extensions = {}
        self.shard_tasks = {}
        self.shard_connect_failures = {}

        self.shard_count = 0
        self.loop = asyncio.get_event_loop()
        self.config = self._read_config("config.json")
        self.credentials = self._read_config("credentials.json")

        self.description = kwargs.pop("description", "\nHsss! Checkout the support command the join the official server!\n")
        self.pm_help = kwargs.pop("pm_help", False)
        self.help_attrs = kwargs.pop("help_attrs", dict(hidden=True))
        self.command_not_found = kwargs.pop("command_not_found", "\N{WARNING SIGN} Whoops, '{}' doesn't exist!")
        self.command_has_no_subcommands = kwargs.pop("command_has_no_subcommands", "\N{WARNING SIGN} Sorry, '{0.name}' doesn't have '{1}'")

        self.invite_url = "https://discord.gg/qC4ancm"
        self.kwargs = kwargs
        self.args = args

        self.kwargs.update({
            "description": self.description,
            "pm_help": self.pm_help,
            "help_attrs": self.help_attrs,
            "command_not_found": self.command_not_found,
            "command_has_no_subcommands": self.command_has_no_subcommands,
            "shard_count": self.shard_count
        })

        self.log = logging.getLogger()
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(
            logging.FileHandler(filename="snake.log", encoding="utf-8", mode='w')
        )

    def set_shard_count(self, shard_count):
        self.shard_count = shard_count
        self.kwargs["shard_count"] = shard_count

    def _read_config(self, filename):
        with open(filename, 'r', encoding="utf-8") as cfg:
            return json.load(cfg)

    @property
    def servers(self):
        server_list = []
        for shard_id, shard in self.shards.items():
            for server in shard.servers:
                # setattr(server, "shard_id", shard_id)
                server_list.append(server)

        return server_list

        # return [server for server in [shard.servers for shard in self.shards.values()]]

    @property
    def channels(self):
        channel_list = []
        for server in self.servers:
            for channel in server.channels:
                channel_list.append(channel)

        return channel_list

        #return [channel for channel in [server.channels for server in self.servers]]

    @property
    def members(self):
        member_list = []
        for server in self.servers:
            for member in server.members:
                member_list.append(member)

        return member_list

        # return [member for member in [channel.members for channel in self.channels]]

    async def global_eval(self, code, ctx):
        return {shard.shard_id: await shard.run_eval(code, ctx) for shard in self.shards.values()}

    async def global_exec(self, code, ctx):
        return {shard.shard_id: await shard.run_exec(code, ctx) for shard in self.shards.values()}

    async def global_announce(self, text):
        return {shard.shard_id: await shard.post_announcement(text) for shard in self.shards.values()}

    async def post_suggestion(self, text):
        return {shard.shard_id: await shard.post_suggestion(text) for shard in self.shards.values()}

    async def post_server_update(self, text):
        return {shard.shard_id: await shard.post_server_update(text) for shard in self.shards.values()}

    async def get_voice_status(self):
        return {shard.shard_id: await shard.get_voice_status() for shard in self.shards.values()}

    def load_extension(self, extension_name):
        for shard in self.shards.values():
            if extension_name in shard.extensions:
                continue
            else:
                ext_lib = import_module(extension_name)

                if not hasattr(ext_lib, "setup"):
                    del ext_lib
                    del sys.modules[extension_name]
                    raise discord.ClientException("extension does not have a setup function")

                ext_lib.setup(shard)
                shard.extensions[extension_name] = ext_lib
                self.extensions[extension_name] = ext_lib

    def unload_extension(self, extension_name): # horrible hacks to make cogs work with single process sharding
        for shard in self.shards.values():
            if not extension_name in shard.extensions.keys():
                continue

            ext_lib = shard.extensions[extension_name]

            # print("removing cogs")
            for cog_name, cog in shard.cogs.copy().items():
                if get_module(cog) is ext_lib:
                    shard.remove_cog(cog_name)

            # print("removing commands")
            for command in shard.commands.copy().values():
                if command.module is ext_lib:
                    command.module = None
                    if isinstance(command, commands.GroupMixin):
                        command.recursively_remove_all_commands()

                    shard.remove_command(command.name)

            # print("removing events")
            for event_list in shard.extra_events.copy().values():
                remove = []
                for idx, event in enumerate(event_list):
                    if get_module(event) is ext_lib:
                        remove.append(idx)

                for idx in reversed(remove):
                    del event_list[idx]

            # print("tearing down")
            try:
                teardown_func = getattr(ext_lib, "teardown")
            except AttributeError:
                pass
            else:
                try:
                    func(shard)
                except:
                    pass
            finally:
                del shard.extensions[extension_name]

        del self.extensions[extension_name]
        del sys.modules[extension_name]
        # print("finished")

    async def close_all(self):
        for shard_id, shard in self.shards.items():
            print(f"Closing {paint(self.bot_class.__name__, 'cyan')}<{shard_id}>")
            self.shard_tasks[shard_id].cancel()
            await shard.logout()
            shard.loop.stop()
        print(f"Closed {shard_id + 1} shards, exiting..")
        self.loop.stop()
        sys.exit(0)

    def start_shard(self, shard_id, future=None):
        if self.loop.is_closed():
            print(f"Event loop closed, exiting shard#{shard_id}")

        if future is None:
            print(f"Starting {paint(self.bot_class.__name__, 'cyan')}<{shard_id}>")

        else:
            try:
                result = future.result()

            except asyncio.CancelledError: # task was cancelled, it was probably the close_all call
                return

            except aiohttp.ClientOSError:
                if self.shard_connect_failures[shard_id] < 4:
                    self.shard_connect_failures[shard_id] += 1
                    print(f"Shard#{shard_id} lost connection, retrying with {paint(self.shard_connect_failures[shard_id], 'red')} failures so far")
                else:
                    print(f"Shard#{shard_id} could not connect after 4 retries")
                    return

                if all(retries == 4 for retries in self.shard_connect_failures.values()):
                    print(paint("All shards lost connection.", "red"))
                    sys.exit(1)

            except Exception as e:
                print(f"Shard#{shard_id} failed to run: [{paint(type(e).__name__, 'b_red')}]: {e}")

            else:
                print(f"{paint(self.bot_class.__name__, 'cyan')}<{shard_id}>: {result}")

            print(f"Attempting resume of shard#{shard_id}")

        new_shard = self.bot_class(self, shard_id, *self.args, **self.kwargs)
        new_shard.add_cog(Builtin(new_shard))

        shard_task = self.loop.create_task(new_shard.start(self.credentials["token"]))
        shard_task.add_done_callback(partial(self.start_shard, shard_id)) # oh this is weird

        self.shard_tasks[shard_id] = shard_task
        self.shards[shard_id] = new_shard
        if shard_id not in self.shard_connect_failures:
            self.shard_connect_failures[shard_id] = 0

    async def __call__(self):
        for shard_id in range(self.shard_count):
            self.start_shard(shard_id)
        await asyncio.sleep(1)

        for filename in os.listdir("cogs"): # dynamically load cogs
            if os.path.isfile("cogs/" + filename) and filename.startswith("command_"):
                name = filename[8:-3]
                cog_name = "cogs.command_" + name
                try:
                    self.load_extension(cog_name)
                except Exception as e:
                    print(f"Failed to load {paint(name, 'b_red')}: [{type(e).__name__}]: {e}")


class SnakeBot(commands.Bot):
    def log_socket(self, data, send=False):
        if isinstance(data, str):
            json_data = json.loads(data)
            op_type = json_data.get("t")
            if op_type is not None:
                if op_type.lower() == "voice_state_update":
                    if json_data["d"]["guild_id"] == "180133909923758080":
                        print(f"[Shard {self.shard_id}] client {paint('>>' if send else '<<', 'green')} server {paint(op_type.upper(), 'blue')} -> {json_data}")

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
    def stdout_scope(self): # kinda same idea
        old = sys.stdout
        new = StringIO()
        sys.stdout = new
        yield new
        sys.stdout = old

    def __init__(self, share_manager, shard_id, *args, **kwargs):
        self._DEBUG = any("debug" in arg.lower() for arg in sys.argv)
        self.loop = asyncio.get_event_loop()
        self.shared = share_manager
        self.permissions = permissions.Permissions
        self.permissions.bot = self

        self.newline = "\n" # F-strings dont like backslashes
        self.author_ids = ["163521874872107009", "190966952649293824"]

        super().__init__(*args, **kwargs, shard_id=shard_id, command_prefix=self.get_prefix)

        self.aio_session = aiohttp.ClientSession()
        self.db = sql.SQL(db_username=os.getenv("SNAKE_DB_USERNAME"), db_password=os.getenv("SNAKE_DB_PASSWORD"), db_name=os.getenv("SNAKE_DB_NAME"))
        self.boot_time = datetime.now()

    async def log_message(self, message, action): # log the messages
        author = message.author
        channel = message.channel
        server = channel.server

        with self.db_scope() as session:
            msg_author = session.query(sql.User).filter_by(id=int(author.id)).first() # SQLAlchemy query

            if msg_author is None:
                msg_author = sql.User(
                    id=int(author.id),
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
                id=int(message.id),
                timestamp=message.timestamp.strftime(self.shared.config.get("msg_strftime")),
                author_id=int(author.id),
                author=msg_author,
                channel_id=int(channel.id),
                server_id=int(server.id),
                content=message.content,
                action=action
            )
            session.add(new_message)

    async def check_blacklist(self, content, **kwargs):
        if str(kwargs.get("user_id", '0')) in self.author_ids:
            return False

        with self.db_scope() as session:
            blacklist_entry = session.query(sql.Blacklist).filter_by(**kwargs).first() # check for whatever we were sent in kwargs
            if blacklist_entry is None:
                return False
            else:
                if isinstance(content, str):
                    return blacklist_entry.data == content
                elif isinstance(content, list):
                    return blacklist_entry in content

    async def check_whitelist(self, content, **kwargs):
        if str(kwargs.get("user_id", '0')) in self.author_ids:
            return True

        with self.db_scope() as session:
            whitelist_entry = session.query(sql.Whitelist).filter_by(**kwargs).first()
            if whitelist_entry is None:
                return False
            else:
                if isinstance(content, str):
                    return whitelist_entry.data == content
                elif isinstance(content, list):
                    return whitelist_entry in content

    async def get_prefix(self, bot, message): # get custom prefix for server if it exists
        default_prefix = self.shared.config["default_prefix"]

        channel = message.channel

        if channel.is_private:
            return default_prefix
        else:
            server = channel.server
            with self.db_scope() as session:
                prefix_query = session.query(sql.Prefix).filter_by(server_id=int(server.id)).first()
                return default_prefix if prefix_query is None else prefix_query.prefix

    async def log_command_use(self, command_name):
        with self.db_scope() as session:
            command = session.query(sql.Command).filter_by(command_name=command_name).first()
            if command is None:
                command = sql.Command(command_name=command_name, uses=0)
                session.add(command)

            command.uses = command.uses + 1
            # session scope automatically commits

    async def run_eval(self, code, ctx):
        vals = globals()
        vals.update(dict(
            bot=self,
            message=ctx.message,
            ctx=ctx,
            server=ctx.message.server,
            channel=ctx.message.channel,
            author=ctx.message.author,
            code=code,
            shared=self.shared
        ))

        try:
            precompiled = compile(code, "<eval>", "eval")
            vals["compiled"] = precompiled
            result = eval(precompiled, vals)
        except SyntaxError as e:
            return f"```py\n{e.text}\n{'^':>{e.offset}}\n{type(e).__name__}: {e}\n```" # emulate builtin syntaxerror formatting
        except Exception as e:
            return f"```diff\n- {type(e).__name__}: {e}\n```"

        if isawaitable(result):
            result = await result

        result = str(result)
        if len(result) > 1900:
            gist = await self.upload_to_gist(result, 'eval.py')
            return f"\N{WARNING SIGN} Output too long. View results at {gist}\n"
        else:
            return f"```py\n{result}\n```"

    async def run_exec(self, code, ctx):
        code = "async def coro():\n  " + "\n  ".join(code.split("\n"))
        vals = globals()
        vals.update(dict(
            bot=self,
            message=ctx.message,
            ctx=ctx,
            server=ctx.message.server,
            channel=ctx.message.channel,
            author=ctx.message.author,
            code=code,
            shared=self.shared
        ))

        with self.stdout_scope() as std:
            try:
                precompiled = compile(code, "<exec>", "exec")
                vals["compiled"] = precompiled
                result = exec(precompiled, vals)
                await vals["coro"]() # exec takes an expr, so we have to call it. this also enables async in exec
            except SyntaxError as e:
                return f"```py\n{e.text}\n{'^':>{e.offset}}\n{type(e).__name__}: {e}\n```"
            except Exception as e:
                return f"```diff\n- {type(e).__name__}: {e}\n```"

        result = str(std.getvalue())
        if len(result) > 1900:
            gist = await self.upload_to_gist(result, 'exec.py')
            return f"\N{WARNING SIGN} Output too long. View results at {gist}\n"
        else:
            return f"```py\n{result}\n```"

    async def upload_to_gist(self, content, filename, title="Code result"):
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
                return "Could not upload"
            else:
                data = await response.json()
                return data["html_url"]

    async def chat(self, user, text):
        user_id = user.id
        chat_data = {"botid": self.shared.config.get("pb_bot_id"), "input": text}
        if user_id in self.shared.chat_ids:
            chat_data.update({"custid": self.shared.chat_ids[user_id]})

        async def fetch():
            async with self.aio_session.post("http://www.pandorabots/com/pandora/talk-xml", data=chat_data) as response:
                if response.status != 200:
                    return response.status
                response_text = await response.text()
                chat_soup = bs4(response_text, "lxml")
                cust_id = chat_soup.find("result")["custid"]
                answer = chat_soup.find("that").text.strip()
                self.shared.chat_ids[user_id] = cust_id
                return answer

        success = False
        while sucess is False:
            chat_result = await fetch()
            if isinstance(chat_result, str):
                success = True
                return chat_result
            else:
                self.shared.log.warning(f"Could not fetch chat response. Retrying.. [{chat_result}]")

    async def update_servers(self):
        server_count = len(self.shared.servers)

        bots_headers = {
            "Authorization": self.shared.credentials.get("bots_token"),
            "Content-Type": "application/json"
        }

        bots_data = json.dumps({
            "server_count": server_count
        })

        carbon_data = {
            "servercount": server_count,
            "key": self.shared.credentials.get("carbon_key")
        }

        async with self.aio_session.post(f"https://bots.discord.pw/api/bots/{self.user.id}/stats", headers=bots_headers, data=bots_data) as response:
            if response.status != 200:
                self.shared.log.error(f"Could not post to bots.discord.pw ({response.status}")

        async with self.aio_session.post("https://www.carbonitex.net/discord/data/botdata.php", data=carbon_data) as response:
            if response.status != 200:
                self.shared.log.error(f"Could not post to carbonitex.net ({response.status})")

    async def post_server_update(self, text):
        channel = self.get_channel("234512725554888705")
        if channel is not None:
            try:
                await self.send_message(channel, text)
            except:
                pass

    async def post_suggestion(self, text):
        channel = self.get_channel("270718022866567178")
        if channel is not None:
            try:
                await self.send_message(channel, text)
            except:
                pass

    async def post_announcement(self, text):
        failed_servers = 0
        for server in list(self.servers):
            if not await self.check_blacklist("announce", server_id=int(server.id)):
                try:
                    await self.send_message(server.default_channel, text)
                except Exception as e:
                    failed_servers += 1
                    # print(f"[{type(e).__name__}]: {e}")
            else:
                failed_servers += 1

        server_count = len(self.servers)
        succeeded_servers = server_count - failed_servers
        return succeeded_servers, server_count

    async def get_voice_status(self):
        servers = self.servers
        total_servers = len(servers)
        voice_servers = sum(1 for server in servers if self.voice_client_in(server))
        return voice_servers, total_servers

    async def on_resume(self):
        print(f"Resumed as {paint(self.user.name, 'blue')}#{paint(self.user.discriminator, 'yellow')} Shard #{paint(self.shard_id, 'magenta')} [{paint(self.user.id, 'b_green')}] {paint('DEBUG MODE', 'b_cyan') if self._DEBUG else ''}")
        self.resume_time = datetime.now()
        self.resumed_after = time.get_elapsed_time(self.start_time, self.resume_time)
        print(f"Resumed after {self.resumed_after}")

    async def on_ready(self):
        print(f"Logged in as {paint(self.user.name, 'blue')}#{paint(self.user.discriminator, 'yellow')} Shard #{paint(self.shard_id, 'magenta')} [{paint(self.user.id, 'b_green')}] {paint('DEBUG MODE', 'b_cyan') if self._DEBUG else ''}")
        self.start_time = datetime.now()
        self.boot_duration = time.get_elapsed_time(self.boot_time, self.start_time)
        print(f"Loaded in {self.boot_duration}")

    async def on_command_error(self, error, ctx):
        if isinstance(error, commands.NoPrivateMessage):
            await self.send_message(ctx.message.author, "\N{WARNING SIGN} Sorry, you can't use this command in a private message!")

        elif isinstance(error, commands.DisabledCommand):
            await self.send_message(ctx.message.author, "\N{WARNING SIGN} Sorry, this command is disabled!")

        elif isinstance(error, commands.CommandOnCooldown):
            await self.send_message(ctx.message.channel, f"{ctx.message.author.mention} slow down! Try again in {error.retry_after:.1f} seconds.")

        elif isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.BadArgument):
            await self.send_message(ctx.message.channel, f"\N{WARNING SIGN} {error}")

        elif isinstance(error, commands.CommandInvokeError):
            original_name = error.original.__class__.__name__
            print(f"In {paint(ctx.command.qualified_name, 'b_red')}:")
            traceback.print_tb(error.original.__traceback__)
            print(f"{paint(original_name, 'red')}: {error.original}")

        else:
            print(f"{paint(type(error).__name__, 'b_red')}: {error}")

    async def on_command(self, command, ctx):
        message = ctx.message
        destination = None
        if message.channel.is_private:
            destination = "Private Message"
        else:
            destination = f"[{message.server.name} #{message.channel.name}]"
        self.shared.log.info(f"SHARD#{self.shard_id} {destination}: {message.author.name}: {message.clean_content}")
        await self.log_command_use(ctx.command.qualified_name) # log that this command was used

    async def on_message(self, message):
        channel = message.channel
        author = message.author
        if not message.channel.is_private:
            if message.author.bot or await self.check_blacklist("command", server_id=int(channel.server.id)) or await self.check_blacklist("command", channel_id=int(channel.id)):
                return

            if "(╯°□°）╯︵ ┻━┻" in message.clean_content and await self.check_whitelist("unflip", server_id=int(channel.server.id)) and not await self.check_blacklist("unflip", channel_id=int(channel.id)):
                await self.send_message(message.channel, "┬─────────────────┬ ノ(:eye:▽:eye:ノ)")

            if isinstance(author, discord.Member):
                await self.log_message(message, "create")

        if not await self.check_blacklist("command", user_id=int(author.id)):
            #for role in author.roles: # TODO: fix whatever you call this
            #    if role.name != "@everyone":
            #        if await self.check_blacklist("command", role_id=int(role.id)):
            #            print("Failed role check")
            #            return

            await self.process_commands(message)
        else:
            print("Failed user check")

    async def on_message_delete(self, message):
        channel = message.channel
        author = message.author
        if channel.is_private is False and isinstance(author, discord.Member):
            await self.log_message(message, "delete")

    async def on_message_edit(self, old_message, new_message):
        channel = new_message.channel
        author = new_message.author
        if old_message.content != new_message.content:
            if channel.is_private is False and isinstance(author, discord.Member):
                await self.log_message(new_message, "edit")

    async def on_server_join(self, server):
        if await self.check_blacklist("server_join", server_id=int(server.id)):
            await self.leave_server(server)
            return
        await self.shared.post_server_update(f"Joined **{server.name}** [{server.id}] (owned by **{server.owner.display_name}**#**{server.owner.discriminator}** [{server.owner.id}]) ({len(self.shared.servers)} total servers)")
        await self.update_servers()

    async def on_server_remove(self, server):
        await self.shared.post_server_update(f"Left **{server.name}** [{server.id}] (owned by **{server.owner.display_name}**#**{server.owner.discriminator}** [{server.owner.id}]) ({len(self.shared.servers)} total servers)")
        await self.update_servers()

    async def on_socket_raw_receive(self, payload):
        self.log_socket(payload)

    async def on_socket_raw_send(self, payload):
        self.log_socket(payload, send=True)

share_manager = ShareManager(SnakeBot)

try:
    shard_count = int(sys.argv[1])
except:
    shard_count = share_manager.config["default_shard_count"]
finally:
    share_manager.set_shard_count(shard_count)

try:
    loop = asyncio.get_event_loop()
    print(f"Starting {paint(share_manager.bot_class.__name__, 'cyan')}<0 -> {share_manager.shard_count - 1}>")
    loop.run_until_complete(share_manager())
    loop.run_forever()
except KeyboardInterrupt:
    loop.stop()
    for shard in share_manager.shards.values():
        loop.run_until_complete(shard.logout())
finally:
    loop.close()