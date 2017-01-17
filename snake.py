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

from random import choice
from bs4 import BeautifulSoup as bs4
from datetime import datetime
from functools import partial
from contextlib import contextmanager
from io import StringIO

from cogs.utils import config, time, checks
from cogs.utils.colors import paint, back, attr
from cogs.utils import sql

from discord.ext import commands
from discord.state import ConnectionState

try:
    import uvloop
except ModuleNotFoundError:
    print("Can't find uvloop, defaulting to standard event loop")
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    print("Found uvloop")

discord_logger = logging.getLogger("discord")
discord_logger.setLevel(logging.ERROR)

class ShareManager:
    def __init__(self, bot_class, *args, **kwargs):
        self.bot_class = bot_class
        self.chat_ids = {}
        self.shards = {}
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

    def set_shard_count(self, shard_count):
        self.shard_count = shard_count
        self.kwargs["shard_count"] = shard_count

    def _read_config(self, filename):
        with open(filename, 'r', encoding="utf-8") as cfg:
            return json.load(cfg)

    @property
    def servers(self):
        return [server for server in [shard.servers for shard in self.shards.values()]]

    @property
    def channels(self):
        return [channel for channel in [server.channels for server in self.servers.values()]]

    @property
    def members(self):
        return [member for member in [channel.members for channel in self.channels.values()]]

    async def global_eval(self, code, ctx):
        return {shard.shard_id: await shard.run_eval(code, ctx) for shard in self.shards.values()}

    async def global_exec(self, code, ctx):
        return {shard.shard_id: await shard.run_exec(code, ctx) for shard in self.shards.values()}

    async def global_announce(self, text):
        return {shard.shard_id: await shard.post_announcement(text) for shard in self.shards.values()}

    async def post_suggestion(self, text, ctx):
        return {shard.shard_id: await shard.post_suggestion(text, ctx) for shard in self.shards.values()}

    async def post_server_update(self, text):
        return {shard.shard_id: await shard.post_server_update(text) for shard in self.shards.values()}

    def start_shard(self, shard_id, future=None):
        if self.loop.is_closed():
            print(f"Event loop closed, exiting shard#{shard_id}")

        if future is None:
            print(f"Starting {paint(self.bot_class.__name__, 'cyan')}<{shard_id}>")
        else:
            try:
                result = future.result()
            except Exception as e:
                print(f"Shard#{shard_id} failed to run: [{paint(type(e).__name__, 'b_red')}]: {e}")
            else:
                print(f"{paint(self.bot_class.__name__, 'cyan')}<{shard_id}>: {result}")
            print(f"Attempting resume of shard#{shard_id}")

        new_shard = self.bot_class(self, shard_id, *self.args, **self.kwargs)
        shard_task = self.loop.create_task(new_shard.start(self.credentials["token"]))
        shard_task.add_done_callback(partial(self.start_shard, shard_id))
        self.shards[shard_id] = new_shard

    async def __call__(self):
        for shard_id in range(self.shard_count):
            self.start_shard(shard_id)
            await asyncio.sleep(1)


class SnakeBot(commands.Bot):
    @contextmanager
    def db_scope(self):
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
    def stdout_scope(self):
        old = sys.stdout
        new = StringIO()
        sys.stdout = new
        yield new
        sys.stdout = old

    def log_message(self, message, action):
        author = message.author
        channel = message.channel
        server = channel.server

        with self.db_scope() as session:
            msg_author = session.query(sql.User).filter_by(id=int(author.id)).first()

            if query_author is None:
                msg_author = sql.User(
                    id=int(author.id),
                    name=author.name,
                    nick=author.nick,
                    bot=author.bot,
                    discrim=author.discriminator
                )
                session.add(msg_author)

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

    def check_blacklist(self, content, **kwargs):
        with self.db_scope() as session:
            blacklist_entry = session.query(sql.Blacklist).filter_by(**kwargs).first()
            if blacklist_entry is None:
                return False
            else:
                if isinstance(content, str):
                    return blacklist_entry.data == content
                elif isinstance(content, list):
                    return blacklist_entry in content

    def check_whitelist(self, content, **kwargs):
        with self.db_scope() as session:
            whitelist_entry = session.query(sql.Whitelist).filter_by(**kwargs).first()
            if whitelist_entry is None:
                return False
            else:
                if isinstance(content, str):
                    return whitelist_entry.data == content
                elif isinstance(content, list):
                    return whitelist_entry in content

    def get_prefix(self, bot, message):
        default_prefix = self.shared.config["default_prefix"]
        channel = message.channel

        if channel.is_private:
            return default_prefix
        else:
            server = channel.server
            with self.db_scope() as session:
                prefix_query = session.query(sql.Prefix).filter_by(server_id=server.id).first()
                return default_prefix if prefix_query is None else prefix_query.prefix

    def __init__(self, share_manager, shard_id, *args, **kwargs):
        print(args, kwargs)
        self._DEBUG = any("debug" in arg.lower() for arg in sys.argv)
        self.loop = asyncio.get_event_loop()
        kwargs.update({"shard_id": shard_id, "command_prefix": self.get_prefix})
        self.shared = share_manager

        super().__init__(*args, **kwargs)
        print(f"Shard ID: {self.shard_id} Shard Count: {self.shard_count}")

        self.aio_session = aiohttp.ClientSession()
        self.db = sql.SQL(db_username=os.getenv("SNAKE_DB_USERNAME"), db_password=os.getenv("SNAKE_DB_PASSWORD"), db_name=os.getenv("SNAKE_DB_NAME"))
        self.boot_time = datetime.now()
        self.color_emoji = lambda e: "{}{}".format(choice(["", "\N{EMOJI MODIFIER FITZPATRICK TYPE-1-2}", "\N{EMOJI MODIFIER FITZPATRICK TYPE-3}", "\N{EMOJI MODIFIER FITZPATRICK TYPE-4}", "\N{EMOJI MODIFIER FITZPATRICK TYPE-5}", "\N{EMOJI MODIFIER FITZPATRICK TYPE-6}"]))

        self.log = logging.getLogger()
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(
            logging.FileHandler(filename=f"snake_shard_{self.shard_id}.log", encoding="utf-8", mode='w')
        )

        for filename in os.listdir("cogs"):
            if os.path.isfile("cogs/" + filename) and filename.startswith("command_"):
                name = filename[8:-3]
                cog_name = "cogs.command_" + name
                try:
                    self.load_extension(cog_name)
                except Exception as e:
                    print(f"Failed to load {paint(name, 'b_red')}: [{type(e).__name__}]: {e}")

    async def run_eval(self, code, ctx):
        vals = globals()
        vals.update(dict(
            self=self,
            bot=ctx.bot,
            message=ctx.message,
            ctx=ctx,
            server=ctx.message.server,
            channel=ctx.message.channel,
            author=ctx.message.author,
            code=code,
            servers=self.shared.servers,
        ))

        with self.stdout_scope() as std:
            try:
                precompiled = compile(code, "<eval>", "eval")
                vals["compiled"] = precompiled
                result = eval(precompiled, vals)
            except SyntaxError as e:
                return f"```py\n{e.text}\n{'^':>e.offset}\n{type(e).__name__}: {e}"
            except Exception as e:
                return f"```diff\n- {type(e).__name__}: {e}"

        result = str(s.getvalue())
        if len(result) > 1900:
            return f"Output too long. View results at {self.upload_to_gist(result, 'eval.py')}"
        else:
            return f"```py\n{result}\n```"

    async def run_exec(self, code, ctx):
        code = "async def coro():\n  " + "\n  ".join(code.split("\n"))
        vals = globals()
        vals.update(dict(
            self=self,
            bot=ctx.bot,
            message=ctx.message,
            ctx=ctx,
            server=ctx.message.server,
            channel=ctx.message.channel,
            author=ctx.message.author,
            code=code,
            servers=self.shared.servers,
        ))

        try:
            precompiled = compile(code, "<exec>", "exec")
            vals["compiled"] = precompiled
            result = exec(precompiled, vals)
            await vals["coro"]()
        except SyntaxError as e:
            return f"```py\n{e.text}\n{'^':>e.offset}\n{type(e).__name__}: {e}"
        except Exception as e:
            return f"```diff\n- {type(e).__name__}: {e}"

        if inspect.isawaitable(result):
            result = await result
        result = str(result)

        if len(result) > 1900:
            return f"Output too long. View results at {self.upload_to_gist(result, 'exec.py')}"
        else:
            return f"```py\n{result}\n```"

    async def upload_to_gist(self, content, filename):
        payload = {
            "description": "Code result",
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
                self.log.warning(f"Could not fetch chat response. Retrying.. [{chat_result}]")

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
                self.log.error(f"Could not post to bots.discord.pw ({response.status}")

        async with self.aio_session.post("https://www.carbonitex.net/discord/data/botdata.php", data=carbon_data) as response:
            if response.status != 200:
                self.log.error(f"Could not post to carbonitex.net ({response.status})")

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

    async def on_resume(self):
        print(f"Resumed as {paint(self.user.name, 'blue')}#{paint(self.user.discriminator, 'yellow')} [{paint(self.user.id, 'b_green')}]")
        self.resume_time = datetime.now()
        self.resumed_after = time.get_elapsed_time(self.start_time, self.resume_time)
        print(f"Resumed after {self.resumed_after}")

    async def on_resume(self):
        print(f"Logged in as {paint(self.user.name, 'blue')}#{paint(self.user.discriminator, 'yellow')} [{paint(self.user.id, 'b_green')}]")
        self.start_time = datetime.now()
        self.resumed_after = time.get_elapsed_time(self.boot_time, self.start_time)
        print(f"Resumed after {self.boot_duration}")

    async def on_command_error(self, error, ctx):
        if isinstance(error, commands.NoPrivateMessage):
            await self.send_message(ctx.message.author, "\N{WARNING SIGN} Sorry, you can't use this command in a private message!")
        elif isinstance(error, commands.DisabledCommand):
            await self.send_message(ctx.message.author, "\N{WARNING SIGN} Sorry, this command is disabled!")
        elif isinstance(error, commands.CommandOnCooldown):
            await self.send_message(ctx.channel, f"{ctx.author.mention} slow down! Try again in {error.retry_after:.1f} seconds.")

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
        self.log.info(f"{destination}: {message.author.name}: {message.clean_content}")

    async def on_message(self, message):
        channel = message.channel
        author = message.author
        if not message.channel.is_private:
            if message.author.bot or self.check_blacklist("server_ignore", server_id=channel.server.id) or self.check_blacklist("channel_ignore", channel_id=channel.id):
                return

            if "(╯°□°）╯︵ ┻━┻" in message.clean_content and self.check_whitelist("unflip", server_id=channel.server.id) and not self.check_blacklist("unflip_channel", channel_id=channel.id):
                await self.send_message(message.channel, "┬─────────────────┬ ノ(:eye:▽:eye:ノ)")

            if isinstance(author, discord.Member):
                await self.loop.run_in_executor(None, partial(self.log_message, message, "create"))

        # TODO: add permission checks
        await self.process_commands(message)

    async def on_message_delete(self, message):
        channel = message.channel
        author = message.author
        if channel.is_private is False and isinstance(author, discord.Member):
            await self.loop.run_in_executor(None, partial(self.log_message, message, "delete"))

    async def on_message_edit(self, old_message, new_message):
        channel = message.channel
        author = message.author
        if old_message.content != new_message.content:
            if channel.is_private is False and isinstance(author, discord.Member):
                await self.loop.run_in_executor(None, partial(self.log_message, message, "edit"))

    async def on_server_join(self, server):
        if self.check_blacklist("server_join", server_id=server.id):
            await self.leave_server(server)
            return
        await self.shared.post_server_update(f"Joined **{server.name}** [{server.id}] (owned by **{server.owner.display_name}**#**{server.owner.discriminator}** [{server.owner.id}]) ({len(self.shared.servers)} total servers)")
        await self.update_servers()

    async def on_server_remove(self, server):
        await self.shared.post_server_update(f"Left **{server.name}** [{server.id}] (owned by **{server.owner.display_name}**#**{server.owner.discriminator}** [{server.owner.id}]) ({len(self.shared.servers)} total servers)")
        await self.update_servers()


share_manager = ShareManager(SnakeBot)

try:
    shard_count = int(sys.argv[1])
except:
    shard_count = share_manager.config["default_shard_count"]
finally:
    share_manager.set_shard_count(shard_count)

loop = asyncio.get_event_loop()
print(f"Starting {paint(share_manager.bot_class.__name__, 'cyan')}<0 -> {share_manager.shard_count}>")
loop.run_until_complete(share_manager())