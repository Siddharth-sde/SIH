import io
import json
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
import httpx
import pandas as pd
from sqlalchemy.orm import Session
from database import get_db
import models
from utils import (
    clean_null_bytes,
    calculate_quality_score,
    extract_tables_from_pdf,
    parse_and_store_dataframe,
    INGESTION_BATCH_SIZE,
    ML_SERVICE_URL,
)

router = APIRouter(tags=["upload"])

@router.post("/api/load-local-file")
def load_local(file_name: str = Query(...), db: Session = Depends(get_db)):
    base_dir = Path(".").resolve()
    target_path = (base_dir / file_name).resolve()

    if not target_path.is_relative_to(base_dir) or not target_path.is_file():
        raise HTTPException(status_code=400, detail="Invalid file path or access outside application boundary.")

    try:
        df = pd.read_csv(target_path, low_memory=False) if target_path.suffix.lower() == ".csv" else pd.read_excel(target_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read local file: {str(e)}")

    count = parse_and_store_dataframe(df, db)
    return {"message": f"Successfully ingested {count} records from {file_name}"}

@router.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    filename = file.filename.lower() if file.filename else "unknown"

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents), low_memory=False)
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(contents))
        elif filename.endswith(".pdf"):
            df = extract_tables_from_pdf(contents)
            if df.empty:
                raise HTTPException(status_code=422, detail="No structured tables found in the uploaded PDF.")
        else:
            raise HTTPException(status_code=400, detail="Unsupported format. Permitted: CSV, XLSX, XLS, PDF.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"File parsing error: {str(e)}")

    def sync_parse_and_store():
        db = SessionLocal()
        try:
            return parse_and_store_dataframe(df, db)
        finally:
            db.close()

    count = await run_in_threadpool(sync_parse_and_store)
    return {"message": f"Successfully ingested {count} records from '{file.filename}'.", "total_ingested": count}

@router.post("/api/upload-and-harmonize")
async def upload_and_harmonize(file: UploadFile = File(...)):
    contents = await file.read()
    filename = file.filename or "upload.csv"
    content_type = file.content_type or "application/octet-stream"

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{ML_SERVICE_URL}/api/ml/harmonize-batch",
                files={"file": (filename, contents, content_type)}
            )
            response.raise_for_status()
            ml_results = response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"ML Service rejected input: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"ML Service unreachable at {ML_SERVICE_URL}: {str(e)}")

    crosswalk = ml_results.get("crosswalk") or ml_results.get("crosswalk_sample") or []

    def store_harmonized():
        from database import SessionLocal
        db = SessionLocal()
        try:
            existing_items = set(
                db.query(models.MaterialMaster.material_code, models.MaterialMaster.cpse_name).all()
            )
            records = []
            total_inserted = 0
            for item in crosswalk:
                raw_code = clean_null_bytes(item.get("source_material_code", ""))
                raw_desc = clean_null_bytes(item.get("raw_description", "") or item.get("material_description", ""))
                cpse = clean_null_bytes(item.get("cpse_id", "") or item.get("cpse_name", "GEN_CPSE"))

                if (raw_code, cpse) in existing_items:
                    continue
                existing_items.add((raw_code, cpse))

                sector = clean_null_bytes(item.get("sector", "General"))
                uom = clean_null_bytes(item.get("standard_uom", "") or item.get("source_uom", "") or item.get("uom", "NOS")).upper()

                try:
                    raw_price = item.get("unit_price_inr", 0.0) if item.get("unit_price_inr") is not None else item.get("unit_price", 0.0)
                    price = float(raw_price or 0.0)
                except (ValueError, TypeError):
                    price = 0.0

                try:
                    raw_stock = item.get("current_stock_qty", 0) if item.get("current_stock_qty") is not None else item.get("stock_qty", 0)
                    stock = int(float(raw_stock or 0))
                except (ValueError, TypeError):
                    stock = 0

                try:
                    raw_annual = item.get("annual_procurement_qty", 0) if item.get("annual_procurement_qty") is not None else item.get("annual_qty", 0)
                    annual = int(float(raw_annual or 0))
                except (ValueError, TypeError):
                    annual = 0

                extra_info = {
                    "match_type": item.get("match_type"),
                    "confidence": item.get("match_confidence"),
                    "category_name": item.get("category_name") or item.get("category_id"),
                    "issue_flag": item.get("issue_flag"),
                    "data_quality_score": calculate_quality_score(raw_code, raw_desc, uom, sector, price, stock, annual)
                }

                canonical = clean_null_bytes(item.get("canonical_description") or raw_desc).upper()
                cnmc = clean_null_bytes(item.get("cnmc_code") or item.get("assigned_cnmc", "PENDING_HARMONIZATION"))
                review_status = str(item.get("review_status", "")).upper()
                match_type = str(item.get("match_type", "")).upper()
                is_approved = review_status == "APPROVED" or match_type == "EXACT_DUPLICATE"

                records.append({
                    "material_code": raw_code,
                    "description": raw_desc,
                    "cpse_name": cpse,
                    "sector": sector,
                    "uom": uom,
                    "unit_price": max(0.0, price),
                    "stock_qty": max(0, stock),
                    "annual_qty": max(0, annual),
                    "cnmc_code": cnmc,
                    "standardized_description": canonical,
                    "status": "APPROVED" if is_approved else "PENDING_REVIEW",
                    "extra_data": json.dumps(extra_info)
                })

                if len(records) >= INGESTION_BATCH_SIZE:
                    db.bulk_insert_mappings(models.MaterialMaster, records)
                    db.commit()
                    total_inserted += len(records)
                    records = []

            if records:
                db.bulk_insert_mappings(models.MaterialMaster, records)
                db.commit()
                total_inserted += len(records)

            return total_inserted
        finally:
            db.close()

    total_inserted = await run_in_threadpool(store_harmonized)

    return {
        "message": f"Harmonized and saved {total_inserted} items via ML engine.",
        "kpis": ml_results.get("kpis", {})
    }
