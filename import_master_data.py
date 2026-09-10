import pandas as pd
import json
import os
from database import engine, SessionLocal, Base
import models

def run_import(csv_file="material_master_input.csv"):
    if not os.path.exists(csv_file):
        print(f"File not found: {csv_file}")
        return

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Fixed: Query MaterialMaster instead of the non-existent CPSEMaterial
    existing_records = db.query(models.MaterialMaster).count()
    if existing_records > 0:
        db.query(models.MaterialMaster).delete()
        db.commit()

    df = pd.read_csv(csv_file, low_memory=False)
    records = []
    for idx, row in df.iterrows():
        code = str(row.get("source_material_code") or row.get("material_code") or f"MAT-{idx}").strip()
        desc = str(row.get("material_description") or row.get("description") or "").strip()
        
        # Capture all supplemental fields into extra_data
        core_cols = {"source_material_code", "material_code", "material_description", "description", 
                     "cpse_id", "sector", "uom", "unit_price_inr", "current_stock_qty", "annual_procurement_qty"}
        extra = {k: str(v) for k, v in row.items() if k not in core_cols and pd.notna(v)}

        records.append(models.MaterialMaster(
            material_code=code,
            description=desc,
            cpse_name=str(row.get("cpse_id") or "GEN_CPSE").strip(),
            sector=str(row.get("sector") or "General").strip(),
            uom=str(row.get("uom") or "NOS").strip().upper(),
            unit_price=float(row.get("unit_price_inr") or row.get("unit_price") or 0.0),
            stock_qty=int(float(row.get("current_stock_qty") or 0)),
            annual_qty=int(float(row.get("annual_procurement_qty") or 0)),
            cnmc_code=str(row.get("cnmc_code") or "PENDING_HARMONIZATION"),
            standardized_description=desc.upper(),
            status="ACTIVE",
            extra_data=json.dumps(extra)
        ))
        if len(records) >= 5000:
            db.bulk_save_objects(records)
            db.commit()
            records = []

    if records:
        db.bulk_save_objects(records)
        db.commit()
    db.close()
    print(f"Successfully ingested records into MaterialMaster.")

if __name__ == "__main__":
    run_import()