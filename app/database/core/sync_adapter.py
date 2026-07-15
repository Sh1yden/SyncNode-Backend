"""Адаптер, оборачивающий FastAPI WebSocket в протокол pycrdt-websocket."""

import logging

from fastapi import WebSocket

_log = logging.getLogger("syncnode.sync_adapter")


class FastAPIWebsocketAdapter:
    """Реализует протокол Websocket из pycrdt-websocket вручную,
    без наследования — чтобы не зависеть от того, как именно
    эта библиотека определяет свой Protocol в конкретной версии.
    """

    def __init__(self, websocket: WebSocket, path: str) -> None:
        self._websocket = websocket
        self._path = path

    @property
    def path(self) -> str:
        return self._path

    async def send(self, message: bytes) -> None:
        await self._websocket.send_bytes(message)

    async def recv(self) -> bytes:
        return await self._websocket.receive_bytes()

    def __aiter__(self):
        return self

    async def __anext__(self) -> bytes:
        try:
            return await self.recv()
        except Exception as exc:
            _log.warning("recv() ended iteration for %s: %r", self._path, exc)
            raise StopAsyncIteration
