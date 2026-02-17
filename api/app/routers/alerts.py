"""
Роутер /alerts — управление уведомлениями и тревогами.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/", response_model=List[schemas.AlertOut])
def get_alerts(
    unacknowledged_only: bool = Query(default=False),
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    """Получить список алертов (по умолчанию последние 50)."""
    q = db.query(models.Alert)
    if unacknowledged_only:
        q = q.filter(models.Alert.acknowledged == False)
    return q.order_by(models.Alert.created_at.desc()).limit(limit).all()


@router.post("/{alert_id}/acknowledge", response_model=schemas.AlertOut)
def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)):
    """Отметить алерт как прочитанный."""
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.acknowledged = True
    db.commit()
    db.refresh(alert)
    return alert


@router.post("/acknowledge-all", response_model=dict)
def acknowledge_all(db: Session = Depends(get_db)):
    """Отметить все алерты как прочитанные."""
    count = db.query(models.Alert).filter(models.Alert.acknowledged == False).update(
        {"acknowledged": True}
    )
    db.commit()
    return {"acknowledged": count}


@router.get("/count", response_model=dict)
def get_alert_counts(db: Session = Depends(get_db)):
    """Количество непрочитанных алертов по уровням."""
    from sqlalchemy import func
    rows = (
        db.query(models.Alert.level, func.count(models.Alert.id))
        .filter(models.Alert.acknowledged == False)
        .group_by(models.Alert.level)
        .all()
    )
    result = {level: count for level, count in rows}
    result["total"] = sum(result.values())
    return result
