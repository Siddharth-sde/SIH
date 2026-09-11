from typing import Dict, List
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter(tags=["clusters"])

@router.get("/api/duplicates/clusters")
def get_duplicate_clusters(limit: int = 25, db: Session = Depends(get_db)):
    duplicate_codes = [
        r[0] for r in (
            db.query(models.MaterialMaster.cnmc_code)
            .filter(models.MaterialMaster.cnmc_code != "PENDING_HARMONIZATION")
            .group_by(models.MaterialMaster.cnmc_code)
            .having(func.count(models.MaterialMaster.id) > 1)
            .limit(limit)
            .all()
        )
    ]

    if not duplicate_codes:
        return {"count": 0, "clusters": []}

    members = (
        db.query(models.MaterialMaster)
        .filter(models.MaterialMaster.cnmc_code.in_(duplicate_codes))
        .all()
    )

    cluster_buckets: Dict[str, List[models.MaterialMaster]] = {}
    for m in members:
        cluster_buckets.setdefault(m.cnmc_code, []).append(m)

    clusters = []
    for code, m_list in cluster_buckets.items():
        clusters.append({
            "cnmc": code,
            "canonical_name": m_list[0].standardized_description or m_list[0].description,
            "material_count": len(m_list),
            "total_duplicates": len(m_list),
            "cpses_involved": sorted(list({m.cpse_name for m in m_list})),
            "materials": [
                {
                    "id": m.id,
                    "code": m.material_code,
                    "cpse": m.cpse_name,
                    "description": m.description,
                    "uom": m.uom,
                    "unit_price": m.unit_price,
                    "stock_qty": m.stock_qty
                }
                for m in m_list
            ]
        })

    return {"count": len(clusters), "clusters": clusters}
