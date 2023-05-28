# MIT License
#
# Copyright (c) 2016-2023 AnonymousDapper
#


from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord
import msgspec
from discord.ext import commands
from yarl import URL

from cogs.utils.sql import BoardMessage, Channel, Emote, EmoteBoard

from .utils.logger import get_logger

if TYPE_CHECKING:
    from ..snake import SnakeBot

log = get_logger()


class ReactionEvent(msgspec.Struct):
    board: EmoteBoard
    board_message: BoardMessage | None
    original_msg: discord.Message
    post_msg: discord.Message | None
    reacts: int


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
    def get_line_header(i: int) -> str:
        if i <= 2:
            match i:
                case 0:
                    return "\N{FIRST PLACE MEDAL}"

                case 1:
                    return "\N{SECOND PLACE MEDAL}"

                case 2:
                    return "\N{THIRD PLACE MEDAL}"

        return f"\N{BLACK SMALL SQUARE} {i + 1: >3}."

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

        if self.compare_emoji(board.emote, "\N{WHITE MEDIUM STAR}"):
            header = self.format_star_sign(message.reacts)
        else:
            header = str(board.emote)

        post = await board.channel.send(
            f"{header} **{message.reacts}** | {original.jump_url}\n\n{links}",
            embeds=embeds,
            allowed_mentions=discord.AllowedMentions.none(),
        )

        await post.add_reaction(board.emote)

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

        if self.compare_emoji(message.board.emote, "\N{WHITE MEDIUM STAR}"):
            header = self.format_star_sign(message.reacts)
        else:
            header = str(message.board.emote)

        post = await post.edit(
            content=f"{header} **{message.reacts}** | {original.jump_url}\n\n{links}",
            embeds=embeds,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    async def calculate_reacts(
        self,
        board: EmoteBoard,
        original: discord.Message,
        post: Optional[discord.Message],
    ) -> int:
        total_reacts = set()

        if react := discord.utils.find(
            lambda r: self.compare_emoji(r.emoji, board.emote), original.reactions
        ):
            total_reacts |= {m.id async for m in react.users() if not m.bot}

            if post and (
                post_react := discord.utils.find(
                    lambda r: self.compare_emoji(r.emoji, board.emote), post.reactions
                )
            ):
                total_reacts |= {m.id async for m in post_react.users() if not m.bot}

        return len(total_reacts)

    async def handle_reaction_event(
        self, payload: discord.RawReactionActionEvent
    ) -> Optional[ReactionEvent]:
        original_msg = None
        post_msg = None

        if payload.member and payload.member.bot:
            return

        if not (
            (msg := await self.resolve_message(payload.channel_id, payload.message_id))
            and msg.guild
        ):
            return

        if not (board := await self.bot.db.get_board(msg.guild, payload.emoji)):
            return

        if msg.channel == board.channel:  # star by proxy
            if board_message := await self.bot.db.get_board_message_by_post(board, msg):
                original_msg = board_message.message
                post_msg = msg

        else:  # direct star
            if board_message := await self.bot.db.get_board_message(board, msg):
                original_msg = board_message.message
                post_msg = await self.bot.db.get_board_post(board, original_msg)
            else:  # new star
                original_msg = msg

        if original_msg:  # can't imagine why this would be None
            react_count = await self.calculate_reacts(board, original_msg, post_msg)

            if board_message:
                board_message.reacts = react_count

            return ReactionEvent(
                board, board_message, original_msg, post_msg, react_count
            )

        else:
            self.bot.log.error(f"`original` is None ({payload!r})")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if data := await self.handle_reaction_event(payload):
            board = data.board
            board_message = data.board_message
            original_msg = data.original_msg
            post_msg = data.post_msg
            react_count = data.reacts

            if board_message:
                await self.bot.db.update_board_message(original_msg, react_count)
                if post_msg:
                    await self.edit_board_post(post_msg, board_message)

            elif react_count >= board.threshold:
                board_message = await self.bot.db.add_board_message(
                    board, original_msg, react_count
                )
                await self.add_board_post(board_message)

            else:
                log.debug(
                    f"Ignoring board reaction under threshold: {board.emote} ({react_count}/{board.threshold})"
                )

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if data := await self.handle_reaction_event(payload):
            board = data.board
            board_message = data.board_message
            original_msg = data.original_msg
            post_msg = data.post_msg
            react_count = data.reacts

            if react_count >= board.threshold:
                if board_message:
                    await self.bot.db.update_board_message(original_msg, react_count)

                    if post_msg:
                        await self.edit_board_post(post_msg, board_message)
                else:
                    log.error(
                        f"React count above threshold, but no BoardMessage exists: {original_msg!r}"
                    )

            else:
                await self.bot.db.remove_board_message(original_msg)

                if post_msg:
                    await post_msg.delete()

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

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        if not payload.guild_id:
            return

        if post_details := await self.bot.db.find_board_post_by_id_raw(
            payload.message_id
        ):
            if post := await self.resolve_message(post_details[0], post_details[1]):
                await post.delete()

            await self.bot.db.remove_board_message(payload.message_id)

    @commands.group(name="board")
    @commands.guild_only()
    async def emoteboard(self, ctx: commands.Context):
        ...

    @emoteboard.command(name="list")
    @commands.is_owner()
    async def list_boards(self, ctx: commands.Context):
        msg = [
            f"{b.emote!s} 🡲 {b.channel.mention} **[{b.name}]** (min {b.threshold})"
            async for b in self.bot.db.list_boards(ctx.guild)
        ]

        await ctx.send("\n".join(msg))

    @emoteboard.command(name="add")
    @commands.is_owner()
    async def add_board(
        self,
        ctx: commands.Context,
        emote: Emote,
        channel: Channel,
        name: str,
        threshold: int = 4,
    ):
        if board := await self.bot.db.get_board(ctx.guild, emote):
            await self.bot.post_reaction(ctx.message)
            await ctx.send(
                f"{board.channel.mention} is already registered with {board.emote!s}"
            )
            return

        if board := await self.bot.db.add_board(channel, threshold, name, emote):
            await self.bot.post_reaction(ctx.message, success=True)

        else:
            await self.bot.post_reaction(ctx.message, failure=True)

    @emoteboard.command(name="leaders")
    async def board_leaderboard(self, ctx: commands.Context, emote: Emote):
        assert ctx.guild

        board = await self.bot.db.get_board(ctx.guild, emote)

        if not board:
            await self.bot.post_reaction(ctx.message, unknown=True)
            return

        def formatter(args):
            idx, (count, user_id) = args
            msg = f"{self.get_line_header(idx)} <@{user_id}> | {count}"

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
