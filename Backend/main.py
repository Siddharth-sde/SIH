import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from sqlalchemy import text

from database import Base, engine, get_db
import models
from utils import (
    clean_null_bytes,
    calculate_quality_score,
    parse_and_store_dataframe,
    ML_SERVICE_URL,
    PROCUREMENT_SAVINGS_RATE,
    INVENTORY_REDUCTION_RATE,
    INGESTION_BATCH_SIZE,
    ALIASES,
)
from routers import materials, clusters, analytics, audit, upload, ml_proxy

# ============================================================
# LIFESPAN & APPLICATION LIFECYCLE
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL;"))
        conn.execute(text("PRAGMA synchronous=NORMAL;"))
        conn.commit()

    def sync_startup():
        db = next(get_db())
        try:
            count = db.query(models.MaterialMaster).count()
            candidate_files = [
                "/app/data/material_crosswalk.csv",
                "/app/material_crosswalk.csv",
                "material_crosswalk.csv",
                "ML/data/processed/material_crosswalk.csv",
                "../ML/data/processed/material_crosswalk.csv",
                "material_master_input.csv",
                "Datasets/material_master_input.csv",
                "../Datasets/material_master_input.csv",
                "ML/material_master_input.csv",
                "../ML/material_master_input.csv",
                "Datasets/cpse_material_master_all.csv",
                "../Datasets/cpse_material_master_all.csv",
            ]
            target_file = next((f for f in candidate_files if os.path.exists(f)), None)

            if count == 0 and target_file:
                print(f"[*] Initializing cold-start database from '{target_file}'...")
                df = pd.read_csv(target_file, low_memory=False)
                inserted = parse_and_store_dataframe(df, db)
                print(f"[+] Successfully loaded {inserted} materials into database.")
            else:
                print(f"[*] Database currently contains {count} items. Skipping initialization.")
        except Exception as e:
            print(f"[!] Startup ingestion note: {e}")
        finally:
            db.close()

    await run_in_threadpool(sync_startup)
    yield

# ============================================================
# FASTAPI APP & ROUTER CONFIGURATION
# ============================================================

app = FastAPI(
    title="National Unified Material Master Platform",
    description="CPCL / MoP&NG Material Standardization & Harmonization API Gateway",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root & Health Endpoints
@app.get("/")
def home():
    return {
        "service": "National Unified Material Master Platform",
        "status": "online",
        "docs": "/docs"
    }

@app.get("/api/health")
def api_health():
    return {"status": "healthy", "service": "Backend API Gateway"}

# Include Modular Routers
app.include_router(materials.router)
app.include_router(clusters.router)
app.include_router(analytics.router)
app.include_router(audit.router)
app.include_router(upload.router)
app.include_router(ml_proxy.router)
