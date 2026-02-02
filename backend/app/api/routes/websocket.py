"""
RFP Sniper - WebSocket Routes
==============================
Real-time updates for long-running tasks.
"""

import asyncio
import json
from typing import Dict, Set
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from celery.result import AsyncResult
import structlog

from app.tasks.celery_app import celery_app
from app.services.auth_service import decode_token

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["WebSocket"])


def normalize_status(result: AsyncResult) -> str:
    if result.ready():
        return "completed" if result.successful() else "failed"
    state = (result.state or "").lower()
    if state in {"pending", "received"}:
        return "pending"
    return "processing"


# =============================================================================
# Connection Manager
# =============================================================================

class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.
    """

    def __init__(self):
        # Map of user_id -> set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Map of task_id -> set of user_ids watching
        self.task_watchers: Dict[str, Set[int]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept and register a new connection."""
        await websocket.accept()
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
        logger.info("WebSocket disconnected", user_id=user_id)

    async def send_to_user(self, user_id: int, message: dict):
        """Send a message to all connections for a user."""
        if user_id in self.active_connections:
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


# Global connection manager
manager = ConnectionManager()


# =============================================================================
# WebSocket Endpoints
# =============================================================================

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    Main WebSocket endpoint for real-time updates.

    Connect with: ws://localhost:8000/ws?token=<jwt_token>

    Message types:
    - task_update: Updates on long-running tasks
    - notification: System notifications
    - rfp_update: Changes to RFP data

    Client can send:
    - {"type": "watch_task", "task_id": "xxx"} - Subscribe to task updates
    - {"type": "unwatch_task", "task_id": "xxx"} - Unsubscribe from task
    - {"type": "ping"} - Keep-alive ping
    """
    # Authenticate the connection
    token_data = decode_token(token)
    if not token_data:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    user_id = token_data.user_id

    await manager.connect(websocket, user_id)

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "user_id": user_id,
            "message": "WebSocket connection established",
        })

        while True:
            try:
                # Wait for messages from client
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=30.0  # Ping timeout
                )

                msg_type = data.get("type")

                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

                elif msg_type == "watch_task":
                    task_id = data.get("task_id")
                    if task_id:
                        manager.watch_task(task_id, user_id)
                        # Send current task status
                        result = AsyncResult(task_id, app=celery_app)
                        await websocket.send_json({
                            "type": "task_status",
                            "task_id": task_id,
                            "status": normalize_status(result),
                        })

                elif msg_type == "unwatch_task":
                    task_id = data.get("task_id")
                    if task_id:
                        manager.unwatch_task(task_id, user_id)

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, user_id)


# =============================================================================
# Task Status Endpoint (Fallback HTTP)
# =============================================================================

@router.get("/ws/task/{task_id}/status")
async def get_task_status_http(task_id: str) -> dict:
    """
    HTTP fallback for getting task status.
    Use this if WebSocket is not available.
    """
    result = AsyncResult(task_id, app=celery_app)

    response = {
        "task_id": task_id,
        "status": normalize_status(result),
    }

    if result.ready():
        if result.successful():
            response["result"] = result.get()
        else:
            response["error"] = str(result.result)

    return response


# =============================================================================
# Utility Functions for Other Modules
# =============================================================================

async def notify_user(user_id: int, notification_type: str, data: dict):
    """
    Send a notification to a specific user.
    Can be called from other modules.
    """
    message = {
        "type": notification_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    }
    await manager.send_to_user(user_id, message)


async def notify_task_complete(task_id: str, status: str, result: dict = None):
    """
    Notify watchers that a task has completed.
    Called by Celery task callbacks.
    """
    await manager.notify_task_update(task_id, status, result)
