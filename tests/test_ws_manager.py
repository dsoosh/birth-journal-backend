"""Unit tests for WebSocket connection manager."""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.app.ws_manager import ConnectionManager


def run_async(coro):
    """Helper to run async code in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


class TestConnectionManager:
    """Test cases for ConnectionManager class."""

    def test_init_creates_empty_connections(self):
        """ConnectionManager should start with empty connections dict."""
        manager = ConnectionManager()
        assert hasattr(manager, 'active_connections')
        assert len(manager.active_connections) == 0

    def test_connect_accepts_websocket(self):
        """connect() should call accept() on the websocket."""
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        
        run_async(manager.connect("case-1", mock_ws))
        mock_ws.accept.assert_called_once()

    def test_connect_returns_connection_id(self):
        """connect() should return a connection ID string."""
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        
        conn_id = run_async(manager.connect("case-1", mock_ws))
        assert isinstance(conn_id, str)
        assert len(conn_id) == 36  # UUID format

    def test_connect_stores_connection(self):
        """connect() should store the connection."""
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        
        run_async(manager.connect("case-1", mock_ws))
        assert "case-1" in manager.active_connections
        assert len(manager.active_connections["case-1"]) == 1

    def test_connect_multiple_to_same_case(self):
        """Multiple connections to same case should all be stored."""
        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        
        run_async(manager.connect("case-1", ws1))
        run_async(manager.connect("case-1", ws2))
        assert len(manager.active_connections["case-1"]) == 2

    def test_disconnect_removes_connection(self):
        """disconnect() should remove the connection."""
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        
        run_async(manager.connect("case-1", mock_ws))
        manager.disconnect("case-1", mock_ws)
        assert "case-1" not in manager.active_connections

    def test_disconnect_leaves_other_connections(self):
        """disconnect() should only remove the specified connection."""
        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        
        run_async(manager.connect("case-1", ws1))
        run_async(manager.connect("case-1", ws2))
        manager.disconnect("case-1", ws1)
        assert len(manager.active_connections["case-1"]) == 1

    def test_disconnect_nonexistent_is_safe(self):
        """disconnect() on nonexistent connection should not raise."""
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        manager.disconnect("case-1", mock_ws)  # Should not raise

    def test_broadcast_sends_to_all(self):
        """broadcast() should send to all connections for a case."""
        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        
        run_async(manager.connect("case-1", ws1))
        run_async(manager.connect("case-1", ws2))
        
        message = {"type": "event", "data": "test"}
        run_async(manager.broadcast("case-1", message))
        
        ws1.send_json.assert_called_once_with(message)
        ws2.send_json.assert_called_once_with(message)

    def test_broadcast_only_to_specified_case(self):
        """broadcast() should only send to connections for the specified case."""
        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        
        run_async(manager.connect("case-1", ws1))
        run_async(manager.connect("case-2", ws2))
        
        message = {"type": "event"}
        run_async(manager.broadcast("case-1", message))
        
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_not_called()

    def test_broadcast_to_nonexistent_case_is_safe(self):
        """broadcast() to nonexistent case should not raise."""
        manager = ConnectionManager()
        run_async(manager.broadcast("nonexistent", {"data": "test"}))  # Should not raise

    def test_broadcast_removes_dead_connections(self):
        """broadcast() should remove connections that fail to send."""
        manager = ConnectionManager()
        ws_alive = AsyncMock()
        ws_dead = AsyncMock()
        ws_dead.send_json.side_effect = Exception("Connection closed")
        
        run_async(manager.connect("case-1", ws_alive))
        run_async(manager.connect("case-1", ws_dead))
        
        run_async(manager.broadcast("case-1", {"data": "test"}))
        
        # Dead connection should be removed
        assert len(manager.active_connections["case-1"]) == 1

    def test_send_personal(self):
        """send_personal() should send to a specific websocket."""
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        
        message = {"type": "personal"}
        run_async(manager.send_personal(mock_ws, message))
        mock_ws.send_json.assert_called_once_with(message)

    def test_send_personal_handles_errors(self):
        """send_personal() should not raise on send failure."""
        manager = ConnectionManager()
        ws = AsyncMock()
        ws.send_json.side_effect = Exception("Connection closed")
        run_async(manager.send_personal(ws, {"data": "test"}))  # Should not raise
