"""
Роутер /sensors — история и агрегация показаний датчиков.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from typing import List, Optional
from datetime import datetime, timedelta, timezone

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/sensors", tags=["sensors"])


@router.get("/latest", response_model=List[schemas.SensorReadingOut])
def get_latest_readings(
    device_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Последнее показание каждого типа сенсора.
    Если device_id не указан — по всем устройствам.
    """
    subq = (
        db.query(
            models.SensorReading.device_id,
            models.SensorReading.sensor_type,
            sqlfunc.max(models.SensorReading.timestamp).label("max_ts"),
        )
        .group_by(models.SensorReading.device_id, models.SensorReading.sensor_type)
        .subquery()
    )

    q = db.query(models.SensorReading).join(
        subq,
        (models.SensorReading.device_id == subq.c.device_id)
        & (models.SensorReading.sensor_type == subq.c.sensor_type)
        & (models.SensorReading.timestamp == subq.c.max_ts),
    )

    if device_id is not None:
        q = q.filter(models.SensorReading.device_id == device_id)

    return q.all()


@router.get("/history", response_model=schemas.SensorHistory)
def get_sensor_history(
    device_id: int,
    sensor_type: str,
    hours: int = Query(default=24, ge=1, le=720),
    db: Session = Depends(get_db),
):
    """
    История показаний конкретного сенсора за последние N часов.
    Возвращает список точек {timestamp, value}.
    """
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    readings = (
        db.query(models.SensorReading)
        .filter(
            models.SensorReading.device_id == device_id,
            models.SensorReading.sensor_type == sensor_type,
            models.SensorReading.timestamp >= since,
        )
        .order_by(models.SensorReading.timestamp.asc())
        .all()
    )

    unit = readings[-1].unit if readings else None

    data = [
        schemas.SensorHistoryPoint(
            timestamp=r.timestamp,
            value=r.value,
        )
        for r in readings
    ]

    return schemas.SensorHistory(
        device_id=device_id,
        sensor_type=sensor_type,
        unit=unit,
        data=data,
    )


@router.get("/stats")
def get_sensor_stats(
    device_id: int,
    sensor_type: str,
    hours: int = Query(default=24, ge=1, le=720),
    db: Session = Depends(get_db),
):
    """
    Статистика (min, max, avg) за последние N часов.
    """
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    result = db.query(
        sqlfunc.min(models.SensorReading.value).label("min_val"),
        sqlfunc.max(models.SensorReading.value).label("max_val"),
        sqlfunc.avg(models.SensorReading.value).label("avg_val"),
        sqlfunc.count(models.SensorReading.id).label("count"),
    ).filter(
        models.SensorReading.device_id == device_id,
        models.SensorReading.sensor_type == sensor_type,
        models.SensorReading.timestamp >= since,
    ).first()

    return {
        "device_id": device_id,
        "sensor_type": sensor_type,
        "hours": hours,
        "min": round(result.min_val, 2) if result.min_val is not None else None,
        "max": round(result.max_val, 2) if result.max_val is not None else None,
        "avg": round(result.avg_val, 2) if result.avg_val is not None else None,
        "count": result.count,
    }
