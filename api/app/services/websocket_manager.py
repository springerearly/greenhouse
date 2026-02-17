"""
WebSocket Manager — управляет подключёнными клиентами и рассылает им сообщения.

Архитектура:
  - Каждый браузер подключается к /ws
  - Клиент отправляет: {"type": "subscribe", "channels": ["sensors", "gpio", "alerts"]}
  - Сервер пушит: {"channel": "sensors", "event": "update", "data": {...}, "timestamp": "..."}
"""

import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, Set
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # websocket -> набор каналов, на которые подписан клиент
        self._connections: Dict[WebSocket, Set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self._connections[websocket] = set()
        print(f"[WS] Client connected. Total: {len(self._connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self._connections.pop(websocket, None)
        print(f"[WS] Client disconnected. Total: {len(self._connections)}")

    async def subscribe(self, websocket: WebSocket, channels: list[str]):
        async with self._lock:
            if websocket in self._connections:
                self._connections[websocket] = set(channels)

    async def broadcast(self, channel: str, event: str, data: dict):
        """Разослать сообщение всем подписчикам канала."""
        message = json.dumps({
            "channel": channel,
            "event": event,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        dead: list[WebSocket] = []
        async with self._lock:
            targets = [
                ws for ws, channels in self._connections.items()
                if channel in channels or "all" in channels
            ]

        for ws in targets:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            await self.disconnect(ws)

    async def send_personal(self, websocket: WebSocket, channel: str, event: str, data: dict):
        """Отправить сообщение конкретному клиенту."""
        message = json.dumps({
            "channel": channel,
            "event": event,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        try:
            await websocket.send_text(message)
        except Exception:
            await self.disconnect(websocket)

    @property
    def connections_count(self) -> int:
        return len(self._connections)


# Singleton экземпляр — используется во всём приложении
manager = ConnectionManager()
