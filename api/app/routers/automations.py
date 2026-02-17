"""
Роутер /automations — CRUD для правил автоматизации.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/automations", tags=["automations"])


@router.get("/", response_model=List[schemas.AutomationOut])
def get_automations(db: Session = Depends(get_db)):
    return db.query(models.Automation).order_by(models.Automation.id).all()


@router.get("/{automation_id}", response_model=schemas.AutomationOut)
def get_automation(automation_id: int, db: Session = Depends(get_db)):
    auto = db.query(models.Automation).filter(models.Automation.id == automation_id).first()
    if not auto:
        raise HTTPException(status_code=404, detail="Automation not found")
    return auto


@router.post("/", response_model=schemas.AutomationOut, status_code=201)
def create_automation(auto_in: schemas.AutomationCreate, db: Session = Depends(get_db)):
    """Создать правило автоматизации.

    Пример тела запроса:
    {
        "name": "Охлаждение при перегреве",
        "trigger_json": '{"device_id":1,"sensor":"temperature","operator":">","threshold":30}',
        "action_json": '{"type":"gpio","target_id":17,"action":"on"}',
        "cooldown_seconds": 120
    }
    """
    import json
    # Валидация JSON-строк
    try:
        json.loads(auto_in.trigger_json)
        json.loads(auto_in.action_json)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON in trigger/action: {e}")

    auto = models.Automation(**auto_in.model_dump())
    db.add(auto)
    db.commit()
    db.refresh(auto)
    return auto


@router.put("/{automation_id}", response_model=schemas.AutomationOut)
def update_automation(
    automation_id: int,
    auto_in: schemas.AutomationUpdate,
    db: Session = Depends(get_db),
):
    auto = db.query(models.Automation).filter(models.Automation.id == automation_id).first()
    if not auto:
        raise HTTPException(status_code=404, detail="Automation not found")

    update_data = auto_in.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(auto, key, val)

    db.commit()
    db.refresh(auto)
    return auto


@router.delete("/{automation_id}", status_code=204)
def delete_automation(automation_id: int, db: Session = Depends(get_db)):
    auto = db.query(models.Automation).filter(models.Automation.id == automation_id).first()
    if not auto:
        raise HTTPException(status_code=404, detail="Automation not found")
    db.delete(auto)
    db.commit()
