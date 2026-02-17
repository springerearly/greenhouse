"""
WebSocket роутер — /ws

Клиент подключается и отправляет:
    {"type": "subscribe", "channels": ["sensors", "gpio", "alerts", "devices"]}

Сервер пушит сообщения в формате:
    {"channel": "sensors", "event": "update", "data": {...}, "timestamp": "..."}

Доступные каналы:
    sensors  — показания датчиков ESP-устройств
    gpio     — изменения GPIO Raspberry Pi
    alerts   — новые алерты и срабатывания автоматизации
    devices  — изменения статуса устройств
    system   — системные сообщения
    all      — все каналы сразу
"""

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..services.websocket_manager import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    # Приветственное сообщение
    await manager.send_personal(websocket, "system", "connected", {
        "message": "Connected to Greenhouse WebSocket",
        "available_channels": ["sensors", "gpio", "alerts", "devices", "system", "all"],
    })

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await manager.send_personal(websocket, "system", "error", {
                    "message": "Invalid JSON"
                })
                continue

            msg_type = msg.get("type")

            if msg_type == "subscribe":
                channels = msg.get("channels", [])
                await manager.subscribe(websocket, channels)
                await manager.send_personal(websocket, "system", "subscribed", {
                    "channels": channels
                })

            elif msg_type == "ping":
                await manager.send_personal(websocket, "system", "pong", {})

            else:
                await manager.send_personal(websocket, "system", "error", {
                    "message": f"Unknown message type: {msg_type}"
                })

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
