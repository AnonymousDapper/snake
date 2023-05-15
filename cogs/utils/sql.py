# MIT License
#
# Copyright (c) 2016-2023 AnonymousDapper
#

from __future__ import annotations

__all__ = "Board", "BoardMessage", "SQL"

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, cast

import aiosqlite
from discord import Emoji, PartialEmoji, TextChannel

if TYPE_CHECKING:
    from pathlib import Path
    from discord import Guild, Message, Member, User
    from discord.abc import GuildChannel

from .logger import get_logger

log = get_logger()

BoardEmote = Emoji | PartialEmoji | str


@dataclass
class Board:
    _id: int
    guild: Guild
    channel: TextChannel
    emote: BoardEmote


@dataclass
class BoardMessage:
    message: Message
    channel: GuildChannel
    author: Member | User
    board_message: Message
    reacts: int
    board: Board


class SQL:
    def __init__(self, db_file: str | Path):
        self.loop = asyncio.get_event_loop()
        self.db_file = db_file
        self.conn: aiosqlite.Connection
        self._ready = False

    async def _setup(self):
        if not self._ready:
            self.conn = await aiosqlite.connect(self.db_file)
            self._ready = True

    async def close(self):
        if self._ready:
            await self.conn.close()

    async def get_board_channel_id(
        self, guild: int, emote: BoardEmote
    ) -> Optional[tuple[int, int]]:
        async with self.conn.execute(
            "SELECT id,channel_id FROM boards WHERE guild_id = ? AND emote = ?;",
            (guild, emote),
        ) as cur:
            data = await cur.fetchone()

            if data:
                return data[0], data[1]

    async def get_board(self, guild: Guild, emote: BoardEmote) -> Optional[Board]:
        board_details = await self.get_board_channel_id(guild.id, str(emote))

        if board_details and (channel := guild.get_channel(board_details[1])):
            return Board(board_details[0], guild, cast(TextChannel, channel), emote)

    async def add_board(self, board: Board):
        await self.conn.execute(
            "INSERT INTO boards (guild_id, channel_id, emote) VALUES (?, ?, '?');",
            (board.guild.id, board.channel.id, str(board.emote)),
        )
        await self.conn.commit()
