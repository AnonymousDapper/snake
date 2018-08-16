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

from .utils import sql
from .utils.logger import get_logger

log = get_logger()

class Analytics:
    def __init__(self, bot):
        self.bot = bot

        log.debug("Adding listeners")

        # Setup listeners
        bot.add_listener(self.on_socket_response)
        bot.add_listener(self.on_command)
        bot.add_listener(self.on_message)
        bot.add_listener(self.on_message_delete)
        bot.add_listener(self.on_message_edit)

        log.debug("Successfully added listeners for: socket_response, command, message, message_delete, message_edit")

    # Logging

    # Messages
    async def log_message(self, message, action):
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
                timestamp=message.created_at.strftime(self.bot.config["Format"]["msg_time"]),
                author_id=author.id,
                channel_id=channel.id,
                guild_id=guild.id,
                content=message.content,
                action=action
            )
            session.add(new_message)

    # Commands
    async def log_command_use(self, command_name):
        with self.bot.db.session() as session:
            command = session.query(sql.Command).filter_by(command_name=command_name).first()
            if command is None:
                command = sql.Command(command_name=command_name, uses=0)
                session.add(command)

            command.uses += 1

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

        await self.log_command_use(ctx.command.qualified_name)

    # Message arrived
    async def on_message(self, message):
        channel = message.channel
        author = message.author

        if author.bot or not self.bot.is_ready():
            return

        if hasattr(author, "display_name"):
            await self.log_message(message, "create")

    # Message deleted
    async def on_message_delete(self, message):
        channel = message.channel
        author = message.author
        if hasattr(channel, "guild") and hasattr(author, "display_name"):
            await self.log_message(message, "delete")

    # Messaged edited
    async def on_message_edit(self, old_message, new_message):
        channel = new_message.channel
        author = new_message.author
        if old_message.content != new_message.content:
            if hasattr(channel, "guild") and hasattr(author, "display_name"):
                await self.log_message(new_message, "edit")


def setup(bot):
    bot.add_cog(Analytics(bot))
