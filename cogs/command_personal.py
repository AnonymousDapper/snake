import discord, aiohttp, json
from discord.ext import commands
from .utils import checks

class Personal:
  def __init__(self, bot):
    self.bot = bot

  @checks.is_owner()
  @commands.command(name="getinvite", brief="get invite for a server",)
  async def get_invite(self, *, server_name : str):
    server = discord.utils.get(self.bot.servers, name=server_name)
    invite = await self.bot.create_invite(server, max_uses=1)
    await self.bot.whisper("Invite for **{}**: {}".format(server.name, invite))

  @checks.is_owner()
  @commands.command(name="announce", brief="broadcast a message", pass_context=True)
  async def announce(self, ctx, *, message : str):
    missed_servers = 0
    author = ctx.message.author
    for server in list(self.bot.servers):
      if server.id not in self.bot.blacklist.get("announce"):
        try:
          await self.bot.send_message(server.default_channel, "Announcement from **{}** (Owner):\n{}".format(author.name, message))
        except:
          missed_servers = missed_servers + 1
      else:
        missed_servers = missed_servers + 1
    server_count = len(self.bot.servers)
    sent_servers = server_count - missed_servers
    await self.bot.say("Sent announcement to {}/{} servers. ({:.0f}%)".format(sent_servers, server_count, 100 * (sent_servers / server_count)))

  @checks.is_owner()
  @commands.command(brief="get voice client info")
  async def voice(self):
    total_servers = len(self.bot.servers)
    servers_with_voice = sum(1 for s in self.bot.servers if self.bot.voice_client_in(s))
    await self.bot.say("Playing music in {}/{} servers. ({:.0f}%)".format(servers_with_voice, total_servers, 100 * (servers_with_voice / total_servers)))

def setup(bot):
  bot.add_cog(Personal(bot))