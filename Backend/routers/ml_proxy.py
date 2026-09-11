import json
import os
from typing import Any, Dict
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
import httpx
from utils import ML_SERVICE_URL

router = APIRouter(tags=["ml_proxy"])

@router.get("/api/ml/health")
async def api_ml_health():
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{ML_SERVICE_URL}/health")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return {"status": "unreachable", "service": "ML Engine"}

@router.get("/api/ml/kpis")
async def proxy_ml_kpis():
    """Proxies KPI request to ML microservice with honest local fallback."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{ML_SERVICE_URL}/api/ml/kpis")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass

    for candidate in [
        "/app/data/dashboard_kpis.json",
        "/app/dashboard_kpis.json",
        "ML/data/processed/dashboard_kpis.json",
        "../ML/data/processed/dashboard_kpis.json",
        "dashboard_kpis.json"
    ]:
        if os.path.exists(candidate):
            try:
                with open(candidate, "r") as f:
                    return json.load(f)
            except Exception:
                continue

    return {
        "status": "unavailable",
        "message": "ML KPIs unavailable. Run harmonization to generate live metrics.",
        "total_materials_ingested": 0,
        "unique_national_materials": 0,
        "duplicates_rationalized": 0,
        "rationalization_percentage": "0.0%",
        "total_annual_spend_inr": 0.0,
        "estimated_procurement_savings_inr": "₹0.00"
    }

@router.post("/api/ml/match-single")
async def proxy_ml_match_single(payload: Dict[str, Any]):
    """Proxies single item matching request to ML microservice."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{ML_SERVICE_URL}/api/ml/match-single", json=payload)
            if resp.status_code == 200:
                return resp.json()
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"ML Service unreachable at {ML_SERVICE_URL}: {str(e)}")

@router.post("/api/ml/harmonize-batch")
async def proxy_ml_harmonize_batch(file: UploadFile = File(...)):
    """Proxies batch harmonization file upload directly to ML microservice."""
    contents = await file.read()
    filename = file.filename or "upload.csv"
    content_type = file.content_type or "application/octet-stream"

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f"{ML_SERVICE_URL}/api/ml/harmonize-batch",
                files={"file": (filename, contents, content_type)}
            )
            if resp.status_code == 200:
                return resp.json()
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"ML Service unreachable at {ML_SERVICE_URL}: {str(e)}")
