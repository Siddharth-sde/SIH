from fastapi import FastAPI, Depends, UploadFile, File, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from database import engine, Base, get_db
import models
import pandas as pd
import json
import io
import os

Base.metadata.create_all(bind=engine)

app = FastAPI(title="National Unified Material Master Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Common aliases so it recognizes columns from ANY dataset
ALIASES = {
    "material_code": ["material_code", "source_material_code", "legacy_material_code", "matnr", "item_code", "code"],
    "description": ["material_description", "description", "maktx", "item_desc", "item_name"],
    "cpse_name": ["cpse_name", "cpse_id", "cpse", "company", "enterprise", "org"],
    "sector": ["sector", "industry", "domain"],
    "uom": ["uom", "meins", "unit"],
    "unit_price": ["unit_price_inr", "unit_price", "price", "rate", "cost"],
    "stock_qty": ["current_stock_qty", "stock_qty", "stock", "quantity"],
    "annual_qty": ["annual_procurement_qty", "annual_consumption", "annual_qty", "procurement_qty"],
    "cnmc_code": ["common_national_material_code", "cnmc_code", "true_cluster_id", "cnmc"]
}

def parse_and_store_dataframe(df: pd.DataFrame, db: Session, filename: str = "upload"):
    """Universally ingests any DataFrame into the database without requiring schema changes."""
    col_lookup = {str(col).strip().lower().replace(" ", "_"): col for col in df.columns}
    
    def get_val(row, target_key, default=None):
        for alias in ALIASES.get(target_key, []):
            if alias in col_lookup:
                val = row[col_lookup[alias]]
                if pd.notna(val) and str(val).strip() != "":
                    return val
        return default

    # Identify core columns mapped
    matched_orig_cols = set()
    for key in ALIASES:
        for alias in ALIASES[key]:
            if alias in col_lookup:
                matched_orig_cols.add(col_lookup[alias])

    records = []
    for idx, row in df.iterrows():
        raw_code = str(get_val(row, "material_code", f"ITEM-{idx+1}")).strip()
        raw_desc = str(get_val(row, "description", "UNNAMED ITEM")).strip()
        cpse = str(get_val(row, "cpse_name", "CPSE_GENERAL")).strip()
        sector = str(get_val(row, "sector", "General")).strip()
        uom = str(get_val(row, "uom", "NOS")).strip().upper()
        
        try:
            price = float(get_val(row, "unit_price", 0.0))
        except (ValueError, TypeError):
            price = 0.0

        try:
            stock = int(float(get_val(row, "stock_qty", 0)))
        except (ValueError, TypeError):
            stock = 0

        try:
            annual = int(float(get_val(row, "annual_qty", 0)))
        except (ValueError, TypeError):
            annual = 0

        raw_cnmc = get_val(row, "cnmc_code")
        if raw_cnmc:
            cnmc = f"NMC-{str(raw_cnmc).replace('CLUSTER_', '').strip()}"
        else:
            cnmc = "PENDING_HARMONIZATION"

        # Capture EVERYTHING ELSE into extra_data as JSON
        extra = {}
        for c in df.columns:
            if c not in matched_orig_cols and pd.notna(row[c]):
                extra[str(c)] = str(row[c])

        record = models.MaterialMaster(
            material_code=raw_code,
            description=raw_desc,
            cpse_name=cpse,
            sector=sector,
            uom=uom,
            unit_price=price,
            stock_qty=stock,
            annual_qty=annual,
            cnmc_code=cnmc,
            standardized_description=raw_desc.upper(),
            status="PENDING_REVIEW" if extra.get("human_review_flag") == "True" else "ACTIVE",
            extra_data=json.dumps(extra)
        )
        records.append(record)

    db.bulk_save_objects(records)
    db.commit()
    return len(records)


# ---------------- API ENDPOINTS ----------------

@app.get("/")
def home():
    return {"status": "Universal Material Harmonization Platform Live"}

# 1. UNIVERSAL UPLOAD: Accepts ANY CSV or Excel file without failing
@app.post("/api/upload")
async def upload_any_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    filename = file.filename.lower()
    
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.StringIO(contents.decode("utf-8", errors="ignore")))
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(status_code=400, detail="Only CSV or Excel files are accepted.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"File parsing error: {str(e)}")

    count = parse_and_store_dataframe(df, db, file.filename)
    return {"message": f"Successfully ingested {count} records from {file.filename} into universal storage."}

# 2. LOCAL SYNC: One-click sync from any file in your project folder
@app.post("/api/load-local-file")
def load_local(file_name: str = Query(..., description="File name in current folder, e.g. material_master_input.csv"), db: Session = Depends(get_db)):
    if not os.path.exists(file_name):
        raise HTTPException(status_code=404, detail=f"File '{file_name}' not found in folder.")
    
    df = pd.read_csv(file_name) if file_name.endswith(".csv") else pd.read_excel(file_name)
    count = parse_and_store_dataframe(df, db, file_name)
    return {"message": f"Loaded {count} records from local file {file_name}"}

# 3. SEARCH & BROWSE: Search across all materials
@app.get("/api/materials")
def get_materials(
    q: str = Query(None, description="Search description, code, or cpse"),
    sector: str = Query(None),
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    query = db.query(models.MaterialMaster)
    if q:
        query = query.filter(
            or_(
                models.MaterialMaster.description.ilike(f"%{q}%"),
                models.MaterialMaster.material_code.ilike(f"%{q}%"),
                models.MaterialMaster.cpse_name.ilike(f"%{q}%")
            )
        )
    if sector:
        query = query.filter(models.MaterialMaster.sector == sector)
        
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    
    # Parse extra_data JSON so frontend sees full details
    results = []
    for item in items:
        item_dict = {
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
            "extra_attributes": json.loads(item.extra_data) if item.extra_data else {}
        }
        results.append(item_dict)

    return {"total": total, "items": results}

# 4. DUPLICATE CLUSTERS: Automatically groups duplicates across CPSEs
@app.get("/api/duplicates/clusters")
def get_duplicate_clusters(limit: int = 25, db: Session = Depends(get_db)):
    subquery = (
        db.query(models.MaterialMaster.cnmc_code)
        .filter(models.MaterialMaster.cnmc_code != "PENDING_HARMONIZATION")
        .group_by(models.MaterialMaster.cnmc_code)
        .having(func.count(models.MaterialMaster.id) > 1)
        .limit(limit)
        .all()
    )
    duplicate_codes = [r[0] for r in subquery]
    
    clusters = []
    for code in duplicate_codes:
        members = db.query(models.MaterialMaster).filter(models.MaterialMaster.cnmc_code == code).all()
        clusters.append({
            "cnmc": code,
            "total_duplicates": len(members),
            "cpses_involved": list(set(m.cpse_name for m in members)),
            "materials": [
                {
                    "code": m.material_code,
                    "cpse": m.cpse_name,
                    "description": m.description,
                    "uom": m.uom,
                    "unit_price": m.unit_price,
                    "stock_qty": m.stock_qty
                }
                for m in members
            ]
        })
    return clusters

# 5. PITCH KPIS: Real calculations for ROI & presentation
@app.get("/api/analytics/kpis")
def get_kpis(db: Session = Depends(get_db)):
    materials = db.query(models.MaterialMaster).all()
    total_count = len(materials)
    if total_count == 0:
        return {"message": "No data loaded yet."}

    total_stock_value = sum(m.unit_price * m.stock_qty for m in materials)
    total_procurement_spend = sum(m.unit_price * m.annual_qty for m in materials)

    unique_cnmcs = db.query(func.count(func.distinct(models.MaterialMaster.cnmc_code))).scalar() or 1
    duplicates_detected = max(0, total_count - unique_cnmcs)

    return {
        "summary": {
            "total_materials": total_count,
            "unique_national_codes": unique_cnmcs,
            "duplicates_eliminated": duplicates_detected,
            "rationalization_percentage": f"{round((duplicates_detected / total_count) * 100, 1)}%"
        },
        "financial_impact_crores": {
            "locked_inventory_value": f"₹{round(total_stock_value / 1e7, 2)} Cr",
            "annual_procurement_spend": f"₹{round(total_procurement_spend / 1e7, 2)} Cr",
            "demand_aggregation_savings": f"₹{round((total_procurement_spend * 0.10) / 1e7, 2)} Cr (10% bulk aggregation)",
            "inventory_holding_savings": f"₹{round((total_stock_value * 0.15) / 1e7, 2)} Cr (15% holding reduction)"
        }
    }

# 6. APPROVE / REJECT: Human-in-the-loop governance
@app.post("/api/materials/{material_id}/action")
def update_status(material_id: int, action: str = Query(..., enum=["APPROVE", "REJECT"]), db: Session = Depends(get_db)):
    mat = db.query(models.MaterialMaster).filter(models.MaterialMaster.id == material_id).first()
    if not mat:
        raise HTTPException(status_code=404, detail="Material not found")
    
    mat.status = "APPROVED" if action == "APPROVE" else "REJECTED"
    
    # Write to audit trail
    log = models.AuditLog(
        material_code=mat.material_code,
        action=action,
        notes=f"Material {mat.material_code} ({mat.description}) was {action.lower()}d."
    )
    db.add(log)
    db.commit()
    return {"message": f"Material {mat.material_code} marked as {mat.status}", "status": mat.status}