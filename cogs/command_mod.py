import discord

from discord.ext import commands
from .utils import checks

class Moderation:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="prune", brief="erase messages", no_pm=True)
    @checks.is_owner()
    async def prune_messages(self, ctx, amount: int = 25):
        try:
            result = await ctx.channel.purge(limit=amount, check=lambda m: True, before=ctx.message)
        except discord.Forbidden:
            await self.bot.post_reaction(ctx.message)

        await self.bot.post_reaction(ctx.message, success=True)


def setup(bot):
    bot.add_cog(Moderation(bot))