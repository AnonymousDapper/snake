import discord

from discord.ext import commands
from datetime import datetime

from .utils import checks, time, MultiMention, sql

from .utils.music.api import SpotifyAPI, YoutubeAPI
from .utils.music.player import FFmpegStreamSource

class Personal:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="getinvite", aliases=["ginvite"], brief="get an invite")
    @checks.is_owner()
    async def get_invite(self, ctx, *, guild_name: str):
        guild = discord.utils.get(self.bot.guilds, name=guild_name)

        print(guild)
        if guild is None:
            await ctx.author.send("\N{WARNING SIGN} That guild can't be found")
        else:
            invite = await self.bot.create_invite(guild, max_uses=1)
            await ctx.author.send(f"Invite for **{guild.name}**: {invite.url}")

    @commands.command(name="invite", brief="get invite link for bot")
    @checks.is_owner()
    async def get_bot_invite(self, ctx):
        await ctx.send(f"Invite link for snake: <{self.bot.invite_url}>")

    @commands.command(name="voice", brief="check voice status")
    @checks.is_owner()
    async def check_voice(self, ctx):
        total_guilds = len(self.bot.guilds)
        total_voice_guilds = sum(1 for guild in self.bot.guilds if guild.voice_client is not None)
        await ctx.send(f"{total_voice_guilds} of {total_guilds} guilds ({(100 * (total_voice_guilds / total_guilds)):.0f}%) using voice")

    @commands.group(name="blacklist", brief="manage blacklist", no_pm=True, invoke_without_command=True)
    @checks.is_owner()
    async def blacklist_group(self, ctx, *, obj:MultiMention):
        print("blacklist")

    @blacklist_group.command(name="add", brief="add to blacklist", no_pm=True)
    @checks.is_owner()
    async def blacklist_add(self, ctx, value:str, *, obj:MultiMention):
        if isinstance(obj, discord.guild):
            kwargs = dict(guild_id=int(obj.id))

        elif isinstance(obj, discord.Channel):
            kwargs = dict(channel_id=int(obj.id))

        elif isinstance(obj, discord.Role):
            kwargs = dict(role_id=int(obj.id))

        elif isinstance(obj, discord.Member):
            kwargs = dict(user_id=int(obj.id))


        with self.bot.db_scope() as session:
            blacklist_obj = session.query(sql.Blacklist).filter_by(**kwargs, data=value).first()
            if blacklist_obj is not None:
                await ctx.send(f"{obj.__class__.__name__} **{str(obj)}** has already been blacklisted for `{value}`")
                return
            else:
                blacklist_obj = sql.Blacklist(**kwargs, data=value)
                session.add(blacklist_obj)
                await ctx.send(f"Blacklisted {obj.__class__.__name__} **{str(obj)}** for `{value}`")

    @blacklist_group.command(name="remove", brief="remove from blacklist", no_pm=True)
    @checks.is_owner()
    async def blacklist_remove(self, ctx, value:str, *, obj:MultiMention):
        if isinstance(obj, discord.guild):
            kwargs = dict(guild_id=int(obj.id))

        elif isinstance(obj, discord.Channel):
            kwargs = dict(channel_id=int(obj.id))

        elif isinstance(obj, discord.Role):
            kwargs = dict(role_id=int(obj.id))

        elif isinstance(obj, discord.Member):
            kwargs = dict(user_id=int(obj.id))


        with self.bot.db_scope() as session:
            blacklist_obj = session.query(sql.Blacklist).filter_by(**kwargs, data=value).first()
            if blacklist_obj is None:
                await ctx.send(f"{obj.__class__.__name__} **{str(obj)}** is not blacklisted for `{value}`")
                return
            else:
                session.delete(blacklist_obj)
                await ctx.send(f"Removed {obj.__class__.__name__} **{str(obj)}** from blacklist for `{value}`")

    @blacklist_group.command(name="check", brief="search blacklist", no_pm=True)
    @checks.is_owner()
    async def blacklist_search(self, ctx, *, obj:MultiMention):
        if isinstance(obj, discord.Guild):
            kwargs = dict(guild_id=int(obj.id))

        elif isinstance(obj, discord.TextChannel):
            kwargs = dict(channel_id=int(obj.id))

        elif isinstance(obj, discord.Role):
            kwargs = dict(role_id=int(obj.id))

        elif isinstance(obj, discord.Member):
            kwargs = dict(user_id=int(obj.id))

        with self.bot.db_scope() as session:
            blacklist_objs = session.query(sql.Blacklist).filter_by(**kwargs).all()

            obj_name = "Channel" if obj.__class__.__name__ == "TextChannel" else obj.__class__.__name__
            if len(blacklist_objs) > 0:
                result_text = f"```md\n# {obj_name} {str(obj)} is blacklisted for\n" + "\n".join(f"- {b_obj.data}" for b_obj in blacklist_objs) + "\n```"
            else:
                result_text = f"```md\n# {obj_name} {str(obj)} is not blacklisted\n```"

        await ctx.send(result_text)

    @commands.command(name="avatar", brief="change avatar")
    @checks.is_owner()
    async def change_avatar(self, ctx, *, file_name:str):
        file_name = f"./avatars/{file_name.lower().replace(' ', '_')}.jpg"

        try:
            with open(file_name, 'rb') as f:
                await self.bot.user.edit(avatar=f.read())
        except Exception as e:
            await ctx.send(f"\N{WARNING SIGN} Couldn't change profile picture. `{e}`")
            return
        else:
            await ctx.send("\N{WHITE HEAVY CHECK MARK} Successfully changed profile picture")

    # @commands.command(name="spotify")
    # @checks.is_owner()
    # async def get_spotify(self, ctx, *, url:str):
    #     d_1 = datetime.now()
    #     playlist = await self.spotify_api.get_playlist(url)

    #     await playlist.load_tracks()

    #     await ctx.send(f"Found `{str(playlist)}` in {time.get_ping_time(d_1, datetime.now())}.. loading tracks")

    #     d_1 = datetime.now()

    #     youtube_list = playlist.to_youtube_playlist(self.bot.youtube_api)

    #     failed = await youtube_list.load_tracks()

    #     await ctx.send(f"Loaded tracks from `{str(youtube_list)}` in {time.get_ping_time(d_1, datetime.now())}")

    #     if failed:
    #         await ctx.send(f"Missed {len(failed)} tracks:\n{str(failed)}")


    # @commands.command(name="youtube")
    # @checks.is_owner()
    # async def get_youtube(self, ctx, *, term:str):
    #     d_1 = datetime.now()

    #     query_type, info = self.youtube_api.determine_query_type(term)

    #     if query_type == "search":

    #         videos = await self.youtube_api.search_videos(info)

    #         print(videos)

    #         await ctx.send(f"Selecting {videos[0]['title']} ({videos[0]['id']} uploaded by {videos[0]['channel']}")

    #         top_video = await self.youtube_api.get_video_from_id(videos[0]["id"])

    #         await ctx.send(f"Found `{str(top_video)}` in {time.get_ping_time(d_1, datetime.now())}")

    #     elif query_type == "video":
    #         d_1 = datetime.now()

    #         video = await self.youtube_api.get_video_from_id(info)

    #         await ctx.send(f"Found `{str(video)}` in {time.get_ping_time(d_1, datetime.now())}")

    #     else:

    #         await ctx.send("That's a playlist")

    # @commands.command(name="play")
    # @checks.is_owner()
    # async def play_song(self, ctx, *, search_term):
    #     d_1 = datetime.now()

    #     query_type, data = self.youtube_api.determine_query_type(search_term)

    #     term = search_term

    #     if query_type == "search":
    #         videos = await self.youtube_api.search_videos(data)

    #         term = videos[0]["id"]

    #     elif query_type == "video":
    #         term = data

    #     else:
    #         await ctx.send("That's a playlist")

    #         return

    #     video = await self.youtube_api.get_video_from_id(term)

    #     author = ctx.message.author
    #     voice_channel = author.voice.channel

    #     if voice_channel is None:
    #         return

    #     print(voice_channel)
    #     voice_client = author.guild.voice_client
    #     if voice_client is None:
    #         voice_client = await voice_channel.connect()

    #     print(video)
    #     voice_player = FFmpegStreamSource(video)

    #     voice_client.play(voice_player, after=lambda: print(f"Done playing {str(video)}"))

def setup(bot):
    bot.add_cog(Personal(bot))

# https://developers.google.com/youtube/v3/docs/search
# https://developers.google.com/youtube/v3/getting-started
# https://developer.spotify.com/web-api/get-playlists-tracks/
# https://developer.spotify.com/web-api/tutorial/
# random.shuffle
# https://api.spotify.com/v1/users/jreasley/playlists/20fpBL4vkmGmcEMJhCoNah/tracks?fields=items(track(name,artists(name),album(name))),total,limit
# ffmpeg -i - -f s16le -ar 48000 -ac 2 -loglevel verbose -vn -b:a 128k