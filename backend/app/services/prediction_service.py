# backend/app/services/prediction_service.py
import os
import pickle
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session

from app.models.models import CashPoint, CashPointType, TelemetryPing, PingStatus, Transaction, TransactionStatus, TransactionType
from app.ml.feature_utils import (
    FEATURE_COLUMNS,
    STANDARD_FLOAT_LIMIT_DEFAULT,
    build_feature_row,
    to_model_frame,
)

# Load trained ML model bundle if available.
# The bundle is a dict: {"model": <calibrated sklearn estimator>,
# "feature_columns": [...], "trained_at": ..., "eval_metrics": {...}}
# saved by app/ml/train_model.py -- NOT a bare model, so an old-format
# cash_model.pkl from before this change will need retraining.
MODEL_PATH = os.path.join(os.path.dirname(__file__), "../ml/cash_model.pkl")
ml_model = None
model_trained_at = None

if os.path.exists(MODEL_PATH):
    try:
        with open(MODEL_PATH, "rb") as f:
            bundle = pickle.load(f)
        ml_model = bundle["model"]
        model_trained_at = bundle.get("trained_at")
        print(f"[ML SERVICE] Successfully loaded calibrated model (trained_at={model_trained_at}) from {MODEL_PATH}")
    except Exception as e:
        print(f"[ML SERVICE WARNING] Failed to load model artifact: {e}")


def calculate_cash_probability(
    db: Session,
    cash_point: CashPoint,
    requested_amount: float
) -> Dict[str, Any]:
    """
    Predicts cash availability using the trained, calibrated Gradient
    Boosted model, falling back to heuristic scoring if the ML model is
    unavailable.
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

    def make_utc(dt: Optional[datetime]) -> Optional[datetime]:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    six_hours_ago = now - timedelta(hours=6)
    one_hour_ago = now - timedelta(hours=1)
    two_hours_ago = now - timedelta(hours=2)

    pos_pings_count = (
        db.query(TelemetryPing)
        .filter(
            TelemetryPing.cash_point_id == cash_point.id,
            TelemetryPing.status == PingStatus.GOT_CASH,
            TelemetryPing.timestamp >= six_hours_ago
        )
        .count()
    )

    fail_pings_count = (
        db.query(TelemetryPing)
        .filter(
            TelemetryPing.cash_point_id == cash_point.id,
            TelemetryPing.status.in_([PingStatus.OUT_OF_CASH, PingStatus.MACHINE_BROKEN]),
            TelemetryPing.timestamp >= one_hour_ago
        )
        .count()
    )

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

    standard_float_limit = cash_point.standard_float_limit or STANDARD_FLOAT_LIMIT_DEFAULT
    is_onsite = 1 if cash_point.type == CashPointType.ATM else 0

    # 2. ML Model Inference
    if ml_model is not None:
        try:
            # NOTE on scale-matching: the training data was hourly, so its
            # "prior success/failure" signals were inherently 0-6 and 0-1
            # respectively (see train_model.py). Live telemetry pings don't
            # have that ceiling, so we clip here to keep inputs in the range
            # the model was actually trained on. If/when a real historical
            # ping dataset is available, retrain on raw counts instead of
            # this proxy and drop the clipping.
            success_count_6h_prior = min(6, pos_pings_count)
            fail_count_1h_prior = min(1, fail_pings_count)

            feature_row = build_feature_row(
                current_cash_balance=cash_point.current_cash_balance,
                standard_float_limit=standard_float_limit,
                requested_amount=requested_amount,
                withdrawn_prior_2h=total_withdrawn_2h,
                hours_since_refill=hours_since_refill,
                hour_of_day=now.hour,
                success_count_6h_prior=success_count_6h_prior,
                fail_count_1h_prior=fail_count_1h_prior,
                is_weekend=1 if now.weekday() >= 5 else 0,
                is_salary_day=1 if now.day <= 5 else 0,
                is_onsite=is_onsite,
                identifier=cash_point.name,
            )
            feature_df = to_model_frame(feature_row)

            # predict_proba on a CalibratedClassifierCV bundle returns
            # probabilities that were fit to match observed frequencies on
            # a held-out calibration split (see train_model.py) -- so, unlike
            # the previous version, we do NOT apply any further ad-hoc
            # adjustment on top of this number. Stacking a manual penalty
            # (e.g. "-0.25 per failure ping") on an already-calibrated
            # probability would break that calibration guarantee and make
            # the displayed percentage untrustworthy again. The failure-ping
            # signal is already an input to the model via `net_signal`,
            # which is monotonically constrained so more failures can never
            # increase the score.
            raw_prob = ml_model.predict_proba(feature_df)[0][1]
            final_score = int(round(raw_prob * 100))
            final_score = max(5, min(99, final_score))

            reasons = [
                f"ML Engine prediction based on live capacity ratio ({feature_row['capacity_ratio']*100:.0f}%)",
                f"Recent withdrawal velocity: INR {feature_row['burn_rate']:.0f}/hr",
                f"Crowdsourced signals (Net Score: {feature_row['net_signal']:+.0f})"
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