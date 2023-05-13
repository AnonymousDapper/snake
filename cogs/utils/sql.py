# MIT License
#
# Copyright (c) 2016-2023 AnonymousDapper
#

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import aiosqlite

if TYPE_CHECKING:
    from pathlib import Path

from .logger import get_logger

log = get_logger()


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
