import asyncio
import os
import tempfile

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:TEST_TOKEN")
os.environ.setdefault("AITUNNEL_API_KEY", "sk-aitunnel-test")

from app.agents import AGENTS, get_agent
from app.database import Database
from app.utils import split_text


async def main() -> None:
    assert get_agent("universal").key == "universal"
    assert len(AGENTS) >= 5
    assert len(split_text("x" * 8000)) >= 2

    with tempfile.TemporaryDirectory() as temp:
        db = Database(os.path.join(temp, "test.sqlite3"))
        await db.init()
        await db.set_agent_key(1, "tech")
        assert await db.get_agent_key(1) == "tech"
        await db.add_message(100, 1, "user", "hello")
        await db.add_message(100, 1, "assistant", "world")
        history = await db.get_history(100, 1, 10)
        assert history == [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "world"},
        ]
        await db.set_group_enabled(-100, True)
        assert await db.is_group_enabled(-100) is True
        await db.clear_history(100, 1)
        assert await db.get_history(100, 1, 10) == []

    print("SMOKE TEST: PASS")


if __name__ == "__main__":
    asyncio.run(main())
