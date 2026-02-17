"""
Automation Engine — движок правил автоматизации.

Правило: если sensor X устройства Y > threshold -> выполнить действие Z.
Проверяется каждый раз при получении новых показаний сенсоров.

Пример trigger_json:
    {"device_id": 1, "sensor": "temperature", "operator": ">", "threshold": 30}

Пример action_json:
    {"type": "gpio", "target_id": 17, "action": "on"}
    {"type": "device_control", "target_id": 2, "command": {"relay1": 1}}
"""

import json
import asyncio
from datetime import datetime, timezone

from ..database import SessionLocal
from .. import models
from .websocket_manager import manager as ws_manager


OPERATORS = {
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def _evaluate_trigger(trigger: dict, sensors: dict, device_id: int) -> bool:
    """Проверить условие срабатывания."""
    if trigger.get("device_id") != device_id:
        return False

    sensor_key = trigger.get("sensor")
    operator = trigger.get("operator", ">")
    threshold = trigger.get("threshold")

    if sensor_key not in sensors:
        return False

    payload = sensors[sensor_key]
    current_value = payload.get("value") if isinstance(payload, dict) else payload

    op_fn = OPERATORS.get(operator)
    if op_fn is None or current_value is None or threshold is None:
        return False

    return op_fn(float(current_value), float(threshold))


async def _execute_action(action: dict):
    """Выполнить действие автоматизации."""
    action_type = action.get("type")

    if action_type == "gpio":
        # Управление GPIO пином Raspberry Pi
        target_id = action.get("target_id")
        cmd = action.get("action", "on")
        try:
            # Импортируем роутер GPIO для доступа к devices dict
            from ..routers.gpio import devices as gpio_devices, DigitalOutputDevice, ON_PI
            device = gpio_devices.get(target_id)
            if device and isinstance(device, DigitalOutputDevice):
                if cmd == "on":
                    device.on()
                elif cmd == "off":
                    device.off()
                print(f"[Automation] GPIO {target_id} -> {cmd}")
                await ws_manager.broadcast("gpio", "auto_action", {
                    "pin": target_id, "action": cmd
                })
        except Exception as e:
            print(f"[Automation] GPIO action error: {e}")

    elif action_type == "device_control":
        # Отправить команду ESP-устройству
        import httpx
        target_id = action.get("target_id")
        command = action.get("command", {})
        with SessionLocal() as db:
            dev = db.query(models.Device).filter(models.Device.id == target_id).first()
            if dev:
                url = f"http://{dev.ip_address}:{dev.port}/control"
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        await client.post(url, json=command)
                    print(f"[Automation] Device {target_id} control: {command}")
                except Exception as e:
                    print(f"[Automation] Device control error: {e}")


async def check_automations(device_id: int, sensors: dict):
    """
    Вызывается Device Poller'ом при каждом новом показании.
    Проверяет все активные правила и выполняет подходящие.
    """
    with SessionLocal() as db:
        automations = db.query(models.Automation).filter(
            models.Automation.enabled == True
        ).all()

        now = datetime.now(timezone.utc)

        for auto in automations:
            try:
                trigger = json.loads(auto.trigger_json)
                action = json.loads(auto.action_json)
            except json.JSONDecodeError:
                continue

            if not _evaluate_trigger(trigger, sensors, device_id):
                continue

            # Проверка cooldown
            if auto.last_triggered:
                elapsed = (now - auto.last_triggered.replace(tzinfo=timezone.utc)).total_seconds()
                if elapsed < auto.cooldown_seconds:
                    continue

            # Выполняем действие
            await _execute_action(action)

            # Обновляем last_triggered
            auto.last_triggered = now
            db.commit()

            # Уведомляем через WS
            await ws_manager.broadcast("alerts", "automation_triggered", {
                "automation_id": auto.id,
                "automation_name": auto.name,
                "device_id": device_id,
                "trigger": trigger,
                "action": action,
            })
