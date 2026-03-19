"""
sse_bridge.py — connects the refinement loop's SSE queue to
the FastAPI observation endpoint.

Usage in the FastAPI app:

    from refinement_loop.sse_bridge import sse_manager, run_loop_background

    @app.get("/loop/stream")
    async def stream(request: Request):
        return EventSourceResponse(sse_manager.stream(request))

    @app.post("/loop/start")
    async def start(background_tasks: BackgroundTasks):
        background_tasks.add_task(run_loop_background)
        return {"status": "started"}
"""

from __future__ import annotations

import asyncio
import json
import datetime
from typing import AsyncGenerator

from refinement_loop.config import SSE_QUEUE_MAXSIZE


class SSEManager:
    """
    Manages a set of subscriber queues. When the loop emits an event,
    it is fanned out to all connected clients.
    """

    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue] = []
        self._history: list[dict] = []        # last N events for late joiners
        self._history_limit = 200

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=SSE_QUEUE_MAXSIZE)
        self._subscribers.append(q)
        # Replay history for the new subscriber
        for event in self._history:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                break
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass

    def publish(self, event: dict) -> None:
        """Broadcast an event to all subscribers."""
        self._history.append(event)
        if len(self._history) > self._history_limit:
            self._history = self._history[-self._history_limit:]
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass  # slow client — drop

    async def stream(self, request) -> AsyncGenerator[str, None]:
        """
        SSE generator for use with sse-starlette or manual streaming.
        Yields raw SSE-formatted strings.
        """
        q = self.subscribe()
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield _format_sse(event)
                except asyncio.TimeoutError:
                    # Heartbeat to keep the connection alive
                    yield ": heartbeat\n\n"
        finally:
            self.unsubscribe(q)


def _format_sse(event: dict) -> str:
    event_name = event.get("event", "message")
    data = json.dumps(event)
    return f"event: {event_name}\ndata: {data}\n\n"


sse_manager = SSEManager()


async def run_loop_background(scenario_ids: list[str] | None = None) -> None:
    """
    Run the refinement loop as a background coroutine, publishing
    all events to the SSE manager.
    """
    from refinement_loop.loop import RefinementLoop

    # Create a queue and wire it to the SSE manager
    q: asyncio.Queue = asyncio.Queue(maxsize=SSE_QUEUE_MAXSIZE)

    async def _relay():
        while True:
            event = await q.get()
            sse_manager.publish(event)
            if event.get("event") == "loop_finished":
                break

    relay_task = asyncio.create_task(_relay())

    loop = RefinementLoop(sse_queue=q, scenario_ids=scenario_ids)
    await loop.run()
    await relay_task
