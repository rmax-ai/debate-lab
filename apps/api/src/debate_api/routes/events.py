"""SSE event streaming endpoint."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from debate_api.dependencies import get_emitter

router = APIRouter(prefix="/runs", tags=["events"])


@router.get("/{run_id}/events")
async def stream_events(run_id: uuid.UUID, request: Request) -> EventSourceResponse:
    """Stream debate run events via Server-Sent Events."""
    emitter = get_emitter()

    async def event_generator():
        queue: asyncio.Queue[dict[str, Any] | None] = emitter.subscribe(run_id)
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except TimeoutError:
                    # Send keep-alive comment
                    yield {"comment": "keepalive"}
                    continue

                if event is None:  # Sentinel: stream ended
                    break

                yield {
                    "event": event.get("event_type", "message"),
                    "id": str(uuid.uuid4()),
                    "data": json.dumps(event.get("payload", {})),
                }
        finally:
            emitter.unsubscribe(run_id, queue)

    return EventSourceResponse(event_generator())
