# MIT License
#
# Copyright (c) 2018 AnonymousDapper
#
# Permission is hereby granted
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import asyncio

from contextlib import contextmanager

from datetime import datetime

import asyncpg

from .logger import get_logger

log = get_logger()

USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id BIGINT NOT NULL,
    name VARCHAR(40),
    bot BOOLEAN,
    discrim VARCHAR(4),

    CONSTRAINT users_pk PRIMARY KEY (id),
    UNIQUE (id)
);
"""

MESSAGES_TABLE = """
CREATE TABLE IF NOT EXISTS chat_logs (
    id BIGINT NOT NULL,
    timestamp TIMESTAMP,
    author_id BIGINT,
    channel_id BIGINT,
    guild_id BIGINT,
    content VARCHAR(2000),

    CONSTRAINT chat_logs_pk PRIMARY KEY (id),
    UNIQUE (id),

    FOREIGN KEY(author_id) REFERENCES users (id)
);
"""

TAGS_TABLE = """
CREATE TABLE IF NOT EXISTS tags (
    name VARCHAR(50) NOT NULL,
    author_id BIGINT,
    content VARCHAR(1950),
    uses INTEGER,
    timestamp TIMESTAMP,
    data JSONB,

    CONSTRAINT tags_pk PRIMARY KEY (name),
    UNIQUE (name),

    FOREIGN KEY(author_id) REFERENCES users (id)
);
"""

PREFIX_TABLE = """
CREATE TABLE IF NOT EXISTS prefixes (
    pk SERIAL NOT NULL,
    id BIGINT NOT NULL,
    personal BOOLEAN,
    prefix VARCHAR(32),

    CONSTRAINT prefixes_pk PRIMARY KEY (pk),
    UNIQUE (pk)
);
"""

PERMISSION_TABLE = """
CREATE TABLE IF NOT EXISTS permissions (
    pk SERIAL NOT NULL,
    guild_id BIGINT,
    channel_id BIGINT,
    role_id BIGINT,
    user_id BIGINT,
    bits INTEGER,

    CONSTRAINT permissions_pk PRIMARY KEY (pk),
    UNIQUE (pk)
);
"""

BLACKLIST_TABLE = """
CREATE TABLE IF NOT EXISTS blacklist (
    pk SERIAL NOT NULL,
    guild_id BIGINT,
    channel_id BIGINT,
    role_id BIGINT,
    user_id BIGINT,
    data VARCHAR(2000),

    CONSTRAINT blacklist_pk PRIMARY KEY (pk),
    UNIQUE (pk)
);
"""

WHITELIST_TABLE = """
CREATE TABLE IF NOT EXISTS whitelist (
    pk SERIAL NOT NULL,
    guild_id BIGINT,
    channel_id BIGINT,
    role_id BIGINT,
    user_id BIGINT,
    data VARCHAR(2000),

    CONSTRAINT whitelist_pk PRIMARY KEY (pk),
    UNIQUE (pk)
);
"""

ERRORS_TABLE = """
CREATE TABLE IF NOT EXISTS logged_errors (
    pk SERIAL NOT NULL,
    level VARCHAR(30),
    module VARCHAR(2000),
    function VARCHAR(2000),
    filename VARCHAR(2000),
    line INTEGER,
    message VARCHAR(2000),
    timestamp TIMESTAMP,

    CONSTRAINT logged_errors_pk PRIMARY KEY (pk),
    UNIQUE (pk)
);
"""

STATS_TABLE = """
CREATE TABLE IF NOT EXISTS command_stats (
    pk SERIAL NOT NULL,
    message_id BIGINT,
    command_name VARCHAR(40),
    user_id BIGINT,
    args VARCHAR(2000),
    errored BOOLEAN,

    CONSTRAINT command_stats_pk PRIMARY KEY (pk),
    UNIQUE (pk),

    FOREIGN KEY(user_id) REFERENCES users (id)
);
"""

class SQL:
    def __init__(self, *args, **kwargs):
        self.loop = asyncio.get_event_loop()

        db_name = kwargs.get("db_name")
        db_username = kwargs.get("db_username")
        db_password = kwargs.get("db_password")

        self.pool = None

        self.loop.create_task(self._generate_pool(f"postgres://{db_username}:{db_password}@localhost:5432/{db_name}?application_name=snake"))
        self.loop.create_task(self._setup_tables())

    async def _generate_pool(self, url, **kwargs):
        self.pool = await asyncpg.create_pool(dsn=url, **kwargs)

    async def _setup_tables(self):
        await asyncio.sleep(1)
        async with self.pool.acquire() as conn:
            for query in (USERS_TABLE, MESSAGES_TABLE, TAGS_TABLE, PREFIX_TABLE, PERMISSION_TABLE,BLACKLIST_TABLE, WHITELIST_TABLE, ERRORS_TABLE, STATS_TABLE):
                await conn.execute(query)

    async def close(self):
        await self.pool.close()

    # Users
    async def create_user(self, user):
        async with self.pool.acquire() as conn:
            return await conn.execute("INSERT INTO users(id, name, bot, discrim) VALUES($1, $2, $3, $4);", user.id, user.name, user.bot, user.discriminator)

    async def update_user(self, user):
        async with self.pool.acquire() as conn:
            return await conn.execute("UPDATE users SET name = $1, discrim = $2 WHERE id = $3;", user.name, user.discriminator, user.id)

    async def check_user(self, conn, user):
        test_user = await conn.fetchrow("SELECT 1 as test FROM users WHERE id = $1;", user.id);

        if test_user is None:
            await self.create_user(user)

    # Messages
    async def create_message(self, message):
        async with self.pool.acquire() as conn:
            await self.check_user(conn, message.author)

            return await conn.execute("INSERT INTO chat_logs(id, timestamp, author_id, channel_id, guild_id, content) VALUES($1, $2, $3, $4, $5, $6);",
                message.id, message.created_at, message.author.id, message.channel.id, message.guild.id, message.content)

    # Tags
    async def create_tag(self, author, timestamp, name, content):
        async with self.pool.acquire() as conn:
            await self.check_user(conn, author)

            return await conn.execute("INSERT INTO tags(name, author_id, content, uses, timestamp, data) VALUES($1, $2, $3, $4, $5, $6);",
                name, author.id, content, 0, timestamp, "{}")


    # Prefixes
    async def create_prefix(self, item_id, personal, prefix):
        async with self.pool.acquire() as conn:
            return await conn.execute("INSERT INTO prefixes(id, personal, prefix) VALUES($1, $2, $3);", item_id, personal, prefix)

    async def edit_prefix(self, item_id, prefix):
        async with self.pool.acquire() as conn:
            return await conn.execute("UPDATE prefixes SET prefix = $1 WHERE id = $2;", prefix, item_id)

    async def delete_prefix(self, item_id):
        async with self.pool.acquire() as conn:
            return await conn.execute("DELETE FROM prefixes WHERE id = $1;", item_id)

    async def get_prefixes(self, item_id, personal):
        async with self.pool.acquire() as conn:
            return await conn.fetch("SELECT prefix FROM prefixes WHERE id = $1 AND personal = $2;", item_id, personal)



    # Errors
    async def create_error_report(self, report):
        async with self.pool.acquire() as conn:
            return await conn.execute("INSERT INTO logged_errors(level, module, function, filename, line, message, timestamp) VALUES($1, $2, $3, $4, $5, $6, $7);",
                report.levelname, report.module, report.funcName, report.filename, report.lineno, report.msg, datetime.fromtimestamp(report.created))

    # Command stats
    async def create_command_report(self, user, message, command):
        async with self.pool.acquire() as conn:
            await self.check_user(user)

            return await conn.execute("INSERT INTO command_stats(message_id, command_name, user_id, args, errored) VALUES($1, $2, $3, $4, $5);",
                message.id, command.qualified_name, user.id, message.clean_context.split(command.invoked_with)[1].strip(), False)

