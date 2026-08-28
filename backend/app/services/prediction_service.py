# backend/app/services/prediction_service.py
import os
import math
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.models import CashPoint, CashPointType, TelemetryPing, PingStatus, Transaction, TransactionStatus, TransactionType

# Load trained ML model artifact if available
MODEL_PATH = os.path.join(os.path.dirname(__file__), "../ml/cash_model.pkl")
ml_model = None

if os.path.exists(MODEL_PATH):
    try:
        with open(MODEL_PATH, "rb") as f:
            ml_model = pickle.load(f)
        print(f"[ML SERVICE] Successfully loaded trained model from {MODEL_PATH}")
    except Exception as e:
        print(f"[ML SERVICE WARNING] Failed to load model artifact: {e}")

def calculate_cash_probability(
    db: Session,
    cash_point: CashPoint,
    requested_amount: float
) -> Dict[str, Any]:
    """
    Predicts cash availability using trained Gradient Boosted ML Model with feature engineering,
    falling back to heuristic scoring if ML model is unavailable.
    """
    now = datetime.now(timezone.utc)

    # 1. Hard Filter: Requested amount exceeds live available cash balance
    if requested_amount > cash_point.current_cash_balance:
        return {
            "cash_point_id": cash_point.id,
            "cash_point_name": cash_point.name,
            "is_fulfillable": False,
            "probability_score": 0,
            "confidence_level": "UNAVAILABLE",
            "badge_color": "gray",
            "current_balance": cash_point.current_cash_balance,
            "reasons": [f"Insufficient balance for requested amount of INR {requested_amount}"]
        }

    # Helper function to convert naive timestamps to UTC aware
    def make_utc(dt: Optional[datetime]) -> Optional[datetime]:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    # Feature extraction from live DB state
    six_hours_ago = now - timedelta(hours=6)
    one_hour_ago = now - timedelta(hours=1)
    two_hours_ago = now - timedelta(hours=2)

    # Positive pings in last 6 hours
    pos_pings_count = (
        db.query(TelemetryPing)
        .filter(
            TelemetryPing.cash_point_id == cash_point.id,
            TelemetryPing.status == PingStatus.GOT_CASH,
            TelemetryPing.timestamp >= six_hours_ago
        )
        .count()
    )

    # Negative pings in last 1 hour
    fail_pings_count = (
        db.query(TelemetryPing)
        .filter(
            TelemetryPing.cash_point_id == cash_point.id,
            TelemetryPing.status.in_([PingStatus.OUT_OF_CASH, PingStatus.MACHINE_BROKEN]),
            TelemetryPing.timestamp >= one_hour_ago
        )
        .count()
    )

    # Recent withdrawals in last 2 hours
    recent_txs = (
        db.query(Transaction)
        .filter(
            Transaction.cash_point_id == cash_point.id,
            Transaction.type == TransactionType.WITHDRAWAL,
            Transaction.status == TransactionStatus.SUCCESS,
            Transaction.timestamp >= two_hours_ago
        )
        .all()
    )
    total_withdrawn_2h = sum(tx.amount_requested for tx in recent_txs) if recent_txs else 0.0

    last_refill_time = make_utc(cash_point.last_refilled_at)
    hours_since_refill = (now - last_refill_time).total_seconds() / 3600.0 if last_refill_time else 12.0

    # 2. ML Model Inference
    if ml_model is not None:
        try:
            capacity_ratio = min(1.0, max(0.0, cash_point.current_cash_balance / max(1.0, cash_point.standard_float_limit)))
            amount_ratio = min(5.0, max(0.0, requested_amount / max(1.0, cash_point.current_cash_balance)))
            burn_rate = total_withdrawn_2h / 2.0
            
            hour_val = now.hour
            hour_sin = np.sin(2 * np.pi * hour_val / 24.0)
            hour_cos = np.cos(2 * np.pi * hour_val / 24.0)
            net_signal = pos_pings_count - (2 * fail_pings_count)

            is_weekend = 1 if now.weekday() >= 5 else 0
            is_salary_day = 1 if now.day <= 5 else 0
            is_onsite = 1 if cash_point.type == CashPointType.ATM else 0

            feature_df = pd.DataFrame([{
                'capacity_ratio': capacity_ratio,
                'amount_ratio': amount_ratio,
                'burn_rate': burn_rate,
                'hours_since_refill': hours_since_refill,
                'hour_sin': hour_sin,
                'hour_cos': hour_cos,
                'net_signal': net_signal,
                'is_weekend': is_weekend,
                'is_salary_day': is_salary_day,
                'is_onsite': is_onsite
            }])

            prob_array = ml_model.predict_proba(feature_df)
            raw_prob = prob_array[0][1] # Probability of success class

            # Apply crowdsourced failure override penalty if explicit negative reports exist
            if fail_pings_count > 0:
                raw_prob = max(0.05, raw_prob - (0.25 * fail_pings_count))

            final_score = int(round(raw_prob * 100))
            final_score = max(5, min(99, final_score))

            reasons = [
                f"ML Engine prediction based on live capacity ratio ({capacity_ratio*100:.0f}%)",
                f"Recent withdrawal velocity: INR {burn_rate:.0f}/hr",
                f"Crowdsourced signals (Net Score: {net_signal:+d})"
            ]

            if final_score >= 80:
                confidence_level = "HIGH"
                badge_color = "green"
            elif final_score >= 45:
                confidence_level = "MEDIUM"
                badge_color = "yellow"
            else:
                confidence_level = "LOW"
                badge_color = "red"

            return {
                "cash_point_id": cash_point.id,
                "cash_point_name": cash_point.name,
                "is_fulfillable": True,
                "probability_score": final_score,
                "confidence_level": confidence_level,
                "badge_color": badge_color,
                "current_balance": cash_point.current_cash_balance,
                "reasons": reasons
            }
        except Exception as e:
            print(f"[ML INFERENCE ERROR] Falling back to heuristic engine: {e}")

    # Fallback Heuristic Logic
    score = 50.0
    reasons = ["Fallback heuristic prediction"]
    if pos_pings_count > 0:
        score += 30.0
    if fail_pings_count > 0:
        score -= (fail_pings_count * 25.0)

    final_score = int(round(max(5.0, min(99.0, score))))
    badge_color = "green" if final_score >= 80 else ("yellow" if final_score >= 45 else "red")
    confidence_level = "HIGH" if final_score >= 80 else ("MEDIUM" if final_score >= 45 else "LOW")

    return {
        "cash_point_id": cash_point.id,
        "cash_point_name": cash_point.name,
        "is_fulfillable": True,
        "probability_score": final_score,
        "confidence_level": confidence_level,
        "badge_color": badge_color,
        "current_balance": cash_point.current_cash_balance,
        "reasons": reasons
    }
