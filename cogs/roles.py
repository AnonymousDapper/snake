# MIT License
#
# Copyright (c) 2016-2023 AnonymousDapper
#


from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord
import msgspec
from discord.ext import commands

from cogs.utils.sql import Emote, ReactionRole

from .utils.logger import get_logger

if TYPE_CHECKING:
    from ..snake import SnakeBot

log = get_logger()


class AutoroleAction(msgspec.Struct):
    autorole: ReactionRole
    member: discord.Member
    removed: bool


class Roles(commands.Cog):
    def __init__(self, bot: SnakeBot):
        self.bot = bot

    async def handle_reaction_event(
        self, payload: discord.RawReactionActionEvent
    ) -> Optional[AutoroleAction]:
        if payload.member and payload.member.bot:
            return

        if not (payload.guild_id) or not (
            await self.bot.db.check_autorole_raw(
                payload.guild_id, payload.message_id, payload.emoji
            )
        ):
            return

        if not (
            (
                message := await self.bot.resolve_message(
                    payload.channel_id, payload.message_id
                )
            )
            and message.guild
        ):
            return

        if not (member := await message.guild.fetch_member(payload.user_id)):
            return

        if not (
            raw_role := await self.bot.db.get_autorole(
                message.guild, message, payload.emoji
            )
        ):
            return

        try:
            autorole = await raw_role.resolve(message.guild)

        except Exception as e:
            log.error(f"Resolving autorole failed: {e}")
            return

        if autorole:
            return AutoroleAction(
                autorole, member, payload.event_type == "REACTION_REMOVE"
            )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if action := await self.handle_reaction_event(payload):
            if action.autorole.role not in action.member.roles:
                try:
                    await action.member.add_roles(
                        action.autorole.role, reason="Reaction autorole"
                    )

                except Exception as e:
                    log.warn(
                        f"Failed adding autorole to {action.member.name} [{action.member.id}]: {e}"
                    )

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if action := await self.handle_reaction_event(payload):
            if action.autorole.role in action.member.roles:
                try:
                    await action.member.remove_roles(
                        action.autorole.role, reason="Reaction autorole"
                    )

                except Exception as e:
                    log.warn(
                        f"Failed removing autorole from {action.member.name} [{action.member.id}]: {e}"
                    )

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

        if autorole := await self.bot.db.get_autorole(ctx.guild, message, emote):
            try:
                if role_ := await autorole.resolve(ctx.guild):
                    msg = f"{role_.emote!s} 🡲 {role_.role.mention} {role_.message.jump_url}"
                else:
                    raise Exception()

            except:
                msg = f"{autorole.emote} 🡲 <@&{autorole.role_id}> [{autorole.message_id}] **RESOLVE FAILED**"

            await ctx.send(
                f"\N{WARNING SIGN}\N{VARIATION SELECTOR-16} That autorole connection already exists:\n{msg}"
            )
            return

        try:
            await self.bot.db.add_autorole(ctx.guild, message, role, emote)
            await message.add_reaction(emote)
        except Exception as e:
            log.error(f"Failure creating autorole: {e}")
            await self.bot.post_reaction(ctx.message, failure=True)

        else:
            await self.bot.post_reaction(ctx.message, success=True)

    # TODO: unlink

    # TODO: list


async def setup(bot):
    await bot.add_cog(Roles(bot))
