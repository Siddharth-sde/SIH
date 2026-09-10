import pandas as pd
import os
import time
from database import engine, SessionLocal, Base
import models

CSV_FILE = "cpse_material_master_all.csv"
BATCH_SIZE = 5000

def run_import():
    if not os.path.exists(CSV_FILE):
        print(f"❌ Error: {CSV_FILE} was not found in the current folder!")
        print("Please copy the CSV file to the 'SIH backend' directory and run again.")
        return

    print("🚀 Connecting to database and creating tables if needed...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()

    # Optional check: see if already imported
    existing_records = db.query(models.CPSEMaterial).count()
    if existing_records > 0:
        choice = input(f"⚠️  Database already contains {existing_records} records. Overwrite? (y/n): ")
        if choice.lower() == 'y':
            print("Purging existing records...")
            db.query(models.CPSEMaterial).delete()
            db.commit()
        else:
            print("Import cancelled.")
            db.close()
            return

    print(f"📖 Reading {CSV_FILE}...")
    start_time = time.time()

    # The exact subset of columns we care about
    essential_columns = [
        'material_id',
        'cpse_name',
        'sector',
        'plant',
        'legacy_material_code',
        'material_description',
        'standardized_description',
        'technical_specification',
        'uom',
        'unit_price',
        'annual_consumption',
        'common_national_material_code',
        'match_type',
        'status'
    ]

    total_inserted = 0

    # Read in chunks of 5000 rows for high performance & memory efficiency
    for chunk in pd.read_csv(CSV_FILE, usecols=essential_columns, chunksize=BATCH_SIZE):
        chunk = chunk.fillna({
            'plant': 'UNKNOWN',
            'standardized_description': '',
            'technical_specification': '',
            'uom': 'NOS',
            'unit_price': 0.0,
            'annual_consumption': 0,
            'match_type': 'EXACT_DUPLICATE',
            'status': 'ACTIVE'
        })

        records = []
        for _, row in chunk.iterrows():
            record = models.CPSEMaterial(
                material_id=str(row['material_id']).strip(),
                cpse_name=str(row['cpse_name']).strip(),
                sector=str(row['sector']).strip(),
                plant=str(row['plant']).strip(),
                legacy_material_code=str(row['legacy_material_code']).strip(),
                material_description=str(row['material_description']).strip(),
                standardized_description=str(row['standardized_description']).strip(),
                technical_specification=str(row['technical_specification']).strip(),
                uom=str(row['uom']).strip().upper(),
                unit_price=float(row['unit_price']),
                annual_consumption=int(row['annual_consumption']),
                cnmc_code=str(row['common_national_material_code']).strip(),
                match_type=str(row['match_type']).strip(),
                status=str(row['status']).strip()
            )
            records.append(record)

        db.bulk_save_objects(records)
        db.commit()
        total_inserted += len(records)
        print(f"  -> Ingested {total_inserted} / 50,000 records...")

    db.close()
    elapsed = round(time.time() - start_time, 2)
    print(f"\n🎉 Done! Successfully imported {total_inserted} records in {elapsed} seconds.")

if __name__ == "__main__":
    run_import()