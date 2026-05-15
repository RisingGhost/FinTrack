from typing import Any

import asyncpg
from asyncpg import Pool


class Database:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: Pool | None = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(
            dsn=self._dsn,
            min_size=1,
            max_size=5,
        )

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def fetchval(self, query: str, *args: Any) -> Any:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")
        return await self._pool.fetchval(query, *args)

    async def fetchrow(self, query: str, *args: Any) -> asyncpg.Record | None:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")
        return await self._pool.fetchrow(query, *args)

    async def fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")
        return await self._pool.fetch(query, *args)

    async def execute(self, query: str, *args: Any) -> str:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")
        return await self._pool.execute(query, *args)
