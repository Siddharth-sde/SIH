import json
import math
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session
from database import get_db
import models
from utils import escape_like_string, token_similarity

router = APIRouter(tags=["materials"])

@router.get("/api/materials/meta")
def get_materials_meta(db: Session = Depends(get_db)):
    """Returns distinct sectors, CPSEs, and statuses currently populated in the catalog."""
    sectors = [r[0] for r in db.query(models.MaterialMaster.sector).distinct().all() if r[0]]
    cpses = [r[0] for r in db.query(models.MaterialMaster.cpse_name).distinct().all() if r[0]]
    statuses = [r[0] for r in db.query(models.MaterialMaster.status).distinct().all() if r[0]]
    total = db.query(models.MaterialMaster).count()
    return {
        "sectors": sorted(sectors),
        "cpses": sorted(cpses),
        "statuses": sorted(statuses),
        "total": total
    }

@router.get("/api/materials")
def get_materials(
    q: Optional[str] = Query(None, description="Search description, code, or CPSE"),
    sector: Optional[str] = Query(None),
    cpse: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=500),
    limit: Optional[int] = Query(None, ge=1, le=500),
    offset: Optional[int] = Query(None, ge=0),
    db: Session = Depends(get_db)
):
    eff_limit = limit if limit is not None else (page_size or 50)
    if offset is not None:
        eff_offset = offset
        eff_page = (offset // eff_limit) + 1
    else:
        eff_page = page or 1
        eff_offset = (eff_page - 1) * eff_limit

    query = db.query(models.MaterialMaster)
    if q:
        safe_q = escape_like_string(q.strip())
        query = query.filter(
            or_(
                models.MaterialMaster.description.ilike(f"%{safe_q}%"),
                models.MaterialMaster.material_code.ilike(f"%{safe_q}%"),
                models.MaterialMaster.cpse_name.ilike(f"%{safe_q}%"),
                models.MaterialMaster.cnmc_code.ilike(f"%{safe_q}%")
            )
        )
    if sector:
        query = query.filter(models.MaterialMaster.sector == sector)
    if cpse:
        query = query.filter(models.MaterialMaster.cpse_name == cpse)
    if status:
        query = query.filter(models.MaterialMaster.status == status)

    total = query.count()
    items = query.offset(eff_offset).limit(eff_limit).all()

    results = []
    for item in items:
        extra = json.loads(item.extra_data) if item.extra_data else {}
        results.append({
            "id": item.id,
            "material_code": item.material_code,
            "description": item.description,
            "cpse_name": item.cpse_name,
            "sector": item.sector,
            "uom": item.uom,
            "unit_price": item.unit_price,
            "stock_qty": item.stock_qty,
            "annual_qty": item.annual_qty,
            "cnmc_code": item.cnmc_code,
            "status": item.status,
            "data_quality_score": extra.get("data_quality_score", 100),
            "extra_attributes": extra
        })

    return {
        "page": eff_page,
        "page_size": eff_limit,
        "limit": eff_limit,
        "offset": eff_offset,
        "total": total,
        "total_pages": math.ceil(total / eff_limit) if total else 0,
        "results": results,
        "items": results
    }

@router.get("/api/match")
def match_materials(material_id: int, compare_id: int, db: Session = Depends(get_db)):
    first = db.query(models.MaterialMaster).filter(models.MaterialMaster.id == material_id).first()
    second = db.query(models.MaterialMaster).filter(models.MaterialMaster.id == compare_id).first()

    if not first or not second:
        raise HTTPException(status_code=404, detail="One or both materials not found")

    score = token_similarity(first.description, second.description)
    if score >= 0.85:
        decision = "DUPLICATE"
    elif score >= 0.65:
        decision = "LIKELY_EQUIVALENT"
    elif score >= 0.45:
        decision = "REVIEW"
    else:
        decision = "DIFFERENT"

    return {
        "material_a": {"id": first.id, "code": first.material_code, "desc": first.description},
        "material_b": {"id": second.id, "code": second.material_code, "desc": second.description},
        "similarity_score": score,
        "decision": decision
    }

@router.post("/api/materials/{material_id}/action")
def update_material_status(
    material_id: int,
    action: str = Query(..., pattern="^(APPROVE|REJECT)$"),
    performed_by: str = Query("dashboard_user"),
    notes: str = Query(""),
    db: Session = Depends(get_db)
):
    mat = db.query(models.MaterialMaster).filter(models.MaterialMaster.id == material_id).first()
    if not mat:
        raise HTTPException(status_code=404, detail="Material record not found")

    mat.status = "APPROVED" if action == "APPROVE" else "REJECTED"
    log = models.AuditLog(
        material_code=mat.material_code,
        action=action,
        performed_by=performed_by,
        notes=notes or f"Material {mat.material_code} was {action.lower()}d."
    )
    db.add(log)
    db.commit()

    return {
        "success": True,
        "material_id": material_id,
        "action": action,
        "status": mat.status,
        "message": f"Material {mat.material_code} was successfully {action.lower()}d."
    }
