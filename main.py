from fastapi import FastAPI, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import engine, Base, get_db
import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="National Unified Material Master Platform")

@app.get("/")
def home():
    return {"status": "Material Harmonization Engine Active"}

# 1. Search materials across CPSEs (with pagination)
@app.get("/api/materials")
def search_materials(
    q: str = Query(None, description="Search description or code"),
    sector: str = Query(None, description="Filter by sector, e.g. 'Oil & Gas'"),
    cpse: str = Query(None, description="Filter by CPSE, e.g. 'ONGC'"),
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    query = db.query(models.CPSEMaterial)
    if q:
        query = query.filter(models.CPSEMaterial.material_description.ilike(f"%{q}%"))
    if sector:
        query = query.filter(models.CPSEMaterial.sector == sector)
    if cpse:
        query = query.filter(models.CPSEMaterial.cpse_name == cpse)
        
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return {"total": total, "items": items}

# 2. View duplicate clusters across CPSEs sharing the same CNMC
@app.get("/api/duplicates/clusters")
def get_duplicate_clusters(
    cnmc: str = Query(None, description="Specific CNMC e.g. NMC-OG-00655"),
    limit: int = 20,
    db: Session = Depends(get_db)
):
    if cnmc:
        materials = db.query(models.CPSEMaterial).filter(models.CPSEMaterial.cnmc_code == cnmc).all()
        return {"cnmc": cnmc, "count": len(materials), "materials": materials}

    # Find CNMC codes shared across 2 or more distinct CPSEs
    subquery = (
        db.query(models.CPSEMaterial.cnmc_code)
        .group_by(models.CPSEMaterial.cnmc_code)
        .having(func.count(models.CPSEMaterial.id) > 1)
        .limit(limit)
        .all()
    )
    duplicate_cnmcs = [row[0] for row in subquery]
    
    results = []
    for code in duplicate_cnmcs:
        cluster = db.query(models.CPSEMaterial).filter(models.CPSEMaterial.cnmc_code == code).all()
        results.append({
            "cnmc": code,
            "standardized_description": cluster[0].standardized_description,
            "sector": cluster[0].sector,
            "duplicate_count": len(cluster),
            "affected_cpses": list(set([m.cpse_name for m in cluster])),
            "items": cluster
        })
    return results

# 3. High-impact KPI numbers for the frontend dashboard
@app.get("/api/analytics/kpis")
def get_analytics_kpis(db: Session = Depends(get_db)):
    total_materials = db.query(models.CPSEMaterial).count()
    unique_cnmcs = db.query(func.count(func.distinct(models.CPSEMaterial.cnmc_code))).scalar()
    duplicates_detected = total_materials - unique_cnmcs

    # Calculate total annual procurement spend represented in catalog
    total_spend = db.query(func.sum(models.CPSEMaterial.unit_price * models.CPSEMaterial.annual_consumption)).scalar() or 0.0

    # Theoretical 8% savings via common procurement / demand aggregation
    potential_savings_inr = round(total_spend * 0.08, 2)

    return {
        "total_materials_ingested": total_materials,
        "unique_national_materials": unique_cnmcs,
        "duplicates_rationalized": duplicates_detected,
        "rationalization_percentage": f"{(duplicates_detected / total_materials * 100):.1f}%",
        "estimated_procurement_savings_inr": f"₹{potential_savings_inr:,.2f}"
    }