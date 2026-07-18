"""Адаптер, оборачивающий FastAPI WebSocket в протокол pycrdt-websocket."""

from starlette.websockets import WebSocketDisconnect

from fastapi import WebSocket


class FastAPIWebsocketAdapter:
    """Реализует протокол Websocket из pycrdt-websocket вручную,
    без наследования — чтобы не зависеть от того, как именно
    эта библиотека определяет свой Protocol в конкретной версии.
    """

    def __init__(self, websocket: WebSocket, path: str) -> None:
        self._websocket = websocket
        self._path = path
        self._disconnected = False

    @property
    def path(self) -> str:
        return self._path

    async def send(self, message: bytes) -> None:
        if self._disconnected:
            return
        try:
            await self._websocket.send_bytes(message)
        except WebSocketDisconnect:
            self._disconnected = True

    async def recv(self) -> bytes:
        try:
            return await self._websocket.receive_bytes()
        except WebSocketDisconnect:
            self._disconnected = True
            raise StopAsyncIteration from None

    def __aiter__(self):
        return self

    async def __anext__(self) -> bytes:
        if self._disconnected:
            raise StopAsyncIteration
        return await self.recv()
