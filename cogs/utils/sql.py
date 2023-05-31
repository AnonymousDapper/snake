# MIT License
#
# Copyright (c) 2016-2023 AnonymousDapper
#

from __future__ import annotations

__all__ = (
    "SQL",
    "Emote",
    "Channel",
    "RawMessage",
    "RawEmoteBoard",
    "EmoteBoard",
    "RawBoardMessage",
    "BoardMessage",
    "RawBoardUser",
    "BoardUser",
    "RawPostMessage",
    "PostMessage",
    "RawAutorole",
    "Autorole",
)

from typing import TYPE_CHECKING, Optional, cast

import aiosqlite
import msgspec
from discord import (Client, Emoji, Guild, Message, PartialEmoji, Role,
                     StageChannel, TextChannel, Thread, User)

if TYPE_CHECKING:
    from pathlib import Path

from .logger import get_logger

log = get_logger()

Emote = Emoji | PartialEmoji | str
Channel = TextChannel | StageChannel | Thread


class ResolveError(Exception):
    def __init__(self, cls, item, *args):
        super().__init__(cls, item, *args)
        self.cls = cls
        self.item = item

    def __str__(self):
        return f"Resolving {self.cls} failed (bad item: {self.item})"


class DBObject(msgspec.Struct):
    _db: SQL


# helper classes to simplify resolving IDs


class RawMessage(msgspec.Struct):
    message_id: int
    channel_id: int
    guild_id: int

    async def resolve(self, client: Client) -> Message:
        if not (guild := client.get_guild(self.guild_id)):
            raise ResolveError("Message.guild", self.guild_id)

        try:
            channel = cast(Channel, await guild.fetch_channel(self.channel_id))

        except Exception as e:
            raise ResolveError("Message.channel", self.channel_id) from e

        try:
            return await channel.fetch_message(self.message_id)

        except Exception as e:
            raise ResolveError("Message", self.message_id)


class RawEmoteBoard(DBObject):
    id: int
    guild_id: int
    channel_id: int
    threshold: int
    name: str
    emote: str

    async def resolve(self, client: Client) -> EmoteBoard:
        if not (guild := client.get_guild(self.guild_id)):
            raise ResolveError("EmoteBoard", self.guild_id)

        try:
            channel = cast(Channel, await guild.fetch_channel(self.channel_id))

        except Exception as e:
            raise ResolveError("EmoteBoard", self.channel_id) from e

        return EmoteBoard(
            self._db,
            self.id,
            guild,
            channel,
            self.threshold,
            self.name,
            PartialEmoji.from_str(self.emote),
        )


class EmoteBoard(DBObject):
    _id: int
    guild: Guild
    channel: Channel
    threshold: int
    name: str
    emote: Emote


class RawBoardMessage(DBObject):
    message_id: int
    channel_id: int
    guild_id: int
    author_id: int
    reacts: int
    emote_fk: int

    async def resolve(self, client: Client) -> BoardMessage:
        if not (guild := client.get_guild(self.guild_id)):
            raise ResolveError("BoardMessage.guild", self.guild_id)

        try:
            channel = cast(Channel, await guild.fetch_channel(self.channel_id))

        except Exception as e:
            raise ResolveError("BoardMessage.channel", self.channel_id) from e

        try:
            message = await channel.fetch_message(self.message_id)

        except Exception as e:
            raise ResolveError("BoardMessage.message", self.message_id)

        if self.author_id != message.author.id:
            log.warn(
                f"Author ID mismatch on resolving message [{message.id}]: ({self.author_id} != {message.author.id})"
            )

        return BoardMessage(
            self._db, message, channel, guild, self.reacts, self.emote_fk
        )

    async def update_reacts(self, react_count: int):
        self.reacts = react_count

        await self._db.update_board_message(self.message_id, self.reacts)

    async def remove(self):
        await self._db.remove_board_message(self.message_id)


class BoardMessage(DBObject):
    message: Message
    channel: Channel
    guild: Guild
    reacts: int
    _emote: int
    _board: Optional[EmoteBoard]

    async def get_board(self, client: Client) -> EmoteBoard:
        if not self._board:
            self._board = await (await self.get_board_raw()).resolve(client)

        return self._board

    async def get_board_raw(self) -> RawEmoteBoard:
        if raw := await self._db.get_board_by_id(self._emote):
            return raw

        raise ResolveError("BoardMessage.board", self._emote)

    async def update_reacts(self, react_count: int):
        self.reacts = react_count

        await self._db.update_board_message(self.message.id, self.reacts)

    async def add_post(self, post: Message):
        await self._db.add_board_post(self.message.id, post.id)

    async def remove(self):
        await self._db.remove_board_message(self.message.id)


class RawBoardUser(DBObject):
    id: int
    total_reacts: int
    message_count: int
    rank: int
    average_reacts: float
    best_react: int
    worst_react: int
    total_users: int
    _board_id: int

    async def resolve(self, client: Client) -> BoardUser:
        if not (user := client.get_user(self.id)):
            raise ResolveError("BoardUser.user", self.id)

        best = None
        worst = None

        if raw_best := await self._db.get_board_message_by_reacts(
            self.id, self.best_react, self._board_id
        ):
            try:
                best = await raw_best.resolve(client)
            except:
                pass

        if raw_worst := await self._db.get_board_message_by_reacts(
            self.id, self.worst_react, self._board_id
        ):
            try:
                worst = await raw_worst.resolve(client)
            except:
                pass

        return BoardUser(
            user,
            self.total_reacts,
            self.message_count,
            self.rank,
            self.average_reacts,
            best,
            self.best_react,
            worst,
            self.worst_react,
            self.total_users,
        )


class BoardUser(msgspec.Struct):
    user: User
    total: int
    messages: int
    rank: int
    average: float
    best: Optional[Message]
    best_count: int
    worst: Optional[Message]
    worst_count: int
    users_count: int


class RawPostMessage(DBObject):
    message_id: int
    post_id: int

    async def resolve(self, client: Client) -> PostMessage:
        if not (raw_message := await self._db.get_board_message(self.message_id)):
            raise ResolveError("PostMessage.original", self.message_id)

        if not (raw_post := await self._db.get_board_post_data(self.post_id)):
            raise ResolveError("PostMessage.post", self.post_id)

        message = await raw_message.resolve(client)
        post = await raw_post.resolve(client)

        return PostMessage(self._db, message, post)


class PostMessage(DBObject):
    original: BoardMessage
    post: Message

    def update_original(self, new: BoardMessage):
        if new.message == self.original.message:
            self.original = new


class RawAutorole(DBObject):
    role_id: int
    guild_id: int
    channel_id: int
    message_id: int
    emote: str

    async def resolve(self, client: Client) -> Autorole:
        try:
            message = await RawMessage(
                self.message_id, self.channel_id, self.guild_id
            ).resolve(client)
            assert message.guild

        except ResolveError as e:
            raise ResolveError("Autorole.message", e.item)

        except Exception as e:
            raise ResolveError("Autorole.message", "unknown")

        if not (role := message.guild.get_role(self.role_id)):
            raise ResolveError("Autorole.role", self.role_id)

        return Autorole(
            self._db, role, message.guild, message, PartialEmoji.from_str(self.emote)
        )


class Autorole(DBObject):
    role: Role
    guild: Guild
    message: Message
    emote: Emote


class SQL:
    def __init__(self, db_file: str | Path):
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

    # => boards

    async def get_board(self, guild_id: int, emote: Emote) -> Optional[RawEmoteBoard]:
        async with self.conn.execute(
            """
            SELECT id, guild_id, channel_id, threshold, name, emote
            FROM boards
            WHERE guild_id = ? AND emote = ?;
            """,
            (guild_id, str(emote)),
        ) as cur:
            if data := await cur.fetchone():
                return RawEmoteBoard(self, *data)

    async def get_board_by_id(self, board_id: int) -> Optional[RawEmoteBoard]:
        async with self.conn.execute(
            """
            SELECT id, guild_id, channel_id, threshold, name, emote
            FROM boards
            WHERE id = ?;
            """,
            (board_id,),
        ) as cur:
            if data := await cur.fetchone():
                return RawEmoteBoard(*data)

    async def list_boards(self, guild_id: int):
        async with self.conn.execute(
            """
            SELECT id, guild_id, channel_id, threshold, name, emote
            FROM boards
            WHERE guild_id = ?;
            """,
            (guild_id,),
        ) as cur:
            async for row in cur:
                yield RawEmoteBoard(self, *row)

    async def add_board(
        self, guild_id: int, channel_id: int, threshold: int, name: str, emote: Emote
    ) -> RawEmoteBoard:
        async with self.conn.execute(
            """
            INSERT INTO boards (guild_id, channel_id, threshold, name, emote)
            VALUES (?, ?, ?, ?, ?)
            RETURNING id, guild_id, channel_id, threshold, name, emote
            """,
            (guild_id, channel_id, threshold, name, str(emote)),
        ) as cur:
            if data := await cur.fetchone():
                return RawEmoteBoard(self, *data)

        log.critical(f"[Add board failed] {guild_id}#{channel_id} {name}")
        raise RuntimeError(f"Adding board for {channel_id} failed")

    # => board messages

    async def get_board_message(self, message_id: int) -> Optional[RawBoardMessage]:
        async with self.conn.execute(
            """
            SELECT message_id, channel_id, guild_id, author_id, reacts, emote
            FROM board_messages
            WHERE message_id = ?;
            """,
            (message_id,),
        ) as cur:
            if data := await cur.fetchone():
                return RawBoardMessage(self, *data)

    async def get_board_message_by_post(
        self, post_message_id: int
    ) -> Optional[RawBoardMessage]:
        async with self.conn.execute(
            """
            SELECT bm.message_id, bm.channel_id, bm.guild_id, bm.author_id, bm.reacts, bm.emote
            FROM board_messages bm
            JOIN posted_board_messages pbm USING(message_id)
            WHERE pbm.board_message_id = ?;
            """,
            (post_message_id,),
        ) as cur:
            if data := await cur.fetchone():
                return RawBoardMessage(self, *data)

    async def get_board_message_by_reacts(
        self, author_id: int, num_reacts: int, board_id: int
    ) -> Optional[RawMessage]:
        async with self.conn.execute(
            """
            SELECT message_id, channel_id, guild_id
            FROM board_messages
            WHERE author_id = ? AND emote = ? AND reacts = ?;
            """,
            (author_id, board_id, num_reacts),
        ) as cur:
            if data := await cur.fetchone():
                return RawMessage(*data)

    async def add_board_message(
        self,
        message_id: int,
        channel_id: int,
        guild_id: int,
        author_id: int,
        reacts: int,
        emote_fk: int,
    ) -> RawBoardMessage:
        async with self.conn.execute(
            """
            INSERT INTO board_messages (message_id, channel_id, guild_id, author_id, reacts, emote)
            VALUES(?, ?, ?, ?, ?, ?)
            RETURNING message_id, channel_id, guild_id, author_id, reacts, emote;
            """,
            (message_id, channel_id, guild_id, author_id, reacts, emote_fk),
        ) as cur:
            if data := await cur.fetchone():
                return RawBoardMessage(self, *data)

        log.critical(f"[Add board message failed] {guild_id}#{channel_id} {message_id}")
        raise RuntimeError(f"Adding board message for {message_id} failed")

    async def update_board_message(
        self, message_id: int, reacts: int
    ) -> RawBoardMessage:
        async with self.conn.execute(
            """
            UPDATE board_messages
            SET reacts = ?
            WHERE message_id = ?
            RETURNING message_id, channel_id, guild_id, author_id, reacts, emote;
            """,
            (message_id, reacts),
        ) as cur:
            if data := await cur.fetchone():
                return RawBoardMessage(self, *data)

        log.critical(f"[Update board message failed] {message_id}")
        raise RuntimeError(f"Updating board message for {message_id} failed")

    async def remove_board_message(self, message_id: int):
        await self.conn.execute(
            """
            DELETE FROM board_messages
            WHERE message_id = ?;
            """,
            (message_id,),
        )
        await self.conn.commit()

    async def get_boardleaders(self, board_id: int):
        async with self.conn.execute(
            """
            SELECT
                author_id,
                SUM(reacts) total,
                COUNT(message_id) times,
                (ROW_NUMBER () OVER (ORDER BY SUM(reacts) DESC)) pos,
                AVG(reacts) spm,
                MAX(reacts) best,
                MIN(reacts) worst,
                (SELECT COUNT(DISTINCT author_id) FROM board_messages WHERE emote = ?) users,
                emote
            FROM board_messages bm WHERE emote = ?
            GROUP BY author_id ORDER BY total DESC;
            """,
            (board_id,),
        ) as cur:
            async for row in cur:
                yield RawBoardUser(self, *row)

    async def get_boarduser_stats(
        self, board_id: int, user_id: int
    ) -> Optional[RawBoardUser]:
        async with self.conn.execute(
            """
            SELECT
                bm.author_id,
                SUM(reacts) total,
                COUNT(message_id) msgs,
                ranking.pos,
                AVG(reacts) spm,
                MAX(reacts) best,
                MIN(reacts) worst,
                (SELECT COUNT(DISTINCT author_id) FROM board_messages WHERE emote = :board_id) users,
                emote
            FROM board_messages bm
            JOIN (
                SELECT
                    author_id,
                    ROW_NUMBER () OVER (ORDER BY SUM(reacts) DESC) pos
                    FROM board_messages
                    WHERE emote = :board_id
                    GROUP BY author_id
                ) ranking
                USING(author_id)
            WHERE emote = :board_id AND author_id = :user_id
            GROUP BY author_id ORDER BY total DESC;
            """,
            dict(board_id=board_id, user_id=user_id),
        ) as cur:
            if data := await cur.fetchone():
                return RawBoardUser(
                    self,
                    *data,
                )

    # => board posts

    async def get_board_post(self, post_id: int) -> Optional[RawPostMessage]:
        async with self.conn.execute(
            """
            SELECT message_id, board_message_id
            FROM posted_board_messages
            WHERE board_message_id = ?;
            """,
            (post_id,),
        ) as cur:
            if data := await cur.fetchone():
                return RawPostMessage(self, *data)

    async def get_board_post_for_message(
        self, message_id: int
    ) -> Optional[RawPostMessage]:
        async with self.conn.execute(
            """
            SELECT message_id, board_message_id
            FROM posted_board_messages
            WHERE message_id = ?;
            """,
            (message_id,),
        ) as cur:
            if data := await cur.fetchone():
                return RawPostMessage(self, *data)

    async def get_board_post_data(self, post_id: int) -> Optional[RawMessage]:
        async with self.conn.execute(
            """
            SELECT pbm.board_message_id, b.channel_id, b.guild_id
            FROM posted_board_messages pbm
            JOIN board_messages bm USING(message_id)
            JOIN boards b ON b.id = bm.emote
            WHERE pbm.board_message_id = ?;
            """,
            (post_id,),
        ) as cur:
            if data := await cur.fetchone():
                return RawMessage(*data)

    async def add_board_post(self, original_id: int, post_id: int) -> RawPostMessage:
        async with self.conn.execute(
            """
            INSERT INTO posted_board_messages (message_id, board_message_id)
            VALUES(?, ?)
            RETURNING message_id, board_message_id;
            """,
            (original_id, post_id),
        ) as cur:
            if data := await cur.fetchone():
                return RawPostMessage(*data)

        log.critical(f"[Add post failed] {message_id} -> {post_id}")
        raise RuntimeError(f"Adding post {post_id} for {message_id} failed")

    # => autoroles

    async def get_autorole(
        self, guild_id: int, message_id: int, emote: Emote
    ) -> Optional[RawAutorole]:
        async with self.conn.execute(
            """
            SELECT role_id, guild_id, channel_id, message_id, emote
            FROM autoroles
            WHERE guild_id = ? AND message_id = ? AND emote = ?;
            """,
            (guild_id, message_id, str(emote)),
        ) as cur:
            if data := await cur.fetchone():
                return RawAutorole(self, *data)

    async def list_autoroles_for_guild(self, guild_id: int):
        async with self.conn.execute(
            """
            SELECT role_id, guild_id, channel_id, message_id, emote
            FROM autoroles
            WHERE guild_id = ?;
            """,
            (guild_id,),
        ) as cur:
            async for row in cur:
                yield RawAutorole(self, *row)

    async def add_autorole(
        self,
        role_id: int,
        guild_id: int,
        channel_id: int,
        message_id: int,
        emote: Emote,
    ) -> RawAutorole:
        async with self.conn.execute(
            """
            INSERT INTO autoroles (role_id, guild_id, channel_id, message_id, emote)
            VALUES(?, ?, ?, ?, ?)
            RETURNING role_id, guild_id, channel_id, message_id, emote;
            """,
            (role_id, guild_id, channel_id, message_id, str(emote)),
        ) as cur:
            if data := await cur.fetchone():
                return RawAutorole(self, *data)

        log.critical(
            f"[Add autorole failed] {guild_id}#{channel_id} {message_id} [{role_id}]"
        )
        raise RuntimeError(f"Adding autorole for {message_id} [{role_id}] failed")
