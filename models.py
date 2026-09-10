from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from datetime import datetime
from database import Base

class MaterialMaster(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    
    # 7 Core Normalized Columns
    material_code = Column(String(100), index=True)
    description = Column(String(500), index=True)
    cpse_name = Column(String(100), index=True)
    sector = Column(String(100), index=True)
    uom = Column(String(50), default="NOS")
    unit_price = Column(Float, default=0.0)
    stock_qty = Column(Integer, default=0)
    annual_qty = Column(Integer, default=0)
    
    # Harmonization Fields
    cnmc_code = Column(String(100), index=True, default="PENDING_HARMONIZATION")
    standardized_description = Column(String(500), default="")
    status = Column(String(50), default="ACTIVE")
    
    # Extensible metadata (stores specifications, plant, bucket, quality scores)
    extra_data = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    material_code = Column(String(100))
    action = Column(String(50))
    performed_by = Column(String(100), default="dashboard_user")
    notes = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)