"""
WebSocket Routes - Endpoints
=============================
WebSocket connection handler, task status HTTP fallback, and notification utilities.
"""

import asyncio
from datetime import datetime
from time import perf_counter

import structlog
from celery.result import AsyncResult
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from app.api.deps import get_current_user
from app.services.auth_service import UserAuth, decode_token
from app.tasks.celery_app import celery_app

from .manager import manager, normalize_status

logger = structlog.get_logger(__name__)

router = APIRouter()


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
    - {"type": "join_document", "proposal_id": N, "user_name": "..."} - Join document
    - {"type": "leave_document", "proposal_id": N} - Leave document
    - {"type": "lock_section", "section_id": N, "user_name": "..."} - Lock a section
    - {"type": "unlock_section", "section_id": N} - Unlock a section
    - {"type": "cursor_update", "proposal_id": N, "section_id": N, "position": N}
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
        manager.record_outbound_event("connected")
        await websocket.send_json(
            {
                "type": "connected",
                "user_id": user_id,
                "message": "WebSocket connection established",
            }
        )

        while True:
            try:
                # Wait for messages from client
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=30.0,  # Ping timeout
                )

                msg_type = data.get("type")
                manager.record_inbound_event(str(msg_type or "unknown"))

                if msg_type == "ping":
                    manager.record_outbound_event("pong")
                    await websocket.send_json({"type": "pong"})

                elif msg_type == "watch_task":
                    task_id = data.get("task_id")
                    if task_id:
                        watch_started = perf_counter()
                        manager.watch_task(task_id, user_id)
                        # Send current task status
                        result = AsyncResult(task_id, app=celery_app)
                        await websocket.send_json(
                            {
                                "type": "task_status",
                                "task_id": task_id,
                                "status": normalize_status(result),
                            }
                        )
                        manager.record_outbound_event("task_status")
                        manager.record_task_watch_latency((perf_counter() - watch_started) * 1000)

                elif msg_type == "unwatch_task":
                    task_id = data.get("task_id")
                    if task_id:
                        manager.unwatch_task(task_id, user_id)

                elif msg_type == "join_document":
                    proposal_id = data.get("proposal_id")
                    user_name = data.get("user_name", f"User {user_id}")
                    if proposal_id:
                        await manager.join_document(proposal_id, user_id, user_name)

                elif msg_type == "leave_document":
                    proposal_id = data.get("proposal_id")
                    if proposal_id:
                        await manager.leave_document(proposal_id, user_id)

                elif msg_type == "lock_section":
                    section_id = data.get("section_id")
                    user_name = data.get("user_name", f"User {user_id}")
                    proposal_id = data.get("proposal_id")
                    if section_id:
                        lock = manager.lock_section(section_id, user_id, user_name, proposal_id)
                        if lock:
                            manager.record_outbound_event("lock_acquired")
                            await websocket.send_json({"type": "lock_acquired", **lock})
                            if proposal_id:
                                await manager._broadcast_presence(proposal_id)
                        else:
                            existing = manager.get_lock(section_id)
                            manager.record_outbound_event("lock_denied")
                            await websocket.send_json(
                                {
                                    "type": "lock_denied",
                                    "section_id": section_id,
                                    "held_by": existing,
                                }
                            )

                elif msg_type == "unlock_section":
                    section_id = data.get("section_id")
                    proposal_id = data.get("proposal_id")
                    if section_id:
                        manager.unlock_section(section_id, user_id)
                        manager.record_outbound_event("lock_released")
                        await websocket.send_json(
                            {
                                "type": "lock_released",
                                "section_id": section_id,
                            }
                        )
                        if proposal_id:
                            await manager._broadcast_presence(proposal_id)

                elif msg_type == "cursor_update":
                    # Broadcast cursor position to other users in the document
                    proposal_id = data.get("proposal_id")
                    if proposal_id and proposal_id in manager.document_presence:
                        user_name = data.get("user_name", f"User {user_id}")
                        cursor = manager.update_cursor(
                            proposal_id=proposal_id,
                            user_id=user_id,
                            user_name=user_name,
                            section_id=data.get("section_id"),
                            position=data.get("position"),
                        )
                        cursor_msg = {
                            "type": "cursor_update",
                            **cursor,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                        for uid in manager.document_presence[proposal_id]:
                            if uid != user_id:
                                await manager.send_to_user(uid, cursor_msg)
                        await manager._broadcast_presence(proposal_id)

            except TimeoutError:
                # Send ping to keep connection alive
                try:
                    manager.record_outbound_event("ping")
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break

    except WebSocketDisconnect:
        # Clean up presence from all documents
        for pid in list(manager.document_presence.keys()):
            if user_id in manager.document_presence.get(pid, {}):
                await manager.leave_document(pid, user_id)
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        for pid in list(manager.document_presence.keys()):
            if user_id in manager.document_presence.get(pid, {}):
                await manager.leave_document(pid, user_id)
        manager.disconnect(websocket, user_id)


@router.get("/ws/task/{task_id}/status")
async def get_task_status_http(
    task_id: str,
    _current_user: UserAuth = Depends(get_current_user),
) -> dict:
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


# -------------------------------------------------------------------------
# Utility Functions for Other Modules
# -------------------------------------------------------------------------


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
