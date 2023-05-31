# MIT License
#
# Copyright (c) 2016-2023 AnonymousDapper
#


from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands
from yarl import URL

from cogs.utils.sql import (BoardMessage, Channel, Emote, EmoteBoard,
                            PostMessage, RawBoardUser, RawMessage)

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
    def get_line_header(i: int) -> str:
        if i <= 3:
            match i:
                case 1:
                    return "\N{FIRST PLACE MEDAL}"

                case 2:
                    return "\N{SECOND PLACE MEDAL}"

                case 3:
                    return "\N{THIRD PLACE MEDAL}"

        return f"\N{BLACK SMALL SQUARE} {i + 1: >3}."

    @staticmethod
    async def aioenumerate(iter):
        idx = 0

        async for x in iter:
            yield idx, x

            idx = idx + 1

    async def add_board_post(self, message: BoardMessage):
        embeds = []
        footer = []

        original = message.message
        board = await message.get_board(self.bot)

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

        await message.add_post(post)

    async def edit_board_post(self, post: PostMessage):
        embeds = []
        footer = []

        message = post.original
        original = message.message
        board = await message.get_board(self.bot)

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

        await post.post.edit(
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
            total_reacts |= {
                m.id async for m in react.users() if not m.bot and m != original.author
            }

            if post and (
                post_react := discord.utils.find(
                    lambda r: self.compare_emoji(r.emoji, board.emote), post.reactions
                )
            ):
                total_reacts |= {
                    m.id
                    async for m in post_react.users()
                    if not m.bot and m != original.author
                }

        return len(total_reacts)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        post: Optional[PostMessage] = None
        message: Optional[BoardMessage] = None
        board: Optional[EmoteBoard] = None
        react_count: int

        if (not payload.guild_id) or payload.member and payload.member.bot:
            return

        if not (
            raw_board := await self.bot.db.get_board(payload.guild_id, payload.emoji)
        ):
            return

        if payload.channel_id == raw_board.channel_id:  # star by proxy
            if raw_post := await self.bot.db.get_board_post(payload.message_id):
                post = await raw_post.resolve(self.bot)
                message = post.original
                board = await message.get_board(self.bot)
            else:
                self.bot.log.error(
                    f"BoardMessage not found for message: {payload.message_id}"
                )
                return

        else:  # direct star
            if raw_message := await self.bot.db.get_board_message(payload.message_id):
                if raw_post := await self.bot.db.get_board_post_for_message(
                    payload.message_id
                ):
                    post = await raw_post.resolve(self.bot)
                    message = post.original
                    board = await message.get_board(self.bot)
                else:
                    # not re-setting post
                    message = await raw_message.resolve(self.bot)
                    board = await message.get_board(self.bot)

        if not board:
            board = await raw_board.resolve(self.bot)

        if message:
            react_count = await self.calculate_reacts(
                board, message.message, post and post.post
            )

            await message.update_reacts(react_count)

            if post:
                post.update_original(message)
                await self.edit_board_post(post)

        else:
            msg = await RawMessage(
                payload.message_id, payload.channel_id, payload.guild_id
            ).resolve(self.bot)
            react_count = await self.calculate_reacts(board, msg, None)

            if react_count >= board.threshold:
                raw_msg = await self.bot.db.add_board_message(
                    msg.id,
                    msg.channel.id,
                    msg.guild.id,
                    msg.author.id,
                    react_count,
                    board._id,
                )
                message = await raw_msg.resolve(self.bot)
                await self.add_board_post(message)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        post: Optional[PostMessage] = None
        message: Optional[BoardMessage] = None
        board: EmoteBoard

        if (not payload.guild_id) or payload.member and payload.member.bot:
            return

        if not (
            raw_board := await self.bot.db.get_board(payload.guild_id, payload.emoji)
        ):
            return

        if payload.channel_id == raw_board.channel_id:  # star by proxy
            if raw_post := await self.bot.db.get_board_post(payload.message_id):
                post = await raw_post.resolve(self.bot)
                message = post.original
                board = await message.get_board(self.bot)
            else:
                self.bot.log.error(
                    f"BoardMessage not found for message: {payload.message_id}"
                )
                return

        else:  # direct star
            if raw_message := await self.bot.db.get_board_message(payload.message_id):
                if raw_post := await self.bot.db.get_board_post_for_message(
                    payload.message_id
                ):
                    post = await raw_post.resolve(self.bot)
                    message = post.original
                    board = await message.get_board(self.bot)
                else:
                    # not re-setting post
                    message = await raw_message.resolve(self.bot)
                    board = await message.get_board(self.bot)

            else:
                return

        if message:
            react_count = await self.calculate_reacts(
                board, message.message, post and post.post
            )

            if react_count >= board.threshold:
                await message.update_reacts(react_count)

                if post:
                    post.update_original(message)
                    await self.edit_board_post(post)
            else:
                await message.remove()
                if post:
                    await post.post.delete()

    @commands.Cog.listener()
    async def on_raw_reaction_clear(self, payload: discord.RawReactionClearEvent):
        if not payload.guild_id:
            return

        if raw_msg := await self.bot.db.get_board_post_for_message(payload.message_id):
            await self.bot.db.remove_board_message(payload.message_id)

            if raw_post := await self.bot.db.get_board_post_data(raw_msg.post_id):
                await (await raw_post.resolve(self.bot)).delete()

    @commands.Cog.listener()
    async def on_raw_reaction_clear_emoji(
        self, payload: discord.RawReactionClearEmojiEvent
    ):
        if not payload.guild_id:
            return

        if not (
            raw_board := await self.bot.db.get_board(payload.guild_id, payload.emoji)
        ):
            return

        if raw_msg := await self.bot.db.get_board_post_for_message(payload.message_id):
            await self.bot.db.remove_board_message(payload.message_id)

            if raw_post := await self.bot.db.get_board_post_data(raw_msg.post_id):
                await (await raw_post.resolve(self.bot)).delete()

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        if not payload.guild_id:
            return

        if raw_msg := await self.bot.db.get_board_post_for_message(payload.message_id):
            await self.bot.db.remove_board_message(payload.message_id)

            if raw_post := await self.bot.db.get_board_post_data(raw_msg.post_id):
                await (await raw_post.resolve(self.bot)).delete()

    @commands.group(name="board")
    @commands.guild_only()
    async def emoteboard(self, ctx: commands.Context):
        ...

    @emoteboard.command(name="list", brief="list emote boards in current server")
    @commands.is_owner()
    async def list_boards(self, ctx: commands.Context):
        msg = [
            f"{b.emote!s} ➜ <@#{b.channel_id}> **[{b.name}]** (min. {b.threshold})"
            async for b in self.bot.db.list_boards(ctx.guild.id)
        ]

        await ctx.send("\n".join(msg))

    @emoteboard.command(name="add", brief="add a new emote board")
    @commands.is_owner()
    async def add_board(
        self,
        ctx: commands.Context,
        emote: Emote,
        channel: Channel,
        name: str,
        threshold: int = 4,
    ):
        if await self.bot.db.get_board(ctx.guild.id, emote):
            await self.bot.post_reaction(ctx.message)
            await ctx.send(f"{channel.mention} is already registered with {emote!s}")
            return

        try:
            await self.bot.db.add_board(
                ctx.guild.id, channel.id, threshold, name, emote
            )

        except Exception as e:
            log.error(
                f"Failed creating emoteboard {name} for {ctx.guild.name} #{channel.name}: {e}"
            )
            await self.bot.post_reaction(ctx.message, failure=True)

        else:
            await self.bot.post_reaction(ctx.message, success=True)
            await ctx.send(
                f"Setup {channel.mention} to track {emote!s} (minimum {threshold}"
            )

    @emoteboard.command(name="leaders", brief="show leaderboard")
    async def board_leaderboard(self, ctx: commands.Context, emote: Emote):
        assert ctx.guild

        if not (raw_board := await self.bot.db.get_board(ctx.guild.id, emote)):
            await self.bot.post_reaction(ctx.message, unknown=True)
            return

        def formatter(user: RawBoardUser):
            msg = (
                f"{self.get_line_header(user.rank)} <@{user.id}> | {user.total_reacts}"
            )

            if user.id == ctx.author.id:
                return f"**{msg}**"

            return msg

        leaderboard = [
            user async for user in self.bot.db.get_boardleaders(raw_board.id)
        ]

        user = discord.utils.find(lambda u: u.id == ctx.author.id, leaderboard)

        podium = map(formatter, leaderboard[:3])
        tail = map(formatter, leaderboard[3:11])

        embed = discord.Embed(
            color=ctx.author.color,
            title=f"{raw_board.emote!s} Leaderboard",
            description="\n".join([*podium, "", *tail]),
        )

        if user:
            embed.set_footer(
                text=f"Your Place: #{user.rank} ({user.total_reacts}/{user.message_count})"
            )
        else:
            embed.set_footer(text="You are not ranked")

        await ctx.send(embed=embed)

    @emoteboard.command(name="stats", brief="show individual stats")
    async def board_userstats(
        self,
        ctx: commands.Context,
        emote: Emote,
        user: Optional[discord.Member | discord.User] = None,
    ):
        assert ctx.guild
        user = user or ctx.author

        if not (raw_board := await self.bot.db.get_board(ctx.guild.id, emote)):
            await self.bot.post_reaction(ctx.message, unknown=True)
            return

        if not (
            raw_user := await self.bot.db.get_boarduser_stats(raw_board.id, user.id)
        ):
            await ctx.send(
                f"Sorry, {user.display_name}, you aren't ranked on the {emote!s} board yet."
            )
            return

        board_user = await raw_user.resolve(self.bot)

        embed = discord.Embed(
            color=user.color,
            title=f"{user.display_name}'s stats",
            description=f"**{board_user.total}** total {emote!s} reacts \N{EM DASH} Rank **{board_user.rank}** of {board_user.users_count}",
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(
            name="Messages Awarded", value=str(board_user.messages), inline=True
        )
        embed.add_field(
            name="Average reacts per message",
            value=f"{board_user.average:.1f}",
            inline=True,
        )

        best_msg = f"**{board_user.best_count}**"
        if board_user.best:
            best_msg += f" | {board_user.best.jump_url}"

        embed.add_field(name="Best Message", value=best_msg, inline=False)

        worst_msg = f"**{board_user.worst_count}**"
        if board_user.worst:
            worst_msg += f" | {board_user.worst.jump_url}"

        embed.add_field(name="Worst Message", value=worst_msg, inline=False)

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Board(bot))
