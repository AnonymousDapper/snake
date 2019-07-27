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

import traceback

import discord

from datetime import datetime

from discord.ext import commands

#from .utils import sql
from .utils.colors import paint
from .utils.logger import get_logger

log = get_logger()

class Analytics:
    def __init__(self, bot):
        self.bot = bot

        self.pprint_perms = lambda permissions: ", ".join("=".join(map(str, perm)) for perm in list(permissions))

    # Logging

    # Socket data
    def log_socket_data(self, data):
        if "t" in data:
            t_type = data.get("t")

            if t_type is not None:
                if t_type in self.bot.socket_log:
                    self.bot.socket_log[t_type] += 1

                else:
                    self.bot.socket_log[t_type] = 1

    # Commands
    async def log_command_use(self, ctx):
        await self.bot.db.create_command_report(ctx.author, ctx.message, ctx.command, ctx.invoked_with)

    # Message created
    async def log_message(self, message):
        await self.bot.db.create_message(message)

    # Message updated
    async def log_message_change(self, message, edited):
        await self.bot.db.edit_message(message, message.edited_at if edited else datetime.now(), edited)

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
            await self.log_message_change(message, edited=False)

    # Messaged edited
    async def on_message_edit(self, old_message, new_message):
        channel = new_message.channel
        author = new_message.author
        if old_message.content != new_message.content:
            if hasattr(channel, "guild") and hasattr(author, "display_name"):
                await self.log_message_change(new_message, edited=True)

    # Coommand tossed an error
    async def on_command_error(self, ctx, error):
        if ctx.command is not None:
            await self.bot.db.edit_command_report(ctx.message, True)

        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send("\N{WARNING SIGN} You cannot use that command in a private channel")

        elif isinstance(error, commands.CommandNotFound):
            log.debug("Could not find command '%s' (Author: %s)" % (ctx.invoked_with, ctx.author.name))

        elif isinstance(error, commands.CheckFailure):
            log.debug("Check failed for '%s' (Author: %s)" % (ctx.invoked_with, ctx.author.name))

        elif isinstance(error, commands.DisabledCommand):
            await ctx.send("\N{WARNING SIGN} That command is disabled")

        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"{ctx.author.mention} slow down! Try that again in {error.retry_after:.1f} seconds")

        elif isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
            await ctx.send(f"\N{WARNING SIGN} {error}")

        elif isinstance(error, discord.errors.Forbidden):
            log.warn(f"{ctx.command.qualified_name} failed: Forbidden. Required | Have ({self.pprint_perms(self.bot.required_permissions)} | {self.pprint_perms(ctx.channel.permissions_for(ctx.guild.me))})")

        elif isinstance(error, commands.CommandInvokeError):
            original_name = error.original.__class__.__name__
            print(f"In {paint(ctx.command.qualified_name, 'b_red')}:")
            traceback.print_tb(error.original.__traceback__)
            print(f"{paint(original_name, 'red')}: {error.original}")

        else:
            print(f"{paint(type(error).__name__, 'b_red')}: {error}")

    # Commands

def setup(bot):
    bot.add_cog(Analytics(bot))
