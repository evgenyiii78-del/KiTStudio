from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import aiosqlite

from app.agents import DEFAULT_AGENT_KEY


class Database:
    def __init__(self, path: str) -> None:
        self.path = str(Path(path))

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[aiosqlite.Connection]:
        db = await aiosqlite.connect(self.path)
        db.row_factory = aiosqlite.Row
        try:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA foreign_keys=ON")
            yield db
        finally:
            await db.close()

    async def init(self) -> None:
        async with self.connection() as db:
            await db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    agent_key TEXT NOT NULL DEFAULT 'universal',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_history_scope
                    ON history(chat_id, user_id, id);

                CREATE TABLE IF NOT EXISTS group_settings (
                    chat_id INTEGER PRIMARY KEY,
                    enabled INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            await db.commit()

    async def ensure_user(self, user_id: int) -> None:
        async with self.connection() as db:
            await db.execute(
                "INSERT OR IGNORE INTO users(user_id, agent_key) VALUES (?, ?)",
                (user_id, DEFAULT_AGENT_KEY),
            )
            await db.commit()

    async def get_agent_key(self, user_id: int) -> str:
        await self.ensure_user(user_id)
        async with self.connection() as db:
            cur = await db.execute("SELECT agent_key FROM users WHERE user_id = ?", (user_id,))
            row = await cur.fetchone()
            return str(row["agent_key"]) if row else DEFAULT_AGENT_KEY

    async def set_agent_key(self, user_id: int, agent_key: str) -> None:
        async with self.connection() as db:
            await db.execute(
                """
                INSERT INTO users(user_id, agent_key) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    agent_key = excluded.agent_key,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, agent_key),
            )
            await db.commit()

    async def add_message(self, chat_id: int, user_id: int, role: str, content: str) -> None:
        async with self.connection() as db:
            await db.execute(
                "INSERT INTO history(chat_id, user_id, role, content) VALUES (?, ?, ?, ?)",
                (chat_id, user_id, role, content),
            )
            await db.commit()

    async def get_history(self, chat_id: int, user_id: int, limit: int) -> list[dict[str, str]]:
        async with self.connection() as db:
            cur = await db.execute(
                """
                SELECT role, content FROM (
                    SELECT id, role, content
                    FROM history
                    WHERE chat_id = ? AND user_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                )
                ORDER BY id ASC
                """,
                (chat_id, user_id, limit),
            )
            rows = await cur.fetchall()
            return [{"role": str(row["role"]), "content": str(row["content"])} for row in rows]

    async def clear_history(self, chat_id: int, user_id: int) -> None:
        async with self.connection() as db:
            await db.execute(
                "DELETE FROM history WHERE chat_id = ? AND user_id = ?",
                (chat_id, user_id),
            )
            await db.commit()

    async def set_group_enabled(self, chat_id: int, enabled: bool) -> None:
        async with self.connection() as db:
            await db.execute(
                """
                INSERT INTO group_settings(chat_id, enabled) VALUES (?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    enabled = excluded.enabled,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (chat_id, int(enabled)),
            )
            await db.commit()

    async def is_group_enabled(self, chat_id: int) -> bool:
        async with self.connection() as db:
            cur = await db.execute(
                "SELECT enabled FROM group_settings WHERE chat_id = ?",
                (chat_id,),
            )
            row = await cur.fetchone()
            return bool(row and row["enabled"])
