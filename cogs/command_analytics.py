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

import discord

from discord.ext import commands

from .utils import sql
from .utils.logger import get_logger

log = get_logger()

class Analytics:
    def __init__(self, bot):
        self.bot = bot

    # Logging

    # Messages
    async def log_message(self, message):
        author = message.author
        channel = message.channel
        guild = channel.guild

        with self.bot.db.session() as session:
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
                timestamp=message.created_at,
                author_id=author.id,
                channel_id=channel.id,
                guild_id=guild.id,
                content=message.content
            )
            session.add(new_message)

    # Updated messages
    async def log_message_change(self, message, deleted=False):
        author = message.author
        channel = message.channel
        guild = channel.guild

        with self.bot.db.session() as session:
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

            new_message = sql.MessageChange(
                id=message.id,
                timestamp=message.created_at,
                author_id=author.id,
                channel_id=channel.id,
                guild_id=guild.id,
                content=message.content,
                deleted=deleted
            )
            session.add(new_message)

    # Commands
    async def log_command_use(self, ctx):
        user = ctx.author
        command_name = ctx.command.qualified_name
        message = ctx.message

        with self.bot.db.session() as session:
            command_author = session.query(sql.User).filter_by(id=user.id).first()

            if command_author is None:
                command_author = sql.User(
                    id=user.id,
                    name=user.name,
                    bot=user.bot,
                    discrim=user.discriminator
                )

                session.add(command_author)

            command = sql.Command(
                message_id=message.id,
                command_name=command_name,
                user_id=user.id,
                timestamp=ctx.message.created_at,
                args=message.clean_content.split(ctx.invoked_with)[1].strip(),
                errored=False
            )

            session.add(command)

    # Socket data
    def log_socket_data(self, data):
        if "t" in data:
            t_type = data.get("t")

            if t_type is not None:
                if t_type in self.bot.socket_log:
                    self.bot.socket_log[t_type] += 1

                else:
                    self.bot.socket_log[t_type] = 1

    # Listener functions

    # Socket event arrived
    async def on_socket_response(self, payload):
        if self.bot.debug:
            self.log_socket_data(payload)

    # Command was triggered
    async def on_command(self, ctx):
        message = ctx.message
        channel = ctx.channel
        author = ctx.author
        destination = None

        if not hasattr(channel, "guild"):
            destination = "Private Message"

        else:
            destination = f"[{ctx.guild.name} #{channel.name}]"

        log.info(f"{destination}: {author.name}: {message.clean_content}")

        await self.log_command_use(ctx)

    # Message arrived
    async def on_message(self, message):
        channel = message.channel
        author = message.author

        if author.bot or (not self.bot.is_ready()):
            return

        if hasattr(author, "display_name"):
            await self.log_message(message)

    # Message deleted
    async def on_message_delete(self, message):
        channel = message.channel
        author = message.author
        if hasattr(channel, "guild") and hasattr(author, "display_name"):
            await self.log_message_change(message, deleted=True)

    # Messaged edited
    async def on_message_edit(self, old_message, new_message):
        channel = new_message.channel
        author = new_message.author
        if old_message.content != new_message.content:
            if hasattr(channel, "guild") and hasattr(author, "display_name"):
                await self.log_message_change(new_message, deleted=False)

    # Coommand tossed an error
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send("\N{WARNING SIGN} You cannot use that command in a private channel")

        elif isinstance(error, commands.CommandNotFound):
            await self.bot.post_reaction(ctx.message, emoji="\N{BLACK QUESTION MARK ORNAMENT}", quiet=True)

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

        if ctx.command_failed:
            with self.bot.db.session() as session:
                command = session.query(sql.Command).filter_by(message_id=ctx.message.id).first()

                if command is not None:
                    command.errored = True



def setup(bot):
    bot.add_cog(Analytics(bot))
