"""Глобальный экземпляр WebSocket-сервера для CRDT-синхронизации заметок."""

from pycrdt.websocket import WebsocketServer

websocket_server = WebsocketServer(auto_clean_rooms=True)

hydrated_rooms: set[str] = set()
