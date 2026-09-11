from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from database import get_db
import models
from utils import PROCUREMENT_SAVINGS_RATE, INVENTORY_REDUCTION_RATE

router = APIRouter(tags=["analytics"])

@router.get("/api/analytics/kpis")
def get_kpis(db: Session = Depends(get_db)):
    stats = db.query(
        func.count(models.MaterialMaster.id).label("total"),
        func.count(func.distinct(models.MaterialMaster.cnmc_code)).label("unique_cnmcs"),
        func.coalesce(func.sum(models.MaterialMaster.unit_price * models.MaterialMaster.stock_qty), 0.0).label("stock_val"),
        func.coalesce(func.sum(models.MaterialMaster.unit_price * models.MaterialMaster.annual_qty), 0.0).label("spend_val")
    ).first()

    total_materials = stats.total or 0
    if total_materials == 0:
        return {"message": "No materials loaded in database", "error": "No materials loaded in database"}

    unique_cnmcs = stats.unique_cnmcs or 0
    duplicates_detected = max(0, total_materials - unique_cnmcs)
    total_stock_value = float(stats.stock_val)
    total_procurement_spend = float(stats.spend_val)

    stock_cr = total_stock_value / 1e7
    spend_cr = total_procurement_spend / 1e7
    proc_sav_cr = (total_procurement_spend * PROCUREMENT_SAVINGS_RATE) / 1e7
    inv_sav_cr = (total_stock_value * INVENTORY_REDUCTION_RATE) / 1e7
    rat_pct = round((duplicates_detected / total_materials) * 100, 2) if total_materials > 0 else 0.0

    return {
        "summary": {
            "total_materials": total_materials,
            "unique_national_codes": unique_cnmcs,
            "duplicates_eliminated": duplicates_detected,
            "rationalization_percentage": f"{rat_pct}%"
        },
        "financial_impact_crores": {
            "locked_inventory_value": f"₹{stock_cr:.2f} Cr" if stock_cr < 1000 else f"₹{(stock_cr/1000):.1f}K Cr",
            "annual_procurement_spend": f"₹{spend_cr:.2f} Cr" if spend_cr < 1000 else f"₹{(spend_cr/1000):.1f}K Cr",
            "demand_aggregation_savings": f"₹{proc_sav_cr:.2f} Cr",
            "inventory_holding_savings": f"₹{inv_sav_cr:.2f} Cr"
        },
        "total_materials": total_materials,
        "unique_national_codes": unique_cnmcs,
        "duplicate_materials": duplicates_detected,
        "duplicate_percentage": rat_pct,
        "inventory_value_inr": round(total_stock_value, 2),
        "annual_procurement_value_inr": round(total_procurement_spend, 2),
        "potential_procurement_savings_inr": round(total_procurement_spend * PROCUREMENT_SAVINGS_RATE, 2),
        "potential_inventory_reduction_inr": round(total_stock_value * INVENTORY_REDUCTION_RATE, 2),
        "procurement_savings_rate": f"{int(PROCUREMENT_SAVINGS_RATE * 100)}%",
        "inventory_reduction_rate": f"{int(INVENTORY_REDUCTION_RATE * 100)}%"
    }

@router.get("/api/analytics/opportunities")
def get_ranked_opportunities(limit: int = 15, db: Session = Depends(get_db)):
    subquery = (
        db.query(
            models.MaterialMaster.cnmc_code,
            func.min(models.MaterialMaster.standardized_description).label("canonical_name"),
            func.count(models.MaterialMaster.id).label("material_count"),
            func.sum(models.MaterialMaster.unit_price * models.MaterialMaster.stock_qty).label("inv_val"),
            func.sum(models.MaterialMaster.unit_price * models.MaterialMaster.annual_qty).label("proc_val")
        )
        .filter(models.MaterialMaster.cnmc_code != "PENDING_HARMONIZATION")
        .group_by(models.MaterialMaster.cnmc_code)
        .having(func.count(models.MaterialMaster.id) > 1)
        .order_by(text("inv_val DESC"))
        .limit(limit)
        .all()
    )

    top_cnmcs = [row.cnmc_code for row in subquery]
    cpse_map = {}
    if top_cnmcs:
        cpse_records = (
            db.query(models.MaterialMaster.cnmc_code, models.MaterialMaster.cpse_name)
            .filter(models.MaterialMaster.cnmc_code.in_(top_cnmcs))
            .distinct()
            .all()
        )
        for cnmc, cpse in cpse_records:
            cpse_map.setdefault(cnmc, []).append(cpse)

    opportunities = []
    for r in subquery:
        inv = float(r.inv_val or 0.0)
        proc = float(r.proc_val or 0.0)
        opportunities.append({
            "cnmc_code": r.cnmc_code,
            "canonical_name": r.canonical_name,
            "material_count": r.material_count,
            "cpses_involved": cpse_map.get(r.cnmc_code, []),
            "inventory_value_inr": round(inv, 2),
            "procurement_value_inr": round(proc, 2),
            "potential_savings_inr": round(proc * PROCUREMENT_SAVINGS_RATE, 2),
            "working_capital_freed_inr": round(inv * INVENTORY_REDUCTION_RATE, 2)
        })

    return {"count": len(opportunities), "opportunities": opportunities}
