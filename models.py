from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from datetime import datetime
from database import Base

class MaterialMaster(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    
    # 7 Core Standardized Columns (Always present)
    material_code = Column(String(100), index=True)      # Any code (source_material_code, legacy_material_code, MATNR)
    description = Column(String(500), index=True)        # The raw description
    cpse_name = Column(String(100), index=True)          # CPCL, ONGC, NTPC, etc.
    sector = Column(String(100), index=True)             # Oil & Gas, Power, etc.
    uom = Column(String(50), default="NOS")              # Unit of measure
    unit_price = Column(Float, default=0.0)              # Price in INR
    stock_qty = Column(Integer, default=0)               # Current stock / inventory
    annual_qty = Column(Integer, default=0)              # Annual consumption
    
    # Harmonization & Registry Output
    cnmc_code = Column(String(100), index=True, default="PENDING")
    standardized_description = Column(String(500), default="")
    status = Column(String(50), default="ACTIVE")        # ACTIVE, PENDING_REVIEW, APPROVED, REJECTED
    
    # Universal Dynamic Storage: Any other columns (bucket, specs, plant, vendor, etc.) go here as JSON
    extra_data = Column(Text, default="{}")
    
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    material_code = Column(String(100))
    action = Column(String(50))                          # e.g., "MERGED", "APPROVED", "REJECTED"
    performed_by = Column(String(100), default="SYSTEM_ADMIN")
    notes = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)