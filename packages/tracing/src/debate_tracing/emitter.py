"""SSE event emission — pushes events to subscriber queues."""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from collections import defaultdict
from typing import Any


class EventEmitter:
    """Manages per-run asyncio queues for SSE subscribers.

    The API layer pushes events into these queues; the SSE endpoint
    reads from them and streams to clients.
    """

    def __init__(self) -> None:
        self._queues: dict[uuid.UUID, list[asyncio.Queue[dict[str, Any] | None]]] = (
            defaultdict(list)
        )

    def subscribe(self, run_id: uuid.UUID) -> asyncio.Queue[dict[str, Any] | None]:
        """Create a new queue for a run subscriber.

        Returns the queue the caller should read from.
        """
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue(maxsize=256)
        self._queues[run_id].append(queue)
        return queue

    def unsubscribe(self, run_id: uuid.UUID, queue: asyncio.Queue[dict[str, Any] | None]) -> None:
        """Remove a subscriber queue."""
        queues = self._queues.get(run_id, [])
        if queue in queues:
            queues.remove(queue)
        if not queues:
            self._queues.pop(run_id, None)

    async def emit(
        self,
        run_id: uuid.UUID,
        event_type: str,
        *,
        actor: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Push an event to all subscribers of a run."""
        message: dict[str, Any] = {
            "event_type": event_type,
            "actor": actor,
            "payload": payload or {},
        }
        for queue in self._queues.get(run_id, []):
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(message)

    async def close_run(self, run_id: uuid.UUID) -> None:
        """Send sentinel to all subscribers and clean up."""
        for queue in self._queues.pop(run_id, []):
            await queue.put(None)  # sentinel: stream done
