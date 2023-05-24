# MIT License
#
# Copyright (c) 2016-2023 AnonymousDapper
#


from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands
from yarl import URL

from cogs.utils.sql import BoardMessage, Channel, Emote, EmoteBoard

from .utils.logger import get_logger

if TYPE_CHECKING:
    from ..snake import SnakeBot

log = get_logger()


class Board(commands.Cog):
    def __init__(self, bot: SnakeBot):
        self.bot = bot

    @staticmethod
    def format_embed(message: discord.Message, *, reply: bool = False) -> discord.Embed:
        author = message.author

        embed = (
            discord.Embed(
                color=reply and discord.Color.default() or author.color,
                timestamp=message.created_at,
                description=message.content,
            )
            .set_author(
                name=f"{reply and 'Replying to ' or ''}{author.display_name}",
                url=message.jump_url,
                icon_url=author.display_avatar.url,
            )
            .set_footer(text=message.id)
        )

        if message.attachments:
            embed.set_image(url=message.attachments[0].proxy_url)

        elif message.embeds:
            e = message.embeds[0]

            if e.type == "video" or e.type == "gifv":
                if e.provider and e.provider.name == "Tenor":
                    embed.set_image(
                        url=URL(e.thumbnail.url.replace("D/", "d/")).with_suffix(".gif")
                    )
                else:
                    embed.set_image(url=e.thumbnail.url)
                if e.title:
                    _t = ""
                    if e.author and e.provider:
                        _t = f"{e.author.name} - {e.provider.name}"
                    elif e.provider:
                        _t = e.provider.name

                    embed.add_field(name=_t, value=e.title or "")

            elif e.type == "image":
                embed.set_image(url=e.url)

            elif e.type == "rich":
                if e.image:
                    embed.set_image(url=e.image.url)

                if e.author:
                    embed.add_field(
                        name=e.author.name, value=e.description, inline=False
                    )

                for em in e.fields:
                    embed.add_field(name=em.name, value=em.value, inline=em.inline)

        elif message.stickers:
            embed.set_image(url=message.stickers[0].url)

        return embed

    @staticmethod
    def format_star_sign(num_reacts: int) -> str:
        if num_reacts < 8:
            return "\N{WHITE MEDIUM STAR}"

        elif num_reacts < 12:
            return "\N{GLOWING STAR}"

        elif num_reacts < 18:
            return "\N{SPARKLES}"

        return "\N{DIZZY SYMBOL}"

    @staticmethod
    def compare_emoji(a: Emote, b: Emote) -> bool:
        if isinstance(a, str):
            a = discord.PartialEmoji.from_str(a)

        if isinstance(b, str):
            b = discord.PartialEmoji.from_str(b)

        return a == b

    @staticmethod
    def get_icon(i: int) -> str:
        match i:
            case 0:
                return "\N{FIRST PLACE MEDAL}"

            case 1:
                return "\N{SECOND PLACE MEDAL}"

            case 2:
                return "\N{THIRD PLACE MEDAL}"

            case _:
                return "\N{MILITARY MEDAL}\N{VARIATION SELECTOR-16}"

    @staticmethod
    async def aioenumerate(iter):
        idx = 0

        async for x in iter:
            yield idx, x

            idx = idx + 1

    async def resolve_message(
        self, channel_id: int, message_id: int
    ) -> Optional[discord.Message]:
        try:
            channel = await self.bot.fetch_channel(channel_id)
        except:
            return

        if not isinstance(channel, Channel):
            return

        try:
            message = await channel.fetch_message(message_id)
        except:
            return

        return message

    async def add_board_post(self, message: BoardMessage):
        embeds = []
        footer = []

        original = message.message
        board = message.board

        if original.reference and isinstance(
            original.reference.resolved, discord.Message
        ):
            embeds.append(self.format_embed(original.reference.resolved, reply=True))
            footer.append(f"**Referenced Message**: {original.reference.jump_url}")

        embeds.append(self.format_embed(original))
        links = "\n".join(footer)

        post = await board.channel.send(
            f"{self.format_star_sign(message.reacts)} **{message.reacts}** | {original.jump_url}\n\n{links}",
            embeds=embeds,
            allowed_mentions=discord.AllowedMentions.none(),
        )

        await post.add_reaction("\N{WHITE MEDIUM STAR}")

        await self.bot.db.add_board_post(original, post)

    async def edit_board_post(self, post: discord.Message, message: BoardMessage):
        embeds = []
        footer = []

        original = message.message

        if original.reference and isinstance(
            original.reference.resolved, discord.Message
        ):
            embeds.append(self.format_embed(original.reference.resolved, reply=True))
            footer.append(f"**Referenced Message**: {original.reference.jump_url}")

        embeds.append(self.format_embed(original))
        links = "\n".join(footer)

        post = await post.edit(
            content=f"{self.format_star_sign(message.reacts)} **{message.reacts}** | {original.jump_url}\n\n{links}",
            embeds=embeds,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        message = await self.resolve_message(payload.channel_id, payload.message_id)

        if not message or not message.guild:
            return

        board = await self.bot.db.get_board(message.guild, payload.emoji)

        if not board:
            return

        if message.channel == board.channel:
            react = discord.utils.find(
                lambda r: self.compare_emoji(r.emoji, payload.emoji),
                message.reactions,
            )

            if msg := await self.bot.db.get_board_message_by_post(board, message):
                await self.bot.db.update_board_message(msg.message, msg.reacts + 1)
                await self.edit_board_post(message, msg)

        react = discord.utils.find(
            lambda r: self.compare_emoji(r.emoji, payload.emoji)
            and r.count >= board.threshold,
            message.reactions,
        )

        if not react:
            return

        msg = await self.bot.db.add_board_message(board, message, react)
        await self.add_board_post(msg)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        message = await self.resolve_message(payload.channel_id, payload.message_id)

        if not message or not message.guild:
            return

        board = await self.bot.db.get_board(message.guild, payload.emoji)

        if not board:
            return

        if message.channel == board.channel:
            react = discord.utils.find(
                lambda r: self.compare_emoji(r.emoji, payload.emoji),
                message.reactions,
            )

            if msg := await self.bot.db.get_board_message_by_post(board, message):
                await self.bot.db.update_board_message(msg.message, msg.reacts + 1)
                await self.edit_board_post(message, msg)

        react = discord.utils.find(
            lambda r: self.compare_emoji(r.emoji, payload.emoji), message.reactions
        )

        post = await self.bot.db.get_board_post(board, message)
        msg = await self.bot.db.get_board_message(board, message)

        if not msg:
            return

        if react and react.count >= board.threshold:
            await self.bot.db.update_board_message(message, msg.reacts - 1)
            if post:
                await self.edit_board_post(post, msg)

        else:
            await self.bot.db.remove_board_message(message)

            if post:
                await post.delete()

    @commands.Cog.listener()
    async def on_raw_reaction_clear(self, payload: discord.RawReactionClearEvent):
        message = await self.resolve_message(payload.channel_id, payload.message_id)

        if not message or not message.guild:
            return

        await self.bot.db.remove_board_message(message)
        if post := await self.bot.db.find_board_post_by_id(message):
            await post.delete()

    @commands.Cog.listener()
    async def on_raw_reaction_clear_emoji(
        self, payload: discord.RawReactionClearEmojiEvent
    ):
        message = await self.resolve_message(payload.channel_id, payload.message_id)

        if not message or not message.guild:
            return

        board = await self.bot.db.get_board(message.guild, payload.emoji)

        if not board:
            return

        await self.bot.db.remove_board_message(message)

        if post := await self.bot.db.get_board_post(board, message):
            await post.delete()

    @commands.group(name="board")
    @commands.guild_only()
    async def emoteboard(self, ctx: commands.Context):
        ...

    @emoteboard.command(name="leaders")
    async def board_leaderboard(self, ctx: commands.Context, emote: Emote):
        assert ctx.guild

        board = await self.bot.db.get_board(ctx.guild, emote)

        if not board:
            await self.bot.post_reaction(ctx.message, unknown=True)
            return

        def formatter(args):
            idx, (count, user_id) = args
            msg = f"{self.get_icon(idx)} {idx + 1: >3}. <@{user_id}> | {count} {board.emote}"

            if user_id == ctx.author.id:
                return f"**{msg}**"

            return msg

        leaderboard = [
            (idx, d)
            async for idx, d in self.aioenumerate(self.bot.db.get_boardleaders(board))
        ]

        position = discord.utils.find(lambda t: t[1][1] == ctx.author.id, leaderboard)

        podium = map(formatter, leaderboard[:3])

        tail = map(formatter, leaderboard[3:11])

        embed = discord.Embed(
            color=ctx.author.color,
            title=f"{board.emote} Leaderboard",
            description="\n".join([*podium, "", *tail]),
        )

        if position:
            embed.set_footer(text=f"Your Place: #{position[0] + 1}")

        else:
            embed.set_footer(text="You are not ranked")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Board(bot))
