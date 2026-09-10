import os
import io
import json
import math
import re
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, Query, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, text
import pandas as pd
import httpx

from database import engine, Base, get_db
import models

try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# ============================================================
# APP CONFIGURATION & DATABASE SETUP
# ============================================================

Base.metadata.create_all(bind=engine)

# Enable WAL mode for high-concurrency database operations
with engine.connect() as conn:
    conn.execute(text("PRAGMA journal_mode=WAL;"))
    conn.commit()

app = FastAPI(
    title="National Unified Material Master Harmonization Platform",
    description="Consolidated API Gateway serving Frontend, Database, and ML microservices.",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://127.0.0.1:8001")
PROCUREMENT_SAVINGS_RATE = 0.10
INVENTORY_REDUCTION_RATE = 0.15

# ============================================================
# UTILITIES: Security, Text Normalization & Data Quality
# ============================================================

def escape_like_string(text_val: str) -> str:
    """Prevents LIKE wildcard exploitation in search queries."""
    return text_val.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

def normalize_text(value: str) -> str:
    if not value or pd.isna(value):
        return ""
    text_val = str(value).lower().replace("×", "x")
    text_val = re.sub(r"[^a-z0-9\s./%-]", " ", text_val)
    return " ".join(text_val.split())

def calculate_quality_score(code, desc, uom, sector, price, stock, annual_qty) -> float:
    score = sum([
        bool(code),
        bool(desc),
        bool(uom),
        bool(sector),
        float(price or 0) > 0,
        float(stock or 0) >= 0,
        float(annual_qty or 0) >= 0
    ])
    return round((score / 7.0) * 100, 1)

def token_similarity(text_a: str, text_b: str) -> float:
    a = set(normalize_text(text_a).split())
    b = set(normalize_text(text_b).split())
    if not a or not b:
        return 0.0
    return round(len(a.intersection(b)) / len(a.union(b)), 4)

def extract_tables_from_pdf(file_bytes: bytes) -> pd.DataFrame:
    if not PDF_SUPPORT:
        raise HTTPException(status_code=500, detail="pdfplumber library is not installed.")
    
    all_rows = []
    headers = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 2:
                    continue
                if not headers:
                    headers = [str(c).strip() if c else f"col_{i}" for i, c in enumerate(table[0])]
                    data_rows = table[1:]
                else:
                    data_rows = table

                for row in data_rows:
                    cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
                    if len(cleaned_row) < len(headers):
                        cleaned_row.extend([""] * (len(headers) - len(cleaned_row)))
                    all_rows.append(cleaned_row[:len(headers)])

    if not headers or not all_rows:
        return pd.DataFrame()
    return pd.DataFrame(all_rows, columns=headers).dropna(how="all")

# ============================================================
# UNIVERSAL INGESTION ENGINE
# ============================================================

ALIASES = {
    "material_code": ["source_material_code", "material_code", "legacy_material_code", "matnr", "item_code"],
    "description": ["material_description", "description", "maktx", "item_desc", "item_name"],
    "cpse_name": ["cpse_id", "cpse_name", "cpse", "company", "enterprise"],
    "sector": ["sector", "industry", "domain"],
    "uom": ["uom", "meins", "unit"],
    "unit_price": ["unit_price_inr", "unit_price", "price", "rate", "cost"],
    "stock_qty": ["current_stock_qty", "stock_qty", "stock", "inventory"],
    "annual_qty": ["annual_procurement_qty", "annual_consumption", "annual_qty"],
    "cnmc_code": ["cnmc_code", "common_national_material_code", "true_cluster_id", "cluster_id"]
}

def parse_and_store_dataframe(df: pd.DataFrame, db: Session):
    col_lookup = {str(col).strip().lower().replace(" ", "_"): col for col in df.columns}
    
    def get_val(row, target_key, default=None):
        for alias in ALIASES.get(target_key, []):
            if alias in col_lookup:
                val = row[col_lookup[alias]]
                if pd.notna(val) and str(val).strip() != "":
                    return val
        return default

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
        cnmc = f"NMC-{str(raw_cnmc).replace('CLUSTER_', '').strip()}" if raw_cnmc else "PENDING_HARMONIZATION"

        extra = {}
        for c in df.columns:
            if c not in matched_orig_cols and pd.notna(row[c]):
                extra[str(c)] = str(row[c])

        q_score = calculate_quality_score(raw_code, raw_desc, uom, sector, price, stock, annual)

        records.append(models.MaterialMaster(
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
            extra_data=json.dumps({**extra, "data_quality_score": q_score})
        ))

    db.bulk_save_objects(records)
    db.commit()
    return len(records)

# ============================================================
# STARTUP: Auto-Load Benchmark Datasets
# ============================================================

@app.on_event("startup")
def startup_event():
    db = next(get_db())
    try:
        count = db.query(models.MaterialMaster).count()
        candidate_files = ["material_master_input.csv", "material_master_input_50000(1).csv"]
        target_file = next((f for f in candidate_files if os.path.exists(f)), None)
        
        if count == 0 and target_file:
            print(f" Initializing database from {target_file}...")
            df = pd.read_csv(target_file, low_memory=False)
            parse_and_store_dataframe(df, db)
            print(" Database auto-seed complete.")
    finally:
        db.close()

# ============================================================
# API ENDPOINTS
# ============================================================

@app.get("/")
def home():
    return {
        "service": "National Unified Material Master Platform",
        "status": "online",
        "port": 8000,
        "docs": "/docs"
    }

# 1. CATALOG SEARCH, FILTER & PAGINATION
@app.get("/api/materials")
def get_materials(
    q: Optional[str] = Query(None, description="Search description, code, or CPSE"),
    sector: Optional[str] = Query(None),
    cpse: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    query = db.query(models.MaterialMaster)
    if q:
        safe_q = escape_like_string(q)
        query = query.filter(
            or_(
                models.MaterialMaster.description.ilike(f"%{safe_q}%"),
                models.MaterialMaster.material_code.ilike(f"%{safe_q}%"),
                models.MaterialMaster.cpse_name.ilike(f"%{safe_q}%")
            )
        )
    if sector:
        query = query.filter(models.MaterialMaster.sector == sector)
    if cpse:
        query = query.filter(models.MaterialMaster.cpse_name == cpse)

    total = query.count()
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

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
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": math.ceil(total / page_size) if total else 0,
        "results": results
    }

# 2. PAIRWISE MATCH EVALUATION (Live side-by-side comparison)
@app.get("/api/match")
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

# 3. EXECUTIVE PITCH KPIS
@app.get("/api/analytics/kpis")
def get_kpis(db: Session = Depends(get_db)):
    materials = db.query(models.MaterialMaster).all()
    total_materials = len(materials)
    if total_materials == 0:
        return {"error": "No materials loaded in database"}

    unique_cnmcs = db.query(func.count(func.distinct(models.MaterialMaster.cnmc_code))).scalar() or 1
    duplicates_detected = max(0, total_materials - unique_cnmcs)

    total_stock_value = sum(m.unit_price * m.stock_qty for m in materials)
    total_procurement_spend = sum(m.unit_price * m.annual_qty for m in materials)

    return {
        "total_materials": total_materials,
        "unique_national_codes": unique_cnmcs,
        "duplicate_materials": duplicates_detected,
        "duplicate_percentage": round((duplicates_detected / total_materials) * 100, 2),
        "inventory_value_inr": round(total_stock_value, 2),
        "annual_procurement_value_inr": round(total_procurement_spend, 2),
        "potential_procurement_savings_inr": round(total_procurement_spend * PROCUREMENT_SAVINGS_RATE, 2),
        "potential_inventory_reduction_inr": round(total_stock_value * INVENTORY_REDUCTION_RATE, 2),
        "procurement_savings_rate": f"{int(PROCUREMENT_SAVINGS_RATE * 100)}%",
        "inventory_reduction_rate": f"{int(INVENTORY_REDUCTION_RATE * 100)}%"
    }

# 4. RANKED SAVINGS OPPORTUNITIES (Cluster analysis sorted by spend)
@app.get("/api/analytics/opportunities")
def get_ranked_opportunities(limit: int = 15, db: Session = Depends(get_db)):
    duplicate_codes = (
        db.query(models.MaterialMaster.cnmc_code)
        .filter(models.MaterialMaster.cnmc_code != "PENDING_HARMONIZATION")
        .group_by(models.MaterialMaster.cnmc_code)
        .having(func.count(models.MaterialMaster.id) > 1)
        .all()
    )
    duplicate_codes = [r[0] for r in duplicate_codes]

    opportunities = []
    for code in duplicate_codes:
        cluster_items = db.query(models.MaterialMaster).filter(models.MaterialMaster.cnmc_code == code).all()
        inv_val = sum(m.unit_price * m.stock_qty for m in cluster_items)
        proc_val = sum(m.unit_price * m.annual_qty for m in cluster_items)

        opportunities.append({
            "cnmc_code": code,
            "canonical_name": cluster_items[0].standardized_description or cluster_items[0].description,
            "material_count": len(cluster_items),
            "cpses_involved": list(set(m.cpse_name for m in cluster_items)),
            "inventory_value_inr": round(inv_val, 2),
            "procurement_value_inr": round(proc_val, 2),
            "potential_savings_inr": round(proc_val * PROCUREMENT_SAVINGS_RATE, 2),
            "working_capital_freed_inr": round(inv_val * INVENTORY_REDUCTION_RATE, 2)
        })

    opportunities.sort(key=lambda x: x["inventory_value_inr"], reverse=True)
    return {"count": len(opportunities), "opportunities": opportunities[:limit]}

# 5. DUPLICATE CLUSTERS (Grouped by CNMC code)
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
            "canonical_name": members[0].standardized_description or members[0].description,
            "material_count": len(members),
            "cpses_involved": list(set(m.cpse_name for m in members)),
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
                for m in members
            ]
        })
    return {"count": len(clusters), "clusters": clusters}

# 6. HUMAN-IN-THE-LOOP APPROVAL & AUDIT LOG
@app.post("/api/materials/{material_id}/action")
def update_material_status(
    material_id: int,
    action: str = Query(..., pattern="^(APPROVE|REJECT)$"),
    performed_by: str = Query("dashboard_user"),
    notes: str = Query(""),
    db: Session = Depends(get_db)
):
    mat = db.query(models.MaterialMaster).filter(models.MaterialMaster.id == material_id).first()
    if not mat:
        raise HTTPException(status_code=404, detail="Material not found")

    mat.status = "APPROVED" if action == "APPROVE" else "REJECTED"
    log = models.AuditLog(
        material_code=mat.material_code,
        action=action,
        performed_by=performed_by,
        notes=notes or f"Material {mat.material_code} was {action.lower()}d."
    )
    db.add(log)
    db.commit()

    return {"success": True, "material_id": material_id, "action": action, "status": mat.status}

@app.get("/api/audit")
def get_audit_trail(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(models.AuditLog).order_by(models.AuditLog.id.desc()).limit(limit).all()
    return {"count": len(logs), "logs": logs}

# 7. SECURE LOCAL FILE INGESTION
@app.post("/api/load-local-file")
def load_local(file_name: str = Query(...), db: Session = Depends(get_db)):
    base_dir = Path(".").resolve()
    target_path = (base_dir / file_name).resolve()

    if not str(target_path).startswith(str(base_dir)) or not target_path.exists():
        raise HTTPException(status_code=400, detail="Invalid file path or access denied.")

    df = pd.read_csv(target_path) if target_path.suffix == ".csv" else pd.read_excel(target_path)
    count = parse_and_store_dataframe(df, db)
    return {"message": f"Loaded {count} records safely from {file_name}"}

# 8. MULTI-FORMAT UPLOAD (CSV, XLSX, PDF)
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    filename = file.filename.lower()

    if filename.endswith(".csv"):
        df = pd.read_csv(io.StringIO(contents.decode("utf-8", errors="ignore")))
    elif filename.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(contents))
    elif filename.endswith(".pdf"):
        df = extract_tables_from_pdf(contents)
        if df.empty:
            raise HTTPException(status_code=422, detail="No structured tables found in PDF.")
    else:
        raise HTTPException(status_code=400, detail="Supported formats: CSV, XLSX, XLS, PDF.")

    count = parse_and_store_dataframe(df, db)
    return {"message": f"Successfully ingested {count} records from '{file.filename}'.", "total_ingested": count}

# 9. ML SERVICE BRIDGES (With Fallbacks if ML Service is not running)
@app.post("/api/ml/match-single")
async def proxy_single_match(payload: dict, db: Session = Depends(get_db)):
    query_text = f"{payload.get('query_description', '')} {payload.get('query_spec_text', '')}".strip()
    
    # Try calling port 8001 if available
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{ML_SERVICE_URL}/api/ml/match-single",
                json={"query_text": query_text, "top_k": payload.get("top_k", 5)}
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass  # Fallback to local database matching below

    # Graceful Fallback: Match against existing database records
    items = db.query(models.MaterialMaster).limit(500).all()
    scored = []
    for item in items:
        sim = token_similarity(query_text, item.description)
        if sim > 0.3:
            scored.append({
                "source_material_code": item.material_code,
                "material_description": item.description,
                "assigned_cnmc": item.cnmc_code,
                "similarity_score": sim
            })
    scored.sort(key=lambda x: x["similarity_score"], reverse=True)
    return {
        "status": "local_fallback_match",
        "matches": scored[:payload.get("top_k", 5)]
    }

@app.post("/api/upload-and-harmonize")
async def upload_and_harmonize(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    
    # Forward file to ML service port 8001
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{ML_SERVICE_URL}/api/ml/harmonize-batch",
                files={"file": (file.filename, contents, file.content_type)}
            )
            ml_results = response.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"ML Service unavailable on port 8001: {str(e)}")

    crosswalk = ml_results.get("crosswalk", [])
    records = []
    for item in crosswalk:
        extra_info = {
            "match_type": item.get("match_type"),
            "confidence": item.get("match_confidence"),
            "category_name": item.get("category_name"),
            "issue_flag": item.get("issue_flag")
        }
        records.append(models.MaterialMaster(
            material_code=item.get("source_material_code", ""),
            description=item.get("material_description", ""),
            cpse_name=item.get("cpse_id", "GEN_CPSE"),
            cnmc_code=item.get("assigned_cnmc", "PENDING"),
            standardized_description=item.get("canonical_description", ""),
            status=item.get("status", "PENDING_REVIEW"),
            extra_data=json.dumps(extra_info)
        ))
    db.bulk_save_objects(records)
    db.commit()

    return {"message": f"Harmonized {len(records)} items via ML engine.", "kpis": ml_results.get("kpis")}