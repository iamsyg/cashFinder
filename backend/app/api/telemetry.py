# backend/app/api/telemetry.py
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.models import CashPoint, TelemetryPing
from app.schemas.schemas import TelemetryPingCreate, TelemetryPingResponse

router = APIRouter(prefix="/api/telemetry", tags=["Telemetry"])

@router.post("", response_model=TelemetryPingResponse)
def submit_telemetry_ping(
    ping_data: TelemetryPingCreate,
    db: Session = Depends(get_db)
):
    """
    Submits a crowdsourced telemetry report ('GOT_CASH', 'OUT_OF_CASH', 'MACHINE_BROKEN')
    for a specific cash point to update real-time availability signals.
    """
    cash_point = db.query(CashPoint).filter(CashPoint.id == ping_data.cash_point_id).first()
    if not cash_point:
        raise HTTPException(status_code=404, detail="Cash point not found")

    new_ping = TelemetryPing(
        cash_point_id=ping_data.cash_point_id,
        status=ping_data.status,
        amount_withdrawn=ping_data.amount_withdrawn,
        note=ping_data.note,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(new_ping)
    db.commit()
    db.refresh(new_ping)

    return new_ping

@router.get("/{cash_point_id}", response_model=List[TelemetryPingResponse])
def get_cash_point_telemetry_history(
    cash_point_id: int,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Retrieves recent telemetry reports for a specific cash point."""
    pings = (
        db.query(TelemetryPing)
        .filter(TelemetryPing.cash_point_id == cash_point_id)
        .order_by(TelemetryPing.timestamp.desc())
        .limit(limit)
        .all()
    )
    return pings
