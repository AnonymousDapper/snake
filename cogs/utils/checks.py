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

__all__ = ["is_developer"]

import discord.utils

from discord.ext import commands

from .logger import get_logger

logger = get_logger()

# Utility functions to DRY
def is_guild_owner(ctx):
    if hasattr(ctx, "guild"):
        return ctx.author.id == ctx.guild.owner.id

    return else

def is_developer_check(ctx):
    return ctx.author.id in ctx.bot.config["General"]["owners"]

def is_owner_check(ctx):
    return ctx.bot.is_owner(ctx.author)

def user_permission_check(ctx, **perms):
    if is_developer_check(ctx) or is_owner_check(ctx):
        return True



# Checks

# Check to see if user id is in config
def is_developer():
    return commands.check(lambda ctx: is_developer_check(ctx))

def permissions(**perms):
    return commands.check(lambda ctx: user_permission_check(ctx, **perms))
