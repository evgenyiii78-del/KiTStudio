import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable

@dataclass
class Job:
    run: Callable[[], Awaitable[str]]
    done: Callable[[str|None,Exception|None], Awaitable[None]]

class JobQueue:
    def __init__(self,maxsize=20,workers=2): self.q=asyncio.Queue(maxsize=maxsize); self.workers=workers; self.tasks=[]
    async def start(self): self.tasks=[asyncio.create_task(self.worker()) for _ in range(self.workers)]
    async def stop(self):
        for t in self.tasks: t.cancel()
    async def submit(self,job): await self.q.put(job); return self.q.qsize()
    async def worker(self):
        while True:
            job=await self.q.get()
            try: await job.done(await job.run(),None)
            except Exception as e: await job.done(None,e)
            finally: self.q.task_done()
