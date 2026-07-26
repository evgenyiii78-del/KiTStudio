from __future__ import annotations
from pathlib import Path
import aiosqlite
from app.agents import DEFAULT_AGENT

class Database:
    def __init__(self, path: Path): self.path = path
    async def init(self):
        async with aiosqlite.connect(self.path) as db:
            await db.executescript("""
            CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, user_id INTEGER, role TEXT, content TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS preferences(chat_id INTEGER, user_id INTEGER, agent TEXT NOT NULL DEFAULT 'universal', PRIMARY KEY(chat_id,user_id));
            CREATE TABLE IF NOT EXISTS group_settings(chat_id INTEGER PRIMARY KEY, always_on INTEGER NOT NULL DEFAULT 0);
            """)
            await db.commit()
    async def add_message(self, chat_id:int,user_id:int,role:str,content:str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT INTO messages(chat_id,user_id,role,content) VALUES(?,?,?,?)",(chat_id,user_id,role,content)); await db.commit()
    async def history(self, chat_id:int,user_id:int,limit:int):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT role,content FROM messages WHERE chat_id=? AND user_id=? ORDER BY id DESC LIMIT ?",(chat_id,user_id,limit)); rows=await cur.fetchall()
        return [{"role":r,"content":c} for r,c in reversed(rows)]
    async def clear_history(self, chat_id:int,user_id:int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM messages WHERE chat_id=? AND user_id=?",(chat_id,user_id)); await db.commit()
    async def get_agent(self,chat_id:int,user_id:int):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT agent FROM preferences WHERE chat_id=? AND user_id=?",(chat_id,user_id)); row=await cur.fetchone()
        return row[0] if row else DEFAULT_AGENT
    async def set_agent(self,chat_id:int,user_id:int,agent:str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT INTO preferences(chat_id,user_id,agent) VALUES(?,?,?) ON CONFLICT(chat_id,user_id) DO UPDATE SET agent=excluded.agent",(chat_id,user_id,agent)); await db.commit()
    async def group_always_on(self,chat_id:int):
        async with aiosqlite.connect(self.path) as db:
            cur=await db.execute("SELECT always_on FROM group_settings WHERE chat_id=?",(chat_id,)); row=await cur.fetchone()
        return bool(row and row[0])
    async def set_group_always_on(self,chat_id:int,value:bool):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT INTO group_settings(chat_id,always_on) VALUES(?,?) ON CONFLICT(chat_id) DO UPDATE SET always_on=excluded.always_on",(chat_id,int(value))); await db.commit()
