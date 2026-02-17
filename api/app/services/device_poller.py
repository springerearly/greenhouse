"""
Device Poller — фоновый сервис для опроса ESP8266/ESP32 устройств по HTTP.

Каждое устройство опрашивается с индивидуальным интервалом (poll_interval).
Результаты:
  - сохраняются в PostgreSQL (sensor_readings)
  - пушатся в WebSocket (канал "sensors")
  - обновляют статус устройства (online / offline)
"""

import asyncio
import json
import httpx
from datetime import datetime, timezone
from typing import Dict, Optional

from ..database import SessionLocal
from .. import models
from .websocket_manager import manager as ws_manager


# Активные задачи опроса: device_id -> asyncio.Task
_poll_tasks: Dict[int, asyncio.Task] = {}


async def _fetch_device_status(device: models.Device) -> Optional[dict]:
    """
    Выполняет HTTP GET http://{ip}:{port}/status
    Ожидаемый формат ответа от ESP:
    {
        "sensors": {
            "temperature": {"value": 24.5, "unit": "C"},
            "humidity":    {"value": 65.2, "unit": "%"},
            ...
        },
        "actuators": {
            "relay1": 0,
            "relay2": 1,
            "pwm": 128
        },
        "info": {
            "firmware": "1.0.0",
            "mac": "AA:BB:CC:DD:EE:FF",
            "uptime": 3600
        }
    }
    """
    url = f"http://{device.ip_address}:{device.port}/status"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        print(f"[Poller] Device {device.id} ({device.ip_address}) unreachable: {exc}")
        return None


async def _save_readings(device_id: int, sensors: dict):
    """Сохраняет показания датчиков в PostgreSQL."""
    with SessionLocal() as db:
        for sensor_type, payload in sensors.items():
            if isinstance(payload, dict):
                value = payload.get("value")
                unit = payload.get("unit")
            else:
                value = payload
                unit = None

            if value is None:
                continue

            reading = models.SensorReading(
                device_id=device_id,
                sensor_type=sensor_type,
                value=float(value),
                unit=unit,
            )
            db.add(reading)
        db.commit()


async def _update_device_status(device_id: int, status: str, extra: dict = None):
    """Обновляет статус и метаданные устройства."""
    with SessionLocal() as db:
        device = db.query(models.Device).filter(models.Device.id == device_id).first()
        if not device:
            return
        device.status = status
        if status == "online":
            device.last_seen = datetime.now(timezone.utc)
        if extra:
            if "firmware" in extra:
                device.firmware_version = extra["firmware"]
            if "mac" in extra:
                device.mac_address = extra["mac"]
        db.commit()


async def _create_alert(device_id: int, message: str, level: str = "warning"):
    """Создаёт алерт в БД и пушит в WebSocket."""
    with SessionLocal() as db:
        alert = models.Alert(device_id=device_id, message=message, level=level)
        db.add(alert)
        db.commit()
        db.refresh(alert)

        await ws_manager.broadcast("alerts", "new_alert", {
            "id": alert.id,
            "device_id": device_id,
            "level": level,
            "message": message,
            "created_at": alert.created_at.isoformat(),
        })


async def _poll_loop(device_id: int):
    """Основной цикл опроса одного устройства."""
    prev_status = None

    while True:
        # Каждый раз перечитываем устройство из БД (poll_interval мог измениться)
        with SessionLocal() as db:
            device = db.query(models.Device).filter(models.Device.id == device_id).first()
            if not device or not device.enabled:
                print(f"[Poller] Device {device_id} disabled or deleted, stopping poll.")
                break
            interval = device.poll_interval
            device_name = device.name

        data = await _fetch_device_status(device)

        if data is None:
            # Устройство недоступно
            await _update_device_status(device_id, "offline")
            if prev_status != "offline":
                await _create_alert(device_id, f"Устройство '{device_name}' недоступно", "error")
                await ws_manager.broadcast("devices", "status_change", {
                    "device_id": device_id, "status": "offline"
                })
            prev_status = "offline"
        else:
            # Устройство ответило
            info = data.get("info", {})
            await _update_device_status(device_id, "online", extra=info)

            if prev_status != "online":
                await ws_manager.broadcast("devices", "status_change", {
                    "device_id": device_id, "status": "online"
                })
            prev_status = "online"

            sensors = data.get("sensors", {})
            if sensors:
                await _save_readings(device_id, sensors)

                # Пуш в WebSocket
                await ws_manager.broadcast("sensors", "update", {
                    "device_id": device_id,
                    "device_name": device_name,
                    "sensors": sensors,
                    "actuators": data.get("actuators", {}),
                })

        await asyncio.sleep(interval)


def start_polling(device_id: int):
    """Запустить фоновую задачу опроса для устройства."""
    if device_id in _poll_tasks and not _poll_tasks[device_id].done():
        return  # Уже запущено

    task = asyncio.create_task(_poll_loop(device_id))
    _poll_tasks[device_id] = task
    print(f"[Poller] Started polling for device {device_id}")


def stop_polling(device_id: int):
    """Остановить задачу опроса для устройства."""
    task = _poll_tasks.pop(device_id, None)
    if task and not task.done():
        task.cancel()
        print(f"[Poller] Stopped polling for device {device_id}")


def start_all_polling():
    """Запустить опрос всех активных устройств из БД (вызывается при старте приложения)."""
    with SessionLocal() as db:
        devices = db.query(models.Device).filter(models.Device.enabled == True).all()
        for device in devices:
            start_polling(device.id)
    print(f"[Poller] Initialized polling for {len(devices)} device(s)")


def stop_all_polling():
    """Остановить все задачи опроса (вызывается при shutdown)."""
    for device_id in list(_poll_tasks.keys()):
        stop_polling(device_id)
    print("[Poller] All polling tasks stopped")
