# backend/app/api/cashpoints.py
import math
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.models import CashPoint
from app.schemas.schemas import CashPointResponse, RefillRequest, WithdrawalRequest
from app.services.prediction_service import calculate_cash_probability
from app.services.withdrawal_service import refill_cash_point, process_deposit

router = APIRouter(prefix="/api/cashpoints", tags=["CashPoints"])

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates the great-circle distance between two points in kilometers."""
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

@router.get("", response_model=List[CashPointResponse])
def get_nearby_cash_points(
    lat: float = Query(..., description="User latitude"),
    lng: float = Query(..., description="User longitude"),
    radius_km: float = Query(10.0, description="Search radius in kilometers"),
    amount: float = Query(2000.0, description="Requested withdrawal amount in INR"),
    db: Session = Depends(get_db)
):
    """
    Finds nearby active cash points within radius_km, calculates live ML probability scores,
    filters out unfulfillable points, and sorts by highest probability and closest distance.
    """
    all_points = db.query(CashPoint).filter(CashPoint.is_active == True).all()
    results = []

    for cp in all_points:
        dist = calculate_haversine_distance(lat, lng, cp.latitude, cp.longitude)
        if dist <= radius_km:
            pred = calculate_cash_probability(db, cp, requested_amount=amount)
            
            # Filter out points that cannot fulfill the requested amount
            if not pred["is_fulfillable"]:
                continue

            resp = CashPointResponse(
                id=cp.id,
                name=cp.name,
                type=cp.type,
                address=cp.address,
                latitude=cp.latitude,
                longitude=cp.longitude,
                standard_float_limit=cp.standard_float_limit,
                current_cash_balance=cp.current_cash_balance,
                upi_id=cp.upi_id,
                distance_km=dist,
                probability_score=pred["probability_score"],
                confidence_level=pred["confidence_level"],
                badge_color=pred["badge_color"],
                is_fulfillable=pred["is_fulfillable"],
                reasons=pred["reasons"],
                is_active=cp.is_active,
                last_refilled_at=cp.last_refilled_at
            )
            results.append(resp)

    # Sort results: primary by highest probability score, secondary by closest distance
    results.sort(key=lambda x: (-x.probability_score, x.distance_km))
    return results

@router.post("/{cash_point_id}/refill", response_model=CashPointResponse)
def refill_cash_point_endpoint(
    cash_point_id: int,
    req: RefillRequest,
    db: Session = Depends(get_db)
):
    """Refills or manipulates cash float for a specific cash point."""
    try:
        updated_cp = refill_cash_point(
            db=db,
            cash_point_id=cash_point_id,
            new_balance=req.new_balance,
            add_amount=req.add_amount
        )
        pred = calculate_cash_probability(db, updated_cp, requested_amount=2000.0)
        
        return CashPointResponse(
            id=updated_cp.id,
            name=updated_cp.name,
            type=updated_cp.type,
            address=updated_cp.address,
            latitude=updated_cp.latitude,
            longitude=updated_cp.longitude,
            standard_float_limit=updated_cp.standard_float_limit,
            current_cash_balance=updated_cp.current_cash_balance,
            upi_id=updated_cp.upi_id,
            distance_km=0.0,
            probability_score=pred["probability_score"],
            confidence_level=pred["confidence_level"],
            badge_color=pred["badge_color"],
            is_fulfillable=pred["is_fulfillable"],
            reasons=pred["reasons"],
            is_active=updated_cp.is_active,
            last_refilled_at=updated_cp.last_refilled_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{cash_point_id}/deposit", response_model=CashPointResponse)
def deposit_cash_point_endpoint(
    cash_point_id: int,
    req: WithdrawalRequest,
    db: Session = Depends(get_db)
):
    """Processes a cash deposit or merchant cash float addition."""
    try:
        tx = process_deposit(
            db=db,
            cash_point_id=cash_point_id,
            amount=req.amount,
            upi_ref=None
        )
        updated_cp = db.query(CashPoint).get(cash_point_id)
        pred = calculate_cash_probability(db, updated_cp, requested_amount=2000.0)

        return CashPointResponse(
            id=updated_cp.id,
            name=updated_cp.name,
            type=updated_cp.type,
            address=updated_cp.address,
            latitude=updated_cp.latitude,
            longitude=updated_cp.longitude,
            standard_float_limit=updated_cp.standard_float_limit,
            current_cash_balance=updated_cp.current_cash_balance,
            upi_id=updated_cp.upi_id,
            distance_km=0.0,
            probability_score=pred["probability_score"],
            confidence_level=pred["confidence_level"],
            badge_color=pred["badge_color"],
            is_fulfillable=pred["is_fulfillable"],
            reasons=pred["reasons"],
            is_active=updated_cp.is_active,
            last_refilled_at=updated_cp.last_refilled_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
