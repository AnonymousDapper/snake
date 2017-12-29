import discord

from discord.ext import commands

from .utils import checks

from .utils.music.api import YoutubeAPI
from .utils.music.player import FFmpegStreamSource

class PlayerWrapper:
    def __init__(self, requester, channel, track):
        self.requester = requester
        self.channel = channel
        self.track = track

        embed = discord.Embed(title=track.title, url=track.get_url(), description=track.description.strip("\r"))
        embed.set_author(name=track.uploader)
        embed.set_thumbnail(url=track.thumbnail_url)
        embed.add_field(name="Requested by", value=requester.display_name, inline=True)
        embed.add_field(name="Duration", value=track.get_duration(), inline=True)

        self.data_embed = embed

    def display(self):
        print(self.data_embed.to_dict())
        return self.data_embed

    def get_source(self):
        return FFmpegStreamSource(self.track)


class Music:
    def __init__(self, bot):
        self.bot = bot
        self.youtube_api = YoutubeAPI()

    @commands.command(name="play", brief="play music")
    @checks.permissions(queue_music=True, play_music=True)
    async def play(self, ctx, *, search_term:str):
        query_type, data = self.youtube_api.determine_query_type(search_term)
        term = search_term

        if query_type == "search":
            videos = await self.youtube_api.search_videos(data)
            term = videos[0]["id"]

        elif query_type == "video":
            term = data

        else:
            await ctx.send("Playlists not supported yet.")
            return

        video = await self.youtube_api.get_video_from_id(term)

        author = ctx.message.author
        channel = ctx.message.channel

        wrapper = PlayerWrapper(author, channel, video)

        await ctx.send(embed=wrapper.display())


def setup(bot):
    bot.add_cog(Music(bot))