import io
import json
import os
import re
from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy.orm import Session
import models

try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# ============================================================
# APP CONFIGURATION & CONSTANTS
# ============================================================

ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://127.0.0.1:8001").rstrip("/")
PROCUREMENT_SAVINGS_RATE = 0.10
INVENTORY_REDUCTION_RATE = 0.15
INGESTION_BATCH_SIZE = 5000

ALIASES = {
    "material_code": ["source_material_code", "material_code", "legacy_material_code", "matnr", "item_code"],
    "description": ["material_description", "raw_description", "description", "maktx", "item_desc", "item_name"],
    "cpse_name": ["cpse_id", "cpse_name", "cpse", "company", "enterprise"],
    "sector": ["sector", "industry", "domain"],
    "uom": ["uom", "standard_uom", "source_uom", "meins", "unit"],
    "unit_price": ["unit_price_inr", "unit_price", "price", "rate", "cost"],
    "stock_qty": ["current_stock_qty", "stock_qty", "stock", "inventory"],
    "annual_qty": ["annual_procurement_qty", "annual_consumption", "annual_qty"],
    "cnmc_code": ["cnmc_code", "common_national_material_code", "true_cluster_id", "cluster_id"]
}

# ============================================================
# UTILITIES: Sanitization, Normalization & PDF Parsing
# ============================================================

def clean_null_bytes(val: Any) -> str:
    """Removes \x00 null bytes to prevent database driver errors."""
    if val is None or pd.isna(val):
        return ""
    return str(val).replace("\x00", "").strip()

def escape_like_string(text_val: str) -> str:
    return text_val.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

def normalize_text(text_val: Optional[str]) -> str:
    cleaned = clean_null_bytes(text_val)
    text_val = cleaned.lower().replace("×", "x")
    text_val = re.sub(r"[^a-z0-9\s./%-]", " ", text_val)
    return " ".join(text_val.split())

def calculate_quality_score(raw_code: str, raw_desc: str, uom: str, sector: str, raw_price: Any, raw_stock: Any, raw_annual: Any) -> float:
    def safe_positive(val):
        try:
            if val is None or pd.isna(val):
                return False
            cleaned = str(val).replace(",", "").strip()
            return float(cleaned) > 0
        except (ValueError, TypeError):
            return False

    def safe_notna(val):
        try:
            if val is None or pd.isna(val):
                return False
            cleaned = str(val).replace(",", "").strip()
            return cleaned != "" and cleaned.lower() not in ("nan", "none", "null", "n/a", "tbd")
        except Exception:
            return False

    score = sum([
        bool(raw_code and not raw_code.startswith("ITEM-")),
        bool(raw_desc and raw_desc != "UNNAMED ITEM"),
        bool(uom),
        bool(sector and sector != "General"),
        safe_positive(raw_price),
        safe_notna(raw_stock),
        safe_notna(raw_annual)
    ])
    return round((score / 7.0) * 100, 1)

def token_similarity(text_a: str, text_b: str) -> float:
    a = set(normalize_text(text_a).split())
    b = set(normalize_text(text_b).split())
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

def extract_tables_from_pdf(contents: bytes) -> pd.DataFrame:
    if not PDF_SUPPORT:
        return pd.DataFrame()
    all_rows = []
    headers = None
    with pdfplumber.open(io.BytesIO(contents)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                for row in table:
                    clean_row = [clean_null_bytes(cell) for cell in row]
                    if not any(clean_row):
                        continue
                    if headers is None:
                        normalized_header = [c.lower().replace(" ", "_") for c in clean_row]
                        if any(alias in normalized_header for target in ALIASES for alias in ALIASES[target]):
                            headers = clean_row
                            continue
                    elif len(clean_row) == len(headers):
                        all_rows.append(clean_row)
    if not headers or not all_rows:
        return pd.DataFrame()
    return pd.DataFrame(all_rows, columns=headers).dropna(how="all")

def parse_and_store_dataframe(df: pd.DataFrame, db: Session) -> int:
    if df.empty:
        return 0

    col_lookup = {clean_null_bytes(col).lower().replace(" ", "_"): col for col in df.columns}

    def get_val(row, target_key, default=None):
        for alias in ALIASES.get(target_key, []):
            if alias in col_lookup:
                val = row[col_lookup[alias]]
                if pd.notna(val) and str(val).strip() != "":
                    return val
        return default

    matched_orig_cols = {col_lookup[a] for k in ALIASES for a in ALIASES[k] if a in col_lookup}
    unmatched_cols = [c for c in df.columns if c not in matched_orig_cols]

    # Pre-fetch existing (material_code, cpse_name) to prevent duplicate inserts on re-upload
    existing_items = set(
        db.query(models.MaterialMaster.material_code, models.MaterialMaster.cpse_name).all()
    )

    total_inserted = 0
    records = []

    for idx, row in df.iterrows():
        raw_code = clean_null_bytes(get_val(row, "material_code", f"ITEM-{idx+1}"))
        raw_desc = clean_null_bytes(get_val(row, "description", "UNNAMED ITEM"))
        cpse = clean_null_bytes(get_val(row, "cpse_name", "CPSE_GENERAL"))
        sector = clean_null_bytes(get_val(row, "sector", "General"))
        uom = clean_null_bytes(get_val(row, "uom", "NOS")).upper()

        # Skip if item code already exists for this CPSE
        if (raw_code, cpse) in existing_items:
            continue
        existing_items.add((raw_code, cpse))

        raw_price = get_val(row, "unit_price")
        try:
            cleaned_p = str(raw_price).replace(",", "").strip() if pd.notna(raw_price) else "0"
            price = float(cleaned_p)
        except (ValueError, TypeError):
            price = 0.0

        raw_stock = get_val(row, "stock_qty")
        try:
            cleaned_s = str(raw_stock).replace(",", "").strip() if pd.notna(raw_stock) else "0"
            stock = int(float(cleaned_s))
        except (ValueError, TypeError):
            stock = 0

        raw_annual = get_val(row, "annual_qty")
        try:
            cleaned_a = str(raw_annual).replace(",", "").strip() if pd.notna(raw_annual) else "0"
            annual = int(float(cleaned_a))
        except (ValueError, TypeError):
            annual = 0

        raw_cnmc = clean_null_bytes(get_val(row, "cnmc_code"))
        if raw_cnmc and raw_cnmc != "PENDING_HARMONIZATION":
            clean_code = raw_cnmc.replace('CLUSTER_', '').strip()
            cnmc = clean_code if clean_code.startswith("NMC-") else f"NMC-{clean_code}"
        else:
            cnmc = "PENDING_HARMONIZATION"

        extra = {}
        for c in unmatched_cols:
            val = row[c]
            if pd.notna(val):
                extra[str(c)] = clean_null_bytes(val)

        extra["data_quality_score"] = calculate_quality_score(raw_code, raw_desc, uom, sector, raw_price, raw_stock, raw_annual)

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
            "standardized_description": raw_desc.upper(),
            "status": "PENDING_REVIEW" if str(extra.get("human_review_flag", "")).lower() == "true" else "ACTIVE",
            "extra_data": json.dumps(extra)
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
