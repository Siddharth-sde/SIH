"""
FastAPI Microservice for ML Harmonization Engine (Container Entrypoint).
Exposes Batch Harmonization and Real-time Deduplication Matching APIs.
"""

import io
import os
import json
import logging
import tempfile
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import pandas as pd

from src.pipeline import pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ml_service")

app = FastAPI(
    title="National Material Master Harmonization - ML Service",
    version="2.0.0",
    description="Offline-capable AI engine for CPSE material code deduplication, specification extraction, and taxonomy classification."
)


@app.on_event("startup")
def on_startup():
    """Hydrates existing golden catalog if available on startup."""
    logger.info("Starting National Material Master ML Microservice...")
    loaded = pipeline.load_existing_catalog()
    if loaded:
        logger.info(f"Hydrated {len(pipeline.golden_clusters)} golden catalog records on startup.")
    else:
        logger.info("No pre-processed catalog found. Service ready for batch harmonization.")


# ---------------- Request / Response Schemas ----------------

class SingleMatchRequest(BaseModel):
    query_description: str
    query_spec_text: Optional[str] = ""
    query_uom: Optional[str] = "NOS"
    top_k: Optional[int] = 5


class BatchHarmonizeRequest(BaseModel):
    items: List[Dict[str, Any]]


# ---------------- Endpoints ----------------

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "engine": "National Material Master ML Engine",
        "embedding_model": "all-MiniLM-L6-v2 (384-d, offline)",
        "taxonomy_categories": 18,
        "loaded_golden_clusters": len(pipeline.golden_clusters),
    }


@app.post("/api/ml/match-single")
def match_single(req: SingleMatchRequest):
    """
    Real-time interactive matching API (for Shlok's AIMatching.jsx via Harshit's Backend).
    Extracts technical specs, predicts category, and searches against existing CNMC clusters.
    """
    try:
        result = pipeline.match_single_query(
            query_description=req.query_description,
            query_spec_text=req.query_spec_text or "",
            query_uom=req.query_uom or "NOS",
            top_k=req.top_k or 5
        )
        return result
    except Exception as e:
        logger.error(f"Error in match_single: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ml/harmonize-batch")
async def harmonize_batch(file: UploadFile = File(...)):
    """
    Batch harmonization endpoint (for Harshit's /api/upload).
    Accepts raw CPSE CSV file, runs all 4 ML stages, and returns structured golden master and crosswalk records.
    """
    contents = await file.read()
    try:
        df = pd.read_csv(io.StringIO(contents.decode("utf-8", errors="ignore")))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {e}")

    # Secure temporary file to prevent path traversal
    safe_filename = os.path.basename(file.filename or "upload.csv")
    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{safe_filename}") as tmp:
        temp_path = tmp.name

    df.to_csv(temp_path, index=False)

    try:
        summary = pipeline.process_dataset(temp_path)
        output_paths = pipeline.export_results("data/processed")

        golden_df = pd.read_csv(output_paths["golden_master"])
        crosswalk_df = pd.read_csv(output_paths["crosswalk"])
        with open(output_paths["kpis"], "r") as f:
            kpis = json.load(f)

        return {
            "summary": summary,
            "kpis": kpis,
            "total_golden_records": len(golden_df),
            "total_crosswalk_records": len(crosswalk_df),
            "golden_sample": golden_df.head(10).to_dict(orient="records"),
            "crosswalk_sample": crosswalk_df.head(10).to_dict(orient="records"),
        }
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/api/ml/harmonize-batch-json")
def harmonize_batch_json(req: BatchHarmonizeRequest):
    """
    JSON batch harmonization endpoint (for direct programmatic backend ingestion).
    Accepts a list of material records, runs all 4 ML stages, and returns golden masters and crosswalk records.
    """
    if not req.items:
        raise HTTPException(status_code=400, detail="Empty items list provided.")

    df = pd.DataFrame(req.items)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", encoding="utf-8") as tmp:
        temp_path = tmp.name
        df.to_csv(temp_path, index=False)

    try:
        summary = pipeline.process_dataset(temp_path)
        output_paths = pipeline.export_results("data/processed")

        golden_df = pd.read_csv(output_paths["golden_master"])
        crosswalk_df = pd.read_csv(output_paths["crosswalk"])
        with open(output_paths["kpis"], "r") as f:
            kpis = json.load(f)

        return {
            "summary": summary,
            "kpis": kpis,
            "total_golden_records": len(golden_df),
            "total_crosswalk_records": len(crosswalk_df),
            "golden_sample": golden_df.head(10).to_dict(orient="records"),
            "crosswalk_sample": crosswalk_df.head(10).to_dict(orient="records"),
        }
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.get("/api/ml/kpis")
def get_kpis():
    """Returns the latest calculated KPIs from the harmonization run."""
    kpi_path = "data/processed/dashboard_kpis.json"
    if os.path.exists(kpi_path):
        with open(kpi_path, "r") as f:
            return json.load(f)
    return {"message": "No processed KPIs found yet."}
