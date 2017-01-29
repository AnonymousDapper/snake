import discord

from discord.ext import commands
from datetime import datetime

from .utils import checks, time, MultiMention, sql

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

    @commands.group(name="blacklist", pass_context=True, brief="manage blacklist", no_pm=True, invoke_without_command=True)
    @checks.is_owner()
    async def blacklist_group(self, ctx, *, obj:MultiMention):
        print("blacklist")

    @blacklist_group.command(name="add", pass_context=True, brief="add to blacklist", no_pm=True)
    @checks.is_owner()
    async def blacklist_add(self, ctx, value:str, *, obj:MultiMention):
        if isinstance(obj, discord.Server):
            kwargs = dict(server_id=int(obj.id))

        elif isinstance(obj, discord.Channel):
            kwargs = dict(channel_id=int(obj.id))

        elif isinstance(obj, discord.Role):
            kwargs = dict(role_id=int(obj.id))

        elif isinstance(obj, discord.Member):
            kwargs = dict(user_id=int(obj.id))


        with self.bot.db_scope() as session:
            blacklist_obj = session.query(sql.Blacklist).filter_by(**kwargs, data=value).first()
            if blacklist_obj is not None:
                await self.bot.say(f"{obj.__class__.__name__} **{str(obj)}** has already been blacklisted for `{value}`")
                return
            else:
                blacklist_obj = sql.Blacklist(**kwargs, data=value)
                session.add(blacklist_obj)
                await self.bot.say(f"Blacklisted {obj.__class__.__name__} **{str(obj)}** for `{value}`")

    @blacklist_group.command(name="remove", pass_context=True, brief="remove from blacklist", no_pm=True)
    @checks.is_owner()
    async def blacklist_remove(self, ctx, value:str, *, obj:MultiMention):
        if isinstance(obj, discord.Server):
            kwargs = dict(server_id=int(obj.id))

        elif isinstance(obj, discord.Channel):
            kwargs = dict(channel_id=int(obj.id))

        elif isinstance(obj, discord.Role):
            kwargs = dict(role_id=int(obj.id))

        elif isinstance(obj, discord.Member):
            kwargs = dict(user_id=int(obj.id))


        with self.bot.db_scope() as session:
            blacklist_obj = session.query(sql.Blacklist).filter_by(**kwargs, data=value).first()
            if blacklist_obj is None:
                await self.bot.say(f"{obj.__class__.__name__} **{str(obj)}** is not blacklisted for `{value}`")
                return
            else:
                session.delete(blacklist_obj)
                await self.bot.say(f"Removed {obj.__class__.__name__} **{str(obj)}** from blacklist for `{value}`")

    @blacklist_group.command(name="check", pass_context=True, brief="search blacklist", no_pm=True)
    @checks.is_owner()
    async def blacklist_search(self, ctx, *, obj:MultiMention):
        if isinstance(obj, discord.Server):
            kwargs = dict(server_id=int(obj.id))

        elif isinstance(obj, discord.Channel):
            kwargs = dict(channel_id=int(obj.id))

        elif isinstance(obj, discord.Role):
            kwargs = dict(role_id=int(obj.id))

        elif isinstance(obj, discord.Member):
            kwargs = dict(user_id=int(obj.id))

        with self.bot.db_scope() as session:
            blacklist_objs = session.query(sql.Blacklist).filter_by(**kwargs).all()

            if len(blacklist_objs) > 0:
                result_text = f"```md\n# {obj.__class__.__name__} {str(obj)} is blacklisted for\n" + "\n".join(f"- {b_obj.data}" for b_obj in blacklist_objs) + "\n```"
            else:
                result_text = f"```md\n# {obj.__class__.__name__} {str(obj)} is not blacklisted\n```"

        await self.bot.say(result_text)


def setup(bot):
    bot.add_cog(Personal(bot))