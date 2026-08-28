# backed/app/models/models.py

import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base

class CashPointType(str, enum.Enum):
    ATM = "ATM"
    MERCHANT = "MERCHANT"

class PingStatus(str, enum.Enum):
    GOT_CASH = "GOT_CASH"
    OUT_OF_CASH = "OUT_OF_CASH"
    MACHINE_BROKEN = "MACHINE_BROKEN"

class TransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class CashPoint(Base):
    __tablename__ = "cash_points"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    type = Column(SQLEnum(CashPointType), nullable=False, default=CashPointType.ATM)
    address = Column(String, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    standard_float_limit = Column(Float, default=50000.0)  # Total cash capacity in INR
    current_cash_balance = Column(Float, default=50000.0)  # Current available cash in INR
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # UPI details for merchant cash points
    upi_id = Column(String, nullable=True)

    # Relationships
    telemetry_pings = relationship("TelemetryPing", back_populates="cash_point", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="cash_point", cascade="all, delete-orphan")

class TelemetryPing(Base):
    __tablename__ = "telemetry_pings"

    id = Column(Integer, primary_key=True, index=True)
    cash_point_id = Column(Integer, ForeignKey("cash_points.id"), nullable=False)
    status = Column(SQLEnum(PingStatus), nullable=False)
    amount_withdrawn = Column(Float, nullable=True)  # Amount if user got cash
    note = Column(String, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationship
    cash_point = relationship("CashPoint", back_populates="telemetry_pings")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    cash_point_id = Column(Integer, ForeignKey("cash_points.id"), nullable=False)
    amount_requested = Column(Float, nullable=False)
    status = Column(SQLEnum(TransactionStatus), default=TransactionStatus.PENDING)
    upi_ref = Column(String, nullable=True, unique=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationship
    cash_point = relationship("CashPoint", back_populates="transactions")
