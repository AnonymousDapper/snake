# MIT License
#
# Copyright (c) 2016-2023 AnonymousDapper
#


from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from cogs.utils.sql import Emote, ResolveError

from .utils.logger import get_logger

if TYPE_CHECKING:
    from ..snake import SnakeBot

log = get_logger()


class Roles(commands.Cog):
    def __init__(self, bot: SnakeBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if (not payload.guild_id) or payload.member and payload.member.bot:
            return

        if not (guild := self.bot.get_guild(payload.guild_id)):
            return

        if not (
            raw_role := await self.bot.db.get_autorole(
                payload.guild_id, payload.message_id, payload.emoji
            )
        ):
            return

        if not (member := await guild.fetch_member(payload.user_id)):
            return

        role = await raw_role.resolve(self.bot)

        if role.role not in member.roles:
            try:
                await member.add_roles(role.role, reason="Reaction autorole")
            except:
                pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if (not payload.guild_id) or payload.member and payload.member.bot:
            return

        if not (guild := self.bot.get_guild(payload.guild_id)):
            return

        if not (
            raw_role := await self.bot.db.get_autorole(
                payload.guild_id, payload.message_id, payload.emoji
            )
        ):
            return

        if not (member := await guild.fetch_member(payload.user_id)):
            return

        role = await raw_role.resolve(self.bot)

        if role.role in member.roles:
            try:
                await member.remove_roles(role.role, reason="Reaction autorole")
            except:
                pass

    @commands.group(name="role")
    @commands.guild_only()
    async def reactroles(self, ctx: commands.Context):
        ...

    @reactroles.command(
        name="link", brief="Register an autorole with its reaction", aliases=["+"]
    )
    @commands.is_owner()
    async def new_autorole(
        self,
        ctx: commands.Context,
        message: discord.Message,
        role: discord.Role,
        emote: Emote,
    ):
        assert ctx.guild

        if raw_role := await self.bot.db.get_autorole(ctx.guild.id, message.id, emote):
            try:
                autorole = await raw_role.resolve(self.bot)
                msg = f"{autorole.emote!s} ➜ {autorole.role.mention} {autorole.message.jump_url}"
            except Exception as e:
                msg = f"{raw_role.emote!s} ➜ <@&{raw_role.role_id}> [{raw_role.message_id}] **(resolve failed)**"
                if isinstance(e, ResolveError):
                    msg += f"\n*resolving {e.cls}, got a bad item: {e.item}"

            await ctx.send(
                f"\N{WARNING SIGN}\N{VARIATION SELECTOR-16} That autorole connection already exists:\n{msg}"
            )
            return

        try:
            autorole = await self.bot.db.add_autorole(
                role.id, ctx.guild.id, message.channel.id, message.id, emote
            )
            await message.add_reaction(emote)

        except Exception as e:
            log.error(f"Failure creating autorole link: {e}")
            await self.bot.post_reaction(ctx.message, failure=True)

        else:
            await self.bot.post_reaction(ctx.message, success=True)
            await ctx.send(
                f"Setup {emote!s} reaction for {role.mention} on {message.jump_url}",
                allowed_mentions=discord.AllowedMentions.none(),
            )


async def setup(bot):
    await bot.add_cog(Roles(bot))
