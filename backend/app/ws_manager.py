"""WebSocket connection manager for real-time case events."""
from __future__ import annotations

import json
import uuid
from typing import Callable

from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections per case."""

    def __init__(self):
        # {case_id: {connection_id: websocket}}
        self.active_connections: dict[str, dict[str, WebSocket]] = {}
        self.connection_ids: dict[WebSocket, str] = {}

    async def connect(self, case_id: str, websocket: WebSocket) -> str:
        """Register a new connection for a case. Returns connection_id."""
        await websocket.accept()
        
        if case_id not in self.active_connections:
            self.active_connections[case_id] = {}
        
        connection_id = str(uuid.uuid4())
        self.active_connections[case_id][connection_id] = websocket
        self.connection_ids[websocket] = connection_id
        
        return connection_id

    def disconnect(self, case_id: str, websocket: WebSocket) -> None:
        """Unregister a connection."""
        connection_id = self.connection_ids.pop(websocket, None)
        if connection_id and case_id in self.active_connections:
            self.active_connections[case_id].pop(connection_id, None)
            if not self.active_connections[case_id]:
                del self.active_connections[case_id]

    async def broadcast(self, case_id: str, message: dict) -> None:
        """Broadcast a message to all connections for a case."""
        if case_id not in self.active_connections:
            return
        
        # Send to all connected clients
        disconnected = []
        for conn_id, connection in self.active_connections[case_id].items():
            try:
                await connection.send_json(message)
            except Exception:
                # Connection is dead
                disconnected.append(conn_id)
        
        # Clean up dead connections
        for conn_id in disconnected:
            self.active_connections[case_id].pop(conn_id, None)
        
        if not self.active_connections[case_id]:
            del self.active_connections[case_id]

    async def send_personal(self, websocket: WebSocket, message: dict) -> None:
        """Send a message to a specific connection."""
        try:
            await websocket.send_json(message)
        except Exception:
            pass


# Global instance
manager = ConnectionManager()
