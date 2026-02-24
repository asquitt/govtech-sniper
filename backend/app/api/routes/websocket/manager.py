"""
WebSocket Routes - Connection Manager
======================================
Manages WebSocket connections, document presence, section locking, and cursor telemetry.
"""

from collections import deque
from datetime import datetime

import structlog
from fastapi import WebSocket

logger = structlog.get_logger(__name__)


def normalize_status(result) -> str:
    if result.ready():
        return "completed" if result.successful() else "failed"
    state = (result.state or "").lower()
    if state in {"pending", "received"}:
        return "pending"
    return "processing"


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates and collaborative editing.
    """

    def __init__(self):
        # Map of user_id -> set of WebSocket connections
        self.active_connections: dict[int, set[WebSocket]] = {}
        # Map of task_id -> set of user_ids watching
        self.task_watchers: dict[str, set[int]] = {}
        # Document presence: proposal_id -> set of {user_id, user_name, ...}
        self.document_presence: dict[int, dict[int, dict]] = {}
        # Cursor telemetry: proposal_id -> user_id -> cursor payload
        self.document_cursors: dict[int, dict[int, dict]] = {}
        # Section locks: section_id -> {user_id, user_name, locked_at}
        self.section_locks: dict[int, dict] = {}
        # Diagnostics telemetry
        self.seen_user_ids: set[int] = set()
        self.total_connections = 0
        self.total_disconnects = 0
        self.reconnect_count = 0
        self.inbound_event_total = 0
        self.outbound_event_total = 0
        self.inbound_event_counts: dict[str, int] = {}
        self.outbound_event_counts: dict[str, int] = {}
        self.inbound_event_window: deque[float] = deque()
        self.outbound_event_window: deque[float] = deque()
        self.task_watch_latency_ms: deque[float] = deque(maxlen=200)

    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept and register a new connection."""
        await websocket.accept()
        self.total_connections += 1
        if user_id in self.seen_user_ids:
            self.reconnect_count += 1
        else:
            self.seen_user_ids.add(user_id)
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info("WebSocket connected", user_id=user_id)

    def disconnect(self, websocket: WebSocket, user_id: int):
        """Remove a connection."""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        self.total_disconnects += 1
        logger.info("WebSocket disconnected", user_id=user_id)

    async def send_to_user(self, user_id: int, message: dict):
        """Send a message to all connections for a user."""
        if user_id in self.active_connections:
            self.record_outbound_event(str(message.get("type", "unknown")))
            dead_connections = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    dead_connections.add(connection)
            # Clean up dead connections
            for conn in dead_connections:
                self.active_connections[user_id].discard(conn)

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected users."""
        for user_id in list(self.active_connections.keys()):
            await self.send_to_user(user_id, message)

    def watch_task(self, task_id: str, user_id: int):
        """Register a user to watch a task."""
        if task_id not in self.task_watchers:
            self.task_watchers[task_id] = set()
        self.task_watchers[task_id].add(user_id)

    def unwatch_task(self, task_id: str, user_id: int):
        """Remove a user from watching a task."""
        if task_id in self.task_watchers:
            self.task_watchers[task_id].discard(user_id)
            if not self.task_watchers[task_id]:
                del self.task_watchers[task_id]

    async def notify_task_update(self, task_id: str, status: str, result: dict = None):
        """Notify all watchers of a task update."""
        if task_id in self.task_watchers:
            message = {
                "type": "task_update",
                "task_id": task_id,
                "status": status,
                "result": result,
                "timestamp": datetime.utcnow().isoformat(),
            }
            for user_id in self.task_watchers[task_id]:
                await self.send_to_user(user_id, message)

    def _prune_event_window(self, window: deque[float], now_ts: float) -> None:
        cutoff = now_ts - 60.0
        while window and window[0] < cutoff:
            window.popleft()

    def record_inbound_event(self, event_type: str) -> None:
        now_ts = datetime.utcnow().timestamp()
        self.inbound_event_total += 1
        self.inbound_event_counts[event_type] = self.inbound_event_counts.get(event_type, 0) + 1
        self.inbound_event_window.append(now_ts)
        self._prune_event_window(self.inbound_event_window, now_ts)

    def record_outbound_event(self, event_type: str) -> None:
        now_ts = datetime.utcnow().timestamp()
        self.outbound_event_total += 1
        self.outbound_event_counts[event_type] = self.outbound_event_counts.get(event_type, 0) + 1
        self.outbound_event_window.append(now_ts)
        self._prune_event_window(self.outbound_event_window, now_ts)

    def record_task_watch_latency(self, latency_ms: float) -> None:
        self.task_watch_latency_ms.append(round(max(latency_ms, 0.0), 2))

    def telemetry_snapshot(self) -> dict:
        now_ts = datetime.utcnow().timestamp()
        self._prune_event_window(self.inbound_event_window, now_ts)
        self._prune_event_window(self.outbound_event_window, now_ts)

        latencies = list(self.task_watch_latency_ms)
        avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else None
        p95_latency = None
        if latencies:
            sorted_latencies = sorted(latencies)
            idx = max(int(round(0.95 * len(sorted_latencies))) - 1, 0)
            p95_latency = sorted_latencies[idx]

        return {
            "connections": {
                "active_user_channels": len(self.active_connections),
                "active_connection_count": sum(
                    len(channels) for channels in self.active_connections.values()
                ),
                "total_connections": self.total_connections,
                "total_disconnects": self.total_disconnects,
                "reconnect_count": self.reconnect_count,
            },
            "task_watch": {
                "watched_tasks": len(self.task_watchers),
                "avg_status_latency_ms": avg_latency,
                "p95_status_latency_ms": p95_latency,
            },
            "event_throughput": {
                "inbound_events_total": self.inbound_event_total,
                "outbound_events_total": self.outbound_event_total,
                "inbound_events_per_minute": len(self.inbound_event_window),
                "outbound_events_per_minute": len(self.outbound_event_window),
                "inbound_by_type": dict(sorted(self.inbound_event_counts.items())),
                "outbound_by_type": dict(sorted(self.outbound_event_counts.items())),
            },
        }

    # -------------------------------------------------------------------------
    # Document Presence
    # -------------------------------------------------------------------------

    async def join_document(self, proposal_id: int, user_id: int, user_name: str):
        """Register a user as present in a document."""
        if proposal_id not in self.document_presence:
            self.document_presence[proposal_id] = {}
        self.document_presence[proposal_id][user_id] = {
            "user_id": user_id,
            "user_name": user_name,
            "joined_at": datetime.utcnow().isoformat(),
        }
        await self._broadcast_presence(proposal_id)

    async def leave_document(self, proposal_id: int, user_id: int):
        """Remove a user from document presence."""
        if proposal_id in self.document_presence:
            self.document_presence[proposal_id].pop(user_id, None)
            if not self.document_presence[proposal_id]:
                del self.document_presence[proposal_id]
        if proposal_id in self.document_cursors:
            self.document_cursors[proposal_id].pop(user_id, None)
            if not self.document_cursors[proposal_id]:
                del self.document_cursors[proposal_id]
        # Release any locks held by this user in this proposal
        for section_id in list(self.section_locks.keys()):
            lock = self.section_locks[section_id]
            if lock["user_id"] == user_id and lock.get("proposal_id") in (None, proposal_id):
                del self.section_locks[section_id]
        await self._broadcast_presence(proposal_id)

    def get_presence(self, proposal_id: int) -> list:
        """Get list of users present in a document."""
        if proposal_id not in self.document_presence:
            return []
        return list(self.document_presence[proposal_id].values())

    async def _broadcast_presence(self, proposal_id: int):
        """Broadcast presence update to all users in a document."""
        users = self.get_presence(proposal_id)
        locks = self.get_locks_for_proposal(proposal_id)
        cursors = self.get_cursors(proposal_id)
        message = {
            "type": "presence_update",
            "proposal_id": proposal_id,
            "users": users,
            "locks": locks,
            "cursors": cursors,
            "timestamp": datetime.utcnow().isoformat(),
        }
        # Send to all present users
        for info in users:
            await self.send_to_user(info["user_id"], message)

    # -------------------------------------------------------------------------
    # Section Locking
    # -------------------------------------------------------------------------

    def lock_section(
        self,
        section_id: int,
        user_id: int,
        user_name: str,
        proposal_id: int | None = None,
    ) -> dict | None:
        """
        Attempt to lock a section. Returns the lock if successful, None if already locked.
        """
        existing = self.section_locks.get(section_id)
        if existing and existing["user_id"] != user_id:
            return None  # Already locked by someone else
        lock = {
            "section_id": section_id,
            "user_id": user_id,
            "user_name": user_name,
            "proposal_id": proposal_id,
            "locked_at": datetime.utcnow().isoformat(),
        }
        self.section_locks[section_id] = lock
        return lock

    def unlock_section(self, section_id: int, user_id: int) -> bool:
        """Release a section lock. Returns True if unlocked."""
        existing = self.section_locks.get(section_id)
        if not existing:
            return True
        if existing["user_id"] != user_id:
            return False  # Not the lock owner
        del self.section_locks[section_id]
        return True

    def get_lock(self, section_id: int) -> dict | None:
        """Get the current lock on a section."""
        return self.section_locks.get(section_id)

    def get_locks_for_proposal(self, proposal_id: int) -> list:
        """Get section locks for a proposal."""
        return [
            lock
            for lock in self.section_locks.values()
            if lock.get("proposal_id") in (None, proposal_id)
        ]

    def update_cursor(
        self,
        proposal_id: int,
        user_id: int,
        user_name: str,
        section_id: int | None,
        position: int | None,
    ) -> dict:
        """Store last known cursor position for a user in a proposal."""
        if proposal_id not in self.document_cursors:
            self.document_cursors[proposal_id] = {}
        cursor = {
            "user_id": user_id,
            "user_name": user_name,
            "section_id": section_id,
            "position": position,
            "updated_at": datetime.utcnow().isoformat(),
        }
        self.document_cursors[proposal_id][user_id] = cursor
        return cursor

    def get_cursors(self, proposal_id: int) -> list:
        """Get cursor telemetry for a proposal."""
        if proposal_id not in self.document_cursors:
            return []
        return list(self.document_cursors[proposal_id].values())


# Global connection manager
manager = ConnectionManager()
