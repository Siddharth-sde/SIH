from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter(tags=["audit"])

@router.get("/api/audit")
def get_audit_trail(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(models.AuditLog).order_by(models.AuditLog.id.desc()).limit(limit).all()
    return {"count": len(logs), "logs": logs}
