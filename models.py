from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from sqlalchemy.sql import func
from database import Base

class MaterialMaster(Base):
    __tablename__ = "material_master"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    material_code = Column(String(100), index=True, nullable=False)
    description = Column(String(500), index=True, nullable=False)
    cpse_name = Column(String(150), index=True, nullable=True, default="CPSE_GENERAL")
    sector = Column(String(100), index=True, nullable=True, default="General")
    uom = Column(String(50), nullable=True, default="NOS")
    unit_price = Column(Float, default=0.0, nullable=False)
    stock_qty = Column(Integer, default=0, nullable=False)
    annual_qty = Column(Integer, default=0, nullable=False)
    cnmc_code = Column(String(100), index=True, nullable=True, default="PENDING_HARMONIZATION")
    standardized_description = Column(String(500), nullable=True)
    status = Column(String(50), default="ACTIVE", index=True)
    extra_data = Column(Text, nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    material_code = Column(String(100), index=True, nullable=False)
    action = Column(String(50), nullable=False)
    performed_by = Column(String(100), default="dashboard_user")
    notes = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())