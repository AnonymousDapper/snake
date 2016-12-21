""" Discord API 'snake'"""

"""
MIT License

Copyright (c) 2016 Spoopy Saitama (TickerOfTime)

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

# Imports
import discord, asyncio, os, logging, sys, traceback, aiohttp, json, sqlalchemy, websockets
from contextlib import contextmanager
from random import choice as rand_choice
from bs4 import BeautifulSoup as b_soup
from discord.ext import commands
from datetime import datetime
import sqlalchemy
from cogs.utils import config, time, checks
from cogs.utils import sql
from cogs.utils.colors import paint, back, attr

# Base library logging
discord_logger = logging.getLogger("discord")
discord_logger.setLevel(logging.ERROR)

bot = None

# Commands

async def quit_command():
    payload = {"op": bot.EXIT}
    await bot.shard_send(payload)
    #await bot._exit()

# SnakeBot class

class SnakeBot(commands.Bot):
    EXIT = 0
    RESTART = 1
    EVENT = 2
    PING = 3
    PONG = 4
    DATA = 5
    IDENTIFY = 6
    SHARD_COUNT = 7

    def __init__(self, *args, **kwargs):
        self.config = self._read_config("config.json")
        self._DEBUG = any("debug" in arg for arg in sys.argv)
        self.credentials = config.Config("credentials.json")

        self.loop = asyncio.get_event_loop()
        self.shard_ws = None
        self.shard_count = None
        self.shard_id = int(sys.argv[1])

        self.db = sql.SQL(db_username=os.getenv("SNAKE_DB_USERNAME"), db_password=os.getenv("SNAKE_DB_PASSWORD"), db_name=os.getenv("SNAKE_DB_NAME"))
        self.cust_ids = {}
        self.boot_time = datetime.now()
        self.color_emoji = lambda e: "{}{}".format(rand_choice(["", "\N{EMOJI MODIFIER FITZPATRICK TYPE-1-2}", "\N{EMOJI MODIFIER FITZPATRICK TYPE-3}", "\N{EMOJI MODIFIER FITZPATRICK TYPE-4}", "\N{EMOJI MODIFIER FITZPATRICK TYPE-5}", "\N{EMOJI MODIFIER FITZPATRICK TYPE-6}"]))


        self.log = logging.getLogger()
        self.log.setLevel(logging.INFO)
        self.log.addHandler(
            logging.FileHandler(filename="snake_shard{}.log".format(self.shard_id), encoding="utf-8", mode='w')
        )

    @contextmanager
    def session_scope(self):
        session = self.db.Session()
        try:
            yield session
            session.commit()
        except:
            traceback.print_exc()
            session.rollback()
        finally:
            session.close()

    def get_prefix(self, bot, message):
        return "snake "

    def _get_ping(self, t_1, t_2):
        return abs(t_2 - t_1).microseconds / 1000

    def _read_config(self, filename):
        with open(filename, 'r', encoding="utf-8") as f:
            return json.load(f)

    def _color(self, text, color_code):
        return "\033[3{}m{}\033[0m".format(color_code, text)

    def _log_shard(self, event_name, op, unknown=False):
        if unknown:
            print("Unknown op {} on shard #{}".format(op, self.shard_id))
        else:
            print("{} on shard #{}".format(self._color(event_name, op), self.shard_id))

    async def _run_shard_event(self, event, *args, **kwargs):
        try:
            await getattr(self, event)(*args, **kwargs)
        except asyncio.CancelledError:
            pass
        except Exception:
            try:
                await self.on_shard_error(event, *args, **kwargs)
            except asyncio.CancelledError:
                pass

    def shard_dispatch(self, event, *args, **kwargs):
        method = "on_" + event
        handler = "handle_" + event

        if hasattr(self, handler):
            getattr(self, handler)(*args, **kwargs)
        if hasattr(self, method):
            asyncio.ensure_future(self._run_shard_event(method, *args, **kwargs), loop=self.loop)

    async def on_shard_error(self, event_method, *args, **kwargs):
        print("Ignoring shard exception in {}".format(event_method), file=sys.stderr)
        traceback.print_exc()

    def close_shard(self):
        try:
            asyncio.ensure_future(self.shard_ws.close(code=1004, reason="closing"))
        except:
            pass
        #pending = asyncio.Task.all_tasks()
        #gathered = asyncio.gather(*pending)
        #try:
        #    gathered.cancel()
        #    self.loop.run_until_complete(gathered)
        #    gathered.exception()
        #except:
        #    pass
        self.loop.stop()
        #self.loop.close()
        sys.exit()

    async def _exit(self):
        await self.logout()
        self.close_shard()

    async def shard_send(self, payload):
        data = bytes(json.dumps(payload), "utf-8")
        try:
            await self.shard_ws.send(data)
        except websockets.exceptions.ConnectionClosed:
            print("Server closed")
            self.close_shard()

    def _shard_decode(self, raw_data):
        data = None
        if isinstance(raw_data, bytes):
            # Assuming UTF-8 encoding ¯\_(ツ)_/¯
            data = raw_data.decode(encoding="utf-8")
        elif isinstance(raw_data, str):
            data = raw_data
        else:
            raise ValueError("Data must be bytes or str. Got {}".format(type(raw_data).__name__))
        try:
            data = json.loads(data)
        except:
            pass
        return data

    async def poll_shard(self):
        try:
            data = await self.shard_ws.recv()
            await self.process_shard_message(data)
        except websockets.exceptions.ConnectionClosed:
            print("Server closed")
            self.close_shard()

    async def process_shard_message(self, message):
        self.shard_dispatch("raw_data", message)
        message = self._shard_decode(message)
        self.shard_dispatch("data", message)

        op = message.get("op")
        data = message.get("data")
        event = message.get("event")

        if op == self.EXIT:
            self._log_shard("EXIT", op)
            await self._exit()

        elif op == self.RESTART:
            self._log_shard("RESTART", op)
            # Nothing yet

        elif op == self.EVENT:
            self._log_shard("EVENT", op)
            self.shard_dispatch(event, **data)

        elif op == self.PING:
            self._log_shard("PING", op)
            payload = {
                "op": self.PONG,
                "data": {
                    "reply": datetime.now().strftime("%H-%M-%S:%f")
                }
            }
            await self.shard_send(payload)

        elif op == self.PONG:
            self._log_shard("PONG", op)
            if hasattr(self.shard_ws, "temp_ping"):
                self.shard_ws.temp_pong = datetime.strptime(data.get("reply"), "%H-%M-%S:%f")
                self.shard_ws.ping = self._get_ping()
                del self.shard_ws.temp_ping
                del self.shard_ws.temp_pong

        elif op == self.DATA:
            self._log_shard("DATA", op)
            try:
                self.shard_dispatch("data", *data, **data)
            except:
                pass

        elif op == self.IDENTIFY:
            self._log_shard("IDENTIFY", op)

        elif op == self.SHARD_COUNT:
            self._log_shard("SHARD_COUNT", op)

        else:
            self._log_shard("", op, unknown=True)

    async def __call__(self, url):
        self.log.info("Attempting IPC connection")
        print("Connecting to local IPC broker with shard ID #{}..".format(self.shard_id))
        self.shard_ws = await websockets.client.connect(url)

        try:
            await self.shard_send(dict(shard_id=self.shard_id, op=self.IDENTIFY))
        except websockets.exceptions.ConnectionClosed as e:
            print("Connection closed. [{}]".format(e.reason))
            self.close_shard()

        try:
            shard_data = await self.shard_ws.recv()
            shard_count = self._shard_decode(shard_data)["data"]["shard_count"]
        except websockets.exceptions.ConnectionClosed as e:
            print("Connection closed. [{}]".format(e.reason))
            self.close_shard()
        except Exception:
            print("Malformed data {}".format(shard_data))
            self.close_shard()

        self.shard_count = shard_count

        super().__init__(command_prefix=self.get_prefix, shard_count=self.shard_count, shard_id=self.shard_id, description="\nHsss! Go to discord.gg/qC4ancm for help!\n", help_attrs=dict(hidden=True), command_not_found="Command '{}' does not exist", command_has_no_subcommands="Command '{0.name}' does not have any subcommands")

        self.loop.create_task(self.start(self.credentials.get("token")))

        self.add_command(commands.Command(name="quit", callback=quit_command, brief="exit", checks=[checks.is_owner()]))

        for filename in os.listdir("./cogs"):
            if os.path.isfile("cogs/" + filename) and filename.startswith("command_"):
                name = filename[8:-3]
                cog_name = "cogs.command_" + name
                try:
                    self.load_extension(cog_name)
                except Exception as e:
                    print("Failed to load {}: [{}]: {}".format(paint(name, "red"), type(e).__name__, e))

        while self.shard_ws.open:
            try:
                await self.poll_shard()
            except websockets.exceptions.ConnectionClosed as e:
                print("Shard #{} closed. [{}]".format(self.shard_id, e.reason))
                self.close_shard()

    async def on_resume(self):
        print("Resumed in as {}#{} [{}]".format(paint(self.user.name, "cyan"), paint(self.user.discriminator, "yellow"), paint(self.user.id, "green")))
        self.resume_time = datetime.now()
        print("Loaded in {}".format(self.boot_duration))

    async def on_ready(self):
        print("Logged in as {}#{} [{}]".format(paint(self.user.name, "cyan"), paint(self.user.discriminator, "yellow"), paint(self.user.id, "green")))
        self.start_time = datetime.now()
        self.boot_duration = time.get_ping_time(self.boot_time, self.start_time)
        print("Loaded in {}".format(self.boot_duration))

    async def on_command_error(self, error, ctx):
        if isinstance(error, commands.NoPrivateMessage):
            await self.send_message(ctx.message.author, "You cannot use this command in a private message")

        elif isinstance(error, commands.DisabledCommand):
            await self.send_message(ctx.message.author, "This command is disabled")

        elif isinstance(error, commands.CommandOnCooldown):
            await self.send_message(ctx.channel, "{} slow down! Try again in {:.1f} seconds".format(ctx.author.mention, error.retry_after))

        elif isinstance(error, commands.CommandInvokeError):
            original_name = error.original.__class__.__name__
            print("In {}:".format(paint(ctx.command.qualified_name, "red")))
            traceback.print_tb(error.original.__traceback__)
            print("{}: {}".format(paint(original_name, "red"), error.original))

        # Bad or missing argument alerts??
        else:
            print("{}: {}".format(paint(type(error).__name__, "red"), error))

    async def on_command(self, command, ctx):
        message = ctx.message
        destination = None
        if message.channel.is_private:
            destination = "Private Message"
        else:
            destination = "[{0.server.name} #{0.channel.name}]".format(message)
        self.log.info("{1}: {0.author.name}: {0.clean_content}".format(message, destination))

    async def on_message(self, message):
        author = message.author
        with self.session_scope() as session:
            sql_author = session.query(sql.User).filter_by(id=int(author.id)).first()
            print(sql_author)
            if sql_author is None:
                sql_author = sql.User(id=int(author.id), name=author.name, nick=author.nick, bot=author.bot, discrim=author.discriminator)

            new_message = sql.Message(id=int(message.id), timestamp=message.timestamp.strftime(self.config.get("msg_strftime")), author_id=int(author.id), author=sql_author, channel_id=int(message.channel.id), server_id=int(message.server.id), content=message.content, edited=False, deleted=False)
            print("added new message {0!r}".format(new_message))

            session.add(sql_author)
            session.add(new_message)

        await self.process_commands(message)

# more class functions here


bot = SnakeBot() # here we goooooo


loop = asyncio.get_event_loop()

try:
    loop.run_until_complete(bot("ws://localhost:5230"))
except KeyboardInterrupt:
    loop.run_until_complete(bot._exit())

finally:
    loop.stop()