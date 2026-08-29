# backend/app/schemas/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.models.models import CashPointType, PingStatus, TransactionStatus, TransactionType

# --- CashPoint Schemas ---
class CashPointBase(BaseModel):
    name: str
    type: CashPointType
    address: Optional[str] = None
    latitude: float
    longitude: float
    standard_float_limit: float = 50000.0
    upi_id: Optional[str] = None

class CashPointCreate(CashPointBase):
    pass

class CashPointResponse(CashPointBase):
    id: int
    current_cash_balance: float
    distance_km: float
    probability_score: int
    confidence_level: str
    badge_color: str
    is_fulfillable: bool
    reasons: List[str]
    is_active: bool
    last_refilled_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Telemetry Ping Schemas ---
class TelemetryPingCreate(BaseModel):
    cash_point_id: int
    status: PingStatus
    amount_withdrawn: Optional[float] = None
    note: Optional[str] = None

class TelemetryPingResponse(BaseModel):
    id: int
    cash_point_id: int
    status: PingStatus
    amount_withdrawn: Optional[float] = None
    note: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True

# --- Withdrawal & UPI Schemas ---
class WithdrawalRequest(BaseModel):
    cash_point_id: int
    amount: float = Field(gt=0, description="Amount to withdraw in INR")

class WithdrawalResponse(BaseModel):
    transaction_id: int
    cash_point_id: int
    cash_point_name: str
    amount_requested: float
    status: TransactionStatus
    upi_ref: str
    upi_intent_uri: str
    qr_code_base64: str
    remaining_balance: float
    timestamp: datetime

class RefillRequest(BaseModel):
    new_balance: Optional[float] = None
    add_amount: Optional[float] = None
