import aiosqlite
from datetime import datetime, timezone
from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, created_at TEXT, last_seen TEXT);
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, role TEXT, content TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS generations(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, kind TEXT, prompt TEXT, input_path TEXT, output_path TEXT, status TEXT, error TEXT, created_at TEXT, finished_at TEXT);
CREATE TABLE IF NOT EXISTS chat_settings(chat_id INTEGER PRIMARY KEY, always_reply INTEGER NOT NULL DEFAULT 0, updated_at TEXT);
CREATE TABLE IF NOT EXISTS user_agents(user_id INTEGER PRIMARY KEY, agent TEXT NOT NULL DEFAULT 'universal', updated_at TEXT);
"""

def now(): return datetime.now(timezone.utc).isoformat()

async def init_db():
    async with aiosqlite.connect(settings.database_path) as db:
        await db.executescript(SCHEMA); await db.commit()

async def upsert_user(user):
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute("INSERT INTO users(id,username,first_name,created_at,last_seen) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name, last_seen=excluded.last_seen", (user.id,user.username,user.first_name,now(),now())); await db.commit()

async def add_message(user_id:int, role:str, content:str):
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute("INSERT INTO messages(user_id,role,content,created_at) VALUES(?,?,?,?)",(user_id,role,content,now())); await db.commit()

async def get_history(user_id:int, limit:int):
    async with aiosqlite.connect(settings.database_path) as db:
        cur=await db.execute("SELECT role,content FROM messages WHERE user_id=? ORDER BY id DESC LIMIT ?",(user_id,limit)); rows=await cur.fetchall()
    return [{"role":r[0],"content":r[1]} for r in reversed(rows)]

async def create_generation(user_id,kind,prompt,input_path=None):
    async with aiosqlite.connect(settings.database_path) as db:
        cur=await db.execute("INSERT INTO generations(user_id,kind,prompt,input_path,status,created_at) VALUES(?,?,?,?,?,?)",(user_id,kind,prompt,input_path,"queued",now())); await db.commit(); return cur.lastrowid

async def finish_generation(gid, output_path=None, error=None):
    status="failed" if error else "done"
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute("UPDATE generations SET status=?,output_path=?,error=?,finished_at=? WHERE id=?",(status,output_path,error,now(),gid)); await db.commit()

async def gallery(user_id, limit=10):
    async with aiosqlite.connect(settings.database_path) as db:
        cur=await db.execute("SELECT output_path,prompt,kind FROM generations WHERE user_id=? AND status='done' AND output_path IS NOT NULL ORDER BY id DESC LIMIT ?",(user_id,limit)); return await cur.fetchall()

async def set_chat_always_reply(chat_id: int, enabled: bool):
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "INSERT INTO chat_settings(chat_id,always_reply,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(chat_id) DO UPDATE SET always_reply=excluded.always_reply, updated_at=excluded.updated_at",
            (chat_id, 1 if enabled else 0, now()),
        )
        await db.commit()

async def is_chat_always_reply(chat_id: int) -> bool:
    async with aiosqlite.connect(settings.database_path) as db:
        cur = await db.execute("SELECT always_reply FROM chat_settings WHERE chat_id=?", (chat_id,))
        row = await cur.fetchone()
    return bool(row and row[0])


async def set_user_agent(user_id: int, agent: str):
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "INSERT INTO user_agents(user_id,agent,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET agent=excluded.agent, updated_at=excluded.updated_at",
            (user_id, agent, now()),
        )
        await db.commit()

async def get_user_agent(user_id: int) -> str:
    async with aiosqlite.connect(settings.database_path) as db:
        cur = await db.execute("SELECT agent FROM user_agents WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
    return row[0] if row else "universal"
