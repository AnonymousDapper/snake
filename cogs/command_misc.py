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

from .utils.logger import get_logger

log = get_logger()

class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="lewd-alert", brief="print alert about lewd activities")
    @commands.guild_only()
    async def lewd_alert(self, ctx, *participants: discord.Member):
        await ctx.send(f"**Lewd Alert**: A *lewd*, *lascivious*, and likely *immoral* act has occured in __{ctx.guild.name}__ #{ctx.channel.name}. Participating individuals include {', '.join(f'`{participant.display_name}`' for participant in participants)}.\nThis incident will be reported.")

        # Lewd Alert: A lewd, lascivious, and possibly immoral act has occured in Discord Bots <#110373943822540800>. Individuals reported as participating in such debauchery include Julia, lewd-alert as a service.
    #This incident will be recorded.


def setup(bot):
    bot.add_cog(Misc(bot))
