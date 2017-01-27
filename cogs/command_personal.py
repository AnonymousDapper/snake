import discord

from discord.ext import commands
from datetime import datetime

from .utils import checks, time


class Personal:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="getinvite", aliases=["ginvite"], pass_context=True, brief="get an invite")
    @checks.is_owner()
    async def get_invite(self, ctx, *, server_name: str):
        server = discord.utils.get(self.bot.shared.servers, name=server_name)

        print(server)
        if server is None:
            await self.bot.whisper("\N{WARNING SIGN} That server can't be found")
        else:
            invite = await self.bot.create_invite(server, max_uses=1)
            await self.bot.whisper(f"Invite for **{server.name}**: {invite.url}")

    @commands.command(name="announce", pass_context=True, brief="broadcast a message")
    @checks.is_owner()
    async def announce(self, ctx, *, message:str):
        author = ctx.message.author
        start_time = datetime.now()
        results = await self.bot.shared.global_announce(f"Announcement from **{author.name}** (Owner):\n{message}")
        result_text = f"Finished in {time.get_ping_time(start_time, datetime.now())}\n```md\n"
        result_text += "\n".join(f"- Shard {shard_id} -> {r[0]}/{r[1]} servers ({(100 * (r[0] / r[1])):.0f}%)\n" for shard_id, r in results.items())
        total = (sum(r[0] for s, r in results.items()), sum(r[1] for s, r in results.items()))
        result_text += f"\n\n## Total -> {total[0]}/{total[1]} ({(100 * (total[0] / total[1])):.0f}%)\n```"

        await self.bot.say(result_text)

    @commands.command(name="voice", pass_context=True, brief="check voice status")
    @checks.is_owner()
    async def check_voice(self, ctx):
        results = await self.bot.shared.get_voice_status()
        result_text = "```md\n"
        result_text += "\n".join(f"- Shard {shard_id} -> {r[0]}/{r[1]} servers ({(100 * (r[0] / r[1])):.0f}%)\n" for shard_id, r in results.items())
        total = (sum(r[0] for s, r in results.items()), sum(r[1] for s, r in results.items()))
        result_text += f"\n\n## Total -> {total[0]}/{total[1]} ({(100 * (total[0] / total[1])):.0f}%)\n```"

        await self.bot.say(result_text)

def setup(bot):
    bot.add_cog(Personal(bot))