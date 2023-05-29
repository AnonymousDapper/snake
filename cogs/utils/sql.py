# MIT License
#
# Copyright (c) 2016-2023 AnonymousDapper
#

from __future__ import annotations

__all__ = (
    "EmoteBoard",
    "SQL",
    "Emote",
    "BoardMessage",
    "ReactionRole",
    "RawReactionRole",
)

import asyncio
from typing import TYPE_CHECKING, Optional, cast

import aiosqlite
import msgspec
from discord import (Emoji, Guild, Message, PartialEmoji, Role, StageChannel,
                     TextChannel, Thread)

if TYPE_CHECKING:
    from pathlib import Path

from .logger import get_logger

log = get_logger()

Emote = Emoji | PartialEmoji | str
Channel = TextChannel | StageChannel | Thread


class EmoteBoard(msgspec.Struct):
    id: int
    guild: Guild
    channel: Channel
    threshold: int
    name: str
    emote: Emote


class BoardMessage(msgspec.Struct):
    board: EmoteBoard
    message: Message
    reacts: int


class ReactionRole(msgspec.Struct):
    role: Role
    guild: Guild
    message: Message
    emote: Emote


class RawReactionRole(msgspec.Struct):
    role_id: int
    guild_id: int
    channel_id: int
    message_id: int
    emote: str

    async def resolve(self, guild: Guild) -> Optional[ReactionRole]:
        if guild.id != self.guild_id:
            raise ValueError("Guild ID does not match")

        if not (channel := guild.get_channel(self.channel_id)):
            raise ValueError(
                f"Channel [{self.guild_id}/{self.channel_id}] could not be found"
            )

        if not (role := guild.get_role(self.role_id)):
            raise ValueError(
                f"Role [{self.guild_id}@{self.role_id}] could not be found"
            )

        try:
            message = await channel.fetch_message(self.message_id)
        except Exception as e:
            raise ValueError(
                f"Message [{self.guild_id}/{self.channel_id}/{self.message_id}] could not be found: {e!s}"
            )

        return ReactionRole(role, guild, message, PartialEmoji.from_str(self.emote))


class SQL:
    def __init__(self, db_file: str | Path):
        self.loop = asyncio.get_event_loop()
        self.db_file = db_file
        self.conn: aiosqlite.Connection
        self._ready = False

    async def _setup(self):
        if not self._ready:
            self.conn = await aiosqlite.connect(self.db_file)
            self.conn.row_factory = aiosqlite.Row
            await self.conn.execute("PRAGMA foreign_keys = ON;")
            self._ready = True

    async def close(self):
        if self._ready:
            await self.conn.close()

    # --> boards
    async def get_board(self, guild: Guild, emote: Emote) -> Optional[EmoteBoard]:
        async with self.conn.execute(
            "SELECT id, channel_id, threshold, name FROM boards WHERE guild_id = ? AND emote = ?;",
            (guild.id, str(emote)),
        ) as cur:
            data = await cur.fetchone()

            if data and (channel := guild.get_channel(data[1])):
                return EmoteBoard(
                    data[0], guild, cast(Channel, channel), data[2], data[3], emote
                )

    async def list_boards(self, guild: Guild):
        async with self.conn.execute(
            "SELECT id, channel_id, threshold, name, emote FROM boards WHERE guild_id = ?;",
            (guild.id,),
        ) as cur:
            async for row in cur:
                if channel := guild.get_channel(row[1]):
                    yield EmoteBoard(
                        row[0], guild, cast(Channel, channel), row[2], row[3], row[4]
                    )

    async def find_board(
        self, guild: Guild, query: Emote | str
    ) -> Optional[EmoteBoard]:
        async with self.conn.execute(
            "SELECT id, channel_id, threshold, name, emote FROM boards WHERE guild_id = ? AND (name = ? OR emote = ?);",
            (guild.id, str(query), str(query)),
        ) as cur:
            data = await cur.fetchone()

            if data and (channel := guild.get_channel(data[1])):
                return EmoteBoard(
                    data[0],
                    guild,
                    cast(Channel, channel),
                    data[2],
                    data[3],
                    data[4],
                )

    async def add_board(
        self, channel: Channel, threshold: int, name: str, emote: Emote
    ) -> Optional[EmoteBoard]:
        await self.conn.execute(
            "INSERT INTO boards (guild_id, channel_id, threshold, name, emote) VALUES(?, ?, ?, ?, ?);",
            (channel.guild.id, channel.id, threshold, name, str(emote)),
        )
        await self.conn.commit()

        return await self.get_board(channel.guild, emote)

    async def check_board_raw(self, guild_id: int, emote: Emote) -> bool:
        async with self.conn.execute(
            "SELECT true FROM boards WHERE guild_id = ? and emote = ?;",
            (guild_id, str(emote)),
        ) as cur:
            if data := await cur.fetchone():
                return True

        return False

    # --> board_messages
    async def get_board_message(
        self, board: EmoteBoard, message: Message
    ) -> Optional[BoardMessage]:
        async with self.conn.execute(
            "SELECT reacts, emote FROM board_messages WHERE message_id = ?",
            (message.id,),
        ) as cur:
            data = await cur.fetchone()

            if data:
                return BoardMessage(board, message, data[0])

    async def get_board_message_by_post(
        self, board: EmoteBoard, post: Message
    ) -> Optional[BoardMessage]:
        async with self.conn.execute(
            """
            SELECT pbm.message_id, bm.channel_id, bm.reacts FROM posted_board_messages pbm
            JOIN board_messages bm USING(message_id)
            WHERE pbm.board_message_id = ?;
            """,
            (post.id,),
        ) as cur:
            data = await cur.fetchone()

            if data and (channel := cast(Channel, board.guild.get_channel(data[1]))):
                try:
                    message = await channel.fetch_message(data[0])
                except:
                    return

                if message:
                    return BoardMessage(board, message, data[2])

    async def add_board_message(
        self, board: EmoteBoard, message: Message, reacts: int
    ) -> BoardMessage:
        await self.conn.execute(
            "INSERT INTO board_messages (message_id, channel_id, guild_id, author_id, reacts, emote) VALUES (?, ?, ?, ?, ?, ?);",
            (
                message.id,
                message.channel.id,
                board.guild.id,
                message.author.id,
                reacts,
                board.id,
            ),
        )

        await self.conn.commit()

        return BoardMessage(board, message, reacts)

    async def update_board_message(self, message: Message, reacts: int):
        await self.conn.execute(
            "UPDATE board_messages SET reacts = ? WHERE message_id = ?;",
            (reacts, message.id),
        )

        await self.conn.commit()

    # as long as our FK constraints hold, this should cascade and delete from posted_board_messages as well
    async def remove_board_message(self, message: Message | int):
        await self.conn.execute(
            "DELETE FROM board_messages WHERE message_id = ?",
            (isinstance(message, Message) and message.id or message,),
        )

        await self.conn.commit()

    async def get_boardleaders(self, board: EmoteBoard):
        async with self.conn.execute(
            """
            SELECT SUM(reacts) as total, author_id
            FROM board_messages
            WHERE emote = ?
            GROUP BY author_id ORDER BY total DESC;
            """,
            (board.id,),
        ) as cur:
            async for row in cur:
                yield row

    # --> posted_board_messages
    async def add_board_post(self, original: Message, post: Message):
        await self.conn.execute(
            "INSERT INTO posted_board_messages (message_id, board_message_id) VALUES(?, ?);",
            (original.id, post.id),
        )

        await self.conn.commit()

    async def get_board_post(
        self, board: EmoteBoard, message: Message
    ) -> Optional[Message]:
        async with self.conn.execute(
            "SELECT board_message_id FROM posted_board_messages WHERE message_id = ?;",
            (message.id,),
        ) as cur:
            data = await cur.fetchone()

            if data:
                try:
                    return await board.channel.fetch_message(data[0])
                except:
                    pass

    async def find_board_post_by_id(self, original: Message) -> Optional[Message]:
        async with self.conn.execute(
            """
            SELECT b.channel_id, pbm.board_message_id
            FROM board_messages bm
            JOIN boards b ON bm.emote = b.id
            JOIN posted_board_messages pbm ON pbm.message_id = bm.message_id
            WHERE bm.message_id = ?;
            """,
            (original.id,),
        ) as cur:
            data = await cur.fetchone()

            if data and (channel := original.guild.get_channel(data[0])):
                try:
                    return await channel.fetch_message(data[1])
                except:
                    pass

    async def find_board_post_by_id_raw(
        self, original_id: int
    ) -> Optional[tuple[int, int]]:
        async with self.conn.execute(
            """
            SELECT b.channel_id, pbm.board_message_id
            FROM board_messages bm
            JOIN boards b ON bm.emote = b.id
            JOIN posted_board_messages pbm ON pbm.message_id = bm.message_id
            WHERE bm.message_id = ?;
            """,
            (original_id,),
        ) as cur:
            data = await cur.fetchone()

            if data:
                return data[0], data[1]

    # --> reaction roles
    async def get_autorole(
        self, guild: Guild, message: Message, emote: Emote
    ) -> Optional[RawReactionRole]:
        async with self.conn.execute(
            "SELECT role_id, guild_id, channel_id, message_id, emote FROM autoroles WHERE guild_id = ? AND message_id = ? AND emote = ?;",
            (guild.id, message.id, str(emote)),
        ) as cur:
            data = await cur.fetchone()

            if data:
                return RawReactionRole(*data)

    # this probably should not attempt to resolve in this method
    async def list_autoroles(self, guild: Guild):
        async with self.conn.execute(
            "SELECT role_id, guild_id, channel_id, message_id, emote FROM autoroles WHERE guild_id = ?;",
            (guild.id,),
        ) as cur:
            async for row in cur:
                yield RawReactionRole(*row)

    async def add_autorole(
        self, guild: Guild, message: Message, role: Role, react: Emote
    ):
        await self.conn.execute(
            "INSERT INTO autoroles (role_id, guild_id, channel_id, message_id, emote) VALUES (?, ?, ?, ?, ?);",
            (role.id, guild.id, message.channel.id, message.id, str(react)),
        )

        await self.conn.commit()

    async def check_autorole_raw(
        self, guild_id: int, message_id: int, emote: Emote
    ) -> bool:
        async with self.conn.execute(
            "SELECT true FROM autoroles WHERE guild_id = ? AND message_id = ? AND emote = ?;",
            (guild_id, message_id, str(emote)),
        ) as cur:
            if data := await cur.fetchone():
                return True

        return False
