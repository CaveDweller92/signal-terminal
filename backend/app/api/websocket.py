"""
WebSocket endpoint for live signal updates and exit alerts.

Clients connect to /ws/live and receive:
- New entry signals (BUY/SELL)
- Exit alerts (stop_loss, profit_target, indicator_reversal, etc.)
- Position updates (P&L changes)
- Regime changes

The position monitor pushes exit alerts through here.
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Active: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Send a message to all connected clients."""
        disconnected: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # Clean up dead connections
        for conn in disconnected:
            self.active_connections.remove(conn)


# Singleton — imported by position monitor and other modules
ws_manager = ConnectionManager()


@router.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; client can also send commands
            data = await websocket.receive_text()
            # Echo back as acknowledgment (can be extended for client commands)
            await websocket.send_json({"type": "ack", "received": data})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
