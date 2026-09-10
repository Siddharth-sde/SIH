from sqlalchemy import Column, Integer, String, Float
from database import Base

class CPSEMaterial(Base):
    __tablename__ = "cpse_materials"

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(String, unique=True, index=True)       # e.g., "MAT-OG-000001"
    cpse_name = Column(String, index=True)                      # e.g., "ONGC", "IOCL", "BPCL"
    sector = Column(String, index=True)                         # e.g., "Oil & Gas"
    plant = Column(String)                                      # e.g., "ONGC-PLANT-05"
    legacy_material_code = Column(String, index=True)           # e.g., "OG-126225"
    material_description = Column(String)                       # The messy CPSE description
    standardized_description = Column(String)                   # The clean harmonized description
    technical_specification = Column(String)                    # e.g., "DOE 10 inch"
    uom = Column(String)                                        # Unit of Measure (EA, LTR, etc.)
    unit_price = Column(Float, default=0.0)                     # Price in INR
    annual_consumption = Column(Integer, default=0)             # For inventory demand aggregation
    cnmc_code = Column(String, index=True)                      # e.g., "NMC-OG-00655"
    match_type = Column(String)                                 # EXACT_DUPLICATE, NEAR_DUPLICATE, etc.
    status = Column(String, default="ACTIVE")