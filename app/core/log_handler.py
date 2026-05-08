"""
Async, non-blocking DB log handler.

Architecture:
  - AsyncDBHandler (sync logging.Handler) enqueues records into an asyncio.Queue
  - _db_log_worker() is a background asyncio Task that drains the queue in
    configurable batches and writes SystemLog rows — without ever blocking a request.
  - If the queue is full, records are silently dropped (never blocks).
  - If DB is unavailable, records are dropped after logging a single warning to stdout.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from app.core.context import current_user_id_var, request_id_var

# Loggers that must NEVER write to DB (avoid recursion / infinite loops)
_SUPPRESS_PREFIXES = ("app.core.log_handler", "sqlalchemy", "asyncio", "uvicorn", "fastapi")

_log_queue: asyncio.Queue = asyncio.Queue(maxsize=10_000)
_worker_task: Optional[asyncio.Task] = None


class AsyncDBHandler(logging.Handler):
    """
    Drop-in logging.Handler.  Enqueues records into an asyncio queue.
    The background worker drains the queue and writes to system_logs.
    """

    def __init__(self, level: int = logging.INFO) -> None:
        super().__init__(level)

    def emit(self, record: logging.LogRecord) -> None:
        # Never log our own internals — avoids recursion
        if any(record.name.startswith(p) for p in _SUPPRESS_PREFIXES):
            return
        try:
            msg = record.getMessage()
            # Extract action keyword from message prefix: "USERS_LIST count=5" → "USERS_LIST"
            action = msg.split()[0][:100] if msg.strip() else ""

            # Pull user/request IDs from contextvar (set by middleware + dependency)
            user_id = getattr(record, "user_id", None) or current_user_id_var.get("") or None
            request_id = getattr(record, "request_id", None) or request_id_var.get("") or None

            entry = {
                "level": record.levelname,
                "logger": record.name,
                "action": action,
                "message": self.format(record),
                "user_id": str(user_id) if user_id else None,
                "request_id": str(request_id) if request_id else None,
            }
            _log_queue.put_nowait(entry)
        except asyncio.QueueFull:
            pass  # Drop — never block a request for logging
        except Exception:
            pass  # Never let the logging infrastructure crash the app


async def _db_log_worker() -> None:
    """
    Background coroutine.  Drains _log_queue in batches and writes to system_logs.
    Uses a separate AsyncSession so it never interferes with request sessions.
    """
    from app.db.session import AsyncSessionLocal  # lazy import — avoids circular deps
    from app.modules.system_logs.model import SystemLog  # lazy import

    _stdout = logging.getLogger("app.core.log_handler")
    BATCH = 50
    FLUSH_EVERY = 2.0  # seconds

    buffer: list[dict] = []
    while True:
        try:
            loop = asyncio.get_event_loop()
            deadline = loop.time() + FLUSH_EVERY

            # Collect up to BATCH entries within FLUSH_EVERY seconds
            while len(buffer) < BATCH:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    break
                try:
                    entry = await asyncio.wait_for(_log_queue.get(), timeout=remaining)
                    buffer.append(entry)
                except asyncio.TimeoutError:
                    break

            if buffer:
                async with AsyncSessionLocal() as session:
                    for e in buffer:
                        session.add(SystemLog(
                            level=e["level"],
                            logger=e["logger"],
                            action=e.get("action"),
                            message=e["message"],
                            user_id=e.get("user_id"),
                            request_id=e.get("request_id"),
                            created_at=datetime.now(timezone.utc),
                        ))
                    try:
                        await session.commit()
                    except Exception as exc:
                        await session.rollback()
                        _stdout.warning("DB log flush failed (records dropped): %s", exc)
                buffer.clear()

        except asyncio.CancelledError:
            # Graceful shutdown: flush remaining buffer
            if buffer:
                try:
                    from app.db.session import AsyncSessionLocal
                    from app.modules.system_logs.model import SystemLog
                    async with AsyncSessionLocal() as session:
                        for e in buffer:
                            session.add(SystemLog(
                                level=e["level"],
                                logger=e["logger"],
                                action=e.get("action"),
                                message=e["message"],
                                user_id=e.get("user_id"),
                                request_id=e.get("request_id"),
                                created_at=datetime.now(timezone.utc),
                            ))
                        await session.commit()
                except Exception:
                    pass
            raise

        except Exception as exc:
            _stdout.warning("DB log worker error: %s — restarting in 5s", exc)
            buffer.clear()
            await asyncio.sleep(5)


def install_db_handler() -> AsyncDBHandler:
    """
    Attach the AsyncDBHandler to the root 'app' logger.
    Call once at application startup AFTER the DB is initialised.
    """
    handler = AsyncDBHandler(level=logging.INFO)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    logging.getLogger("app").addHandler(handler)
    return handler


async def start_db_log_worker() -> asyncio.Task:
    global _worker_task
    _worker_task = asyncio.create_task(_db_log_worker(), name="db-log-worker")
    return _worker_task


async def stop_db_log_worker() -> None:
    global _worker_task
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
    _worker_task = None
