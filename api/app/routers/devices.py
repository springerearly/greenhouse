"""
Роутер /devices — CRUD для ESP8266/ESP32 устройств.
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas
from ..database import get_db
from ..services import device_poller
from ..services.websocket_manager import manager as ws_manager

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("/", response_model=List[schemas.DeviceOut])
def get_all_devices(db: Session = Depends(get_db)):
    """Получить список всех зарегистрированных устройств."""
    return db.query(models.Device).order_by(models.Device.id).all()


@router.get("/{device_id}", response_model=schemas.DeviceWithSensors)
def get_device(device_id: int, db: Session = Depends(get_db)):
    """Получить устройство с последними показаниями всех сенсоров."""
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Последние показания каждого типа сенсора
    subq = (
        db.query(
            models.SensorReading.sensor_type,
            models.SensorReading.value,
            models.SensorReading.unit,
            models.SensorReading.timestamp,
        )
        .filter(models.SensorReading.device_id == device_id)
        .order_by(models.SensorReading.sensor_type, models.SensorReading.timestamp.desc())
        .all()
    )

    seen = set()
    latest: dict = {}
    for row in subq:
        if row.sensor_type not in seen:
            seen.add(row.sensor_type)
            latest[row.sensor_type] = {
                "value": row.value,
                "unit": row.unit,
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            }

    result = schemas.DeviceWithSensors.model_validate(device)
    result.latest_readings = latest
    return result


@router.post("/", response_model=schemas.DeviceOut, status_code=201)
async def create_device(device_in: schemas.DeviceCreate, db: Session = Depends(get_db)):
    """Зарегистрировать новое ESP-устройство."""
    existing = db.query(models.Device).filter(
        models.Device.ip_address == device_in.ip_address
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Device with this IP already exists")

    device = models.Device(**device_in.model_dump())
    db.add(device)
    db.commit()
    db.refresh(device)

    # Запустить опрос
    if device.enabled:
        device_poller.start_polling(device.id)

    await ws_manager.broadcast("devices", "device_added", {
        "device_id": device.id, "name": device.name
    })

    return device


@router.put("/{device_id}", response_model=schemas.DeviceOut)
async def update_device(
    device_id: int, device_in: schemas.DeviceUpdate, db: Session = Depends(get_db)
):
    """Обновить параметры устройства."""
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    update_data = device_in.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(device, key, val)

    db.commit()
    db.refresh(device)

    # Перезапустить polling если статус enabled изменился
    if "enabled" in update_data:
        if device.enabled:
            device_poller.start_polling(device.id)
        else:
            device_poller.stop_polling(device.id)

    return device


@router.delete("/{device_id}", status_code=204)
async def delete_device(device_id: int, db: Session = Depends(get_db)):
    """Удалить устройство и остановить его опрос."""
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    device_poller.stop_polling(device_id)
    db.delete(device)
    db.commit()

    await ws_manager.broadcast("devices", "device_removed", {"device_id": device_id})


@router.post("/{device_id}/poll", response_model=dict)
async def poll_device_now(device_id: int, db: Session = Depends(get_db)):
    """Принудительно опросить устройство прямо сейчас (не ждать интервала)."""
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    data = await device_poller._fetch_device_status(device)
    if data is None:
        raise HTTPException(status_code=503, detail="Device unreachable")

    sensors = data.get("sensors", {})
    if sensors:
        await device_poller._save_readings(device_id, sensors)
        await ws_manager.broadcast("sensors", "update", {
            "device_id": device_id,
            "device_name": device.name,
            "sensors": sensors,
            "actuators": data.get("actuators", {}),
        })

    return {"status": "ok", "data": data}


@router.post("/{device_id}/control")
async def control_device(
    device_id: int,
    command: schemas.DeviceControlCommand,
    db: Session = Depends(get_db),
):
    """
    Отправить команду управления ESP-устройству.
    POST http://{esp_ip}/control с JSON-телом.
    """
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    url = f"http://{device.ip_address}:{device.port}/control"
    payload = command.model_dump(exclude_none=True)
    if command.extra:
        payload.update(command.extra)
        payload.pop("extra", None)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            result = resp.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Device timeout")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Device error: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Device unreachable: {str(e)}")

    # Пуш результата в WS
    await ws_manager.broadcast("devices", "control_result", {
        "device_id": device_id,
        "command": payload,
        "result": result,
    })

    return result


@router.get("/{device_id}/info")
async def get_device_info(device_id: int, db: Session = Depends(get_db)):
    """Получить информацию о прошивке ESP-устройства (GET /info)."""
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    url = f"http://{device.ip_address}:{device.port}/info"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Device unreachable: {str(e)}")
