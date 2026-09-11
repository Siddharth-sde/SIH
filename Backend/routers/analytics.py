from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter(tags=["analytics"])

# Enterprise Standard Constants (MoF / DPE Guideline for Public Sector Undertakings)
DPE_ANNUAL_INVENTORY_HOLDING_RATE = 0.20  # 20% p.a. (12% capital + 5% storage/insurance + 3% obsolescence)

@router.get("/api/analytics/kpis")
def get_kpis(db: Session = Depends(get_db)):
    total_materials = db.query(func.count(models.MaterialMaster.id)).scalar() or 0
    if total_materials == 0:
        return {
            "message": "No materials loaded in database",
            "error": "No materials loaded in database",
            "summary": {
                "total_materials": 0,
                "unique_national_codes": 0,
                "duplicates_eliminated": 0,
                "rationalization_percentage": "0.0%"
            },
            "financial_impact_crores": {}
        }

    harmonized_materials = db.query(func.count(models.MaterialMaster.id)).filter(
        models.MaterialMaster.cnmc_code != "PENDING_HARMONIZATION"
    ).scalar() or 0

    unique_cnmcs = db.query(func.count(func.distinct(models.MaterialMaster.cnmc_code))).filter(
        models.MaterialMaster.cnmc_code != "PENDING_HARMONIZATION"
    ).scalar() or 0

    duplicates_detected = max(0, harmonized_materials - unique_cnmcs) if unique_cnmcs > 0 else 0

    stats = db.query(
        func.coalesce(func.sum(models.MaterialMaster.unit_price * models.MaterialMaster.stock_qty), 0.0).label("stock_val"),
        func.coalesce(func.sum(models.MaterialMaster.unit_price * models.MaterialMaster.annual_qty), 0.0).label("spend_val")
    ).first()

    total_stock_value = float(stats.stock_val or 0.0)
    total_procurement_spend = float(stats.spend_val or 0.0)

    # Empirical Price Arbitrage (PDI): sum(Q_i * (P_i - P_min)) across verified multi-variant clusters
    cluster_savings_inr = 0.0
    duplicate_clusters = (
        db.query(models.MaterialMaster.cnmc_code)
        .filter(models.MaterialMaster.cnmc_code != "PENDING_HARMONIZATION")
        .group_by(models.MaterialMaster.cnmc_code)
        .having(func.count(models.MaterialMaster.id) > 1)
        .all()
    )
    dup_cnmc_list = [r[0] for r in duplicate_clusters]
    if dup_cnmc_list:
        members = (
            db.query(
                models.MaterialMaster.cnmc_code,
                models.MaterialMaster.unit_price,
                models.MaterialMaster.annual_qty
            )
            .filter(models.MaterialMaster.cnmc_code.in_(dup_cnmc_list))
            .all()
        )
        from collections import defaultdict
        cluster_buckets = defaultdict(list)
        for cnmc, price, qty in members:
            p = float(price or 0.0)
            q = int(qty or 0)
            if p > 0:
                cluster_buckets[cnmc].append((p, q))

        for cnmc, items in cluster_buckets.items():
            if len(items) > 1:
                min_p = min(p for p, q in items)
                cluster_savings_inr += sum(q * (p - min_p) for p, q in items)

    dpe_holding_savings_inr = total_stock_value * DPE_ANNUAL_INVENTORY_HOLDING_RATE
    rat_pct = round((duplicates_detected / harmonized_materials) * 100, 2) if harmonized_materials > 0 else 0.0

    return {
        "summary": {
            "total_materials": total_materials,
            "unique_national_codes": unique_cnmcs,
            "duplicates_eliminated": duplicates_detected,
            "rationalization_percentage": f"{rat_pct}%"
        },
        "financial_impact_crores": {
            "locked_inventory_value": f"₹{round(total_stock_value / 1e7, 2)} Cr",
            "annual_procurement_spend": f"₹{round(total_procurement_spend / 1e7, 2)} Cr",
            "demand_aggregation_savings": f"₹{round(cluster_savings_inr / 1e7, 2)} Cr (Empirical PDI Arbitrage)",
            "inventory_holding_savings": f"₹{round(dpe_holding_savings_inr / 1e7, 2)} Cr ({int(DPE_ANNUAL_INVENTORY_HOLDING_RATE * 100)}% DPE Holding Cost)"
        },
        "total_materials": total_materials,
        "unique_national_codes": unique_cnmcs,
        "duplicate_materials": duplicates_detected,
        "duplicate_percentage": rat_pct,
        "inventory_value_inr": round(total_stock_value, 2),
        "annual_procurement_value_inr": round(total_procurement_spend, 2),
        "potential_procurement_savings_inr": round(cluster_savings_inr, 2),
        "potential_inventory_reduction_inr": round(dpe_holding_savings_inr, 2),
        "empirical_arbitrage_savings_inr": round(cluster_savings_inr, 2),
        "inventory_holding_cost_inr": round(dpe_holding_savings_inr, 2),
        "procurement_savings_rate": "Empirical PDI Arbitrage",
        "inventory_reduction_rate": f"{int(DPE_ANNUAL_INVENTORY_HOLDING_RATE * 100)}% DPE Standard"
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
    cluster_arbitrage_map = {}

    if top_cnmcs:
        cpse_records = (
            db.query(
                models.MaterialMaster.cnmc_code,
                models.MaterialMaster.cpse_name,
                models.MaterialMaster.unit_price,
                models.MaterialMaster.annual_qty
            )
            .filter(models.MaterialMaster.cnmc_code.in_(top_cnmcs))
            .all()
        )
        from collections import defaultdict
        cluster_items = defaultdict(list)
        for cnmc, cpse, price, qty in cpse_records:
            cpse_map.setdefault(cnmc, set()).add(cpse)
            p = float(price or 0.0)
            q = int(qty or 0)
            if p > 0:
                cluster_items[cnmc].append((p, q))

        for cnmc, items in cluster_items.items():
            if len(items) > 1:
                min_p = min(p for p, q in items)
                cluster_arbitrage_map[cnmc] = sum(q * (p - min_p) for p, q in items)

    opportunities = []
    for r in subquery:
        inv = float(r.inv_val or 0.0)
        proc = float(r.proc_val or 0.0)
        cluster_arbitrage = cluster_arbitrage_map.get(r.cnmc_code, 0.0)
        holding_savings = inv * DPE_ANNUAL_INVENTORY_HOLDING_RATE
        opportunities.append({
            "cnmc_code": r.cnmc_code,
            "canonical_name": r.canonical_name,
            "material_count": r.material_count,
            "cpses_involved": sorted(list(cpse_map.get(r.cnmc_code, set()))),
            "inventory_value_inr": round(inv, 2),
            "procurement_value_inr": round(proc, 2),
            "potential_savings_inr": round(cluster_arbitrage, 2),
            "working_capital_freed_inr": round(holding_savings, 2)
        })

    return {"count": len(opportunities), "opportunities": opportunities}
