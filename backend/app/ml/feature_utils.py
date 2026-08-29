# backend/app/ml/feature_utils.py
"""
Shared feature-engineering logic for the cash-availability model.

CRITICAL: This module is imported by BOTH the offline training script
(train_model.py) and the live inference path (prediction_service.py) so
that a feature has exactly one definition. Previously, train_model.py and
prediction_service.py each computed features independently and had quietly
drifted apart (train/serve skew) -- e.g. `is_onsite` was computed one way
at train time (string match on 'HDFC'/'SBI') and a different way at serve
time (CashPointType.ATM). If you change a feature here, retrain the model.
"""
import numpy as np
import pandas as pd

# No real per-ATM float-capacity data is available in the current dataset
# (historical_atm_transactions.csv has no balance/capacity column). This is
# a documented placeholder assumption, not a measured value -- replace with
# real capacity data (e.g. from bank disclosures or RBI filings) if it
# becomes available.
STANDARD_FLOAT_LIMIT_DEFAULT = 100000.0

# Known major-bank brand prefixes, taken from the training data's atm_id
# naming convention (e.g. "HDFC_Koramangala_01") and cross-checked against
# the "brand" tags in osm_atms_bangalore.json. Anything that doesn't match
# falls into brand_OTHER, so the feature still works for ATMs/merchants the
# model has never seen by name -- unlike one-hot encoding atm_id directly,
# which would only "know" the 5 ATMs in the training set and be useless for
# the other ~318 ATMs in osm_atms_bangalore.json.
KNOWN_BANK_BRANDS = ["HDFC", "SBI", "ICICI", "AXIS", "KOTAK"]
BRAND_COLUMNS = [f"brand_{b}" for b in KNOWN_BANK_BRANDS] + ["brand_OTHER"]

FEATURE_COLUMNS = [
    "capacity_ratio",
    "amount_ratio",
    "burn_rate",
    "hours_since_refill",
    "hour_sin",
    "hour_cos",
    "net_signal",
    "is_weekend",
    "is_salary_day",
    "is_onsite",
] + BRAND_COLUMNS

# Monotonic constraints for HistGradientBoostingClassifier (sklearn >= 1.2),
# in the same order as FEATURE_COLUMNS.
#   +1 = predicted probability must NOT decrease as the feature increases
#   -1 = predicted probability must NOT increase as the feature increases
#    0 = unconstrained
# These encode domain knowledge the training data alone can't fully pin
# down with only 5 ATMs, and they also make the "reasons" shown in the UI
# defensible (e.g. we can promise the score never drops when the ATM has
# strictly more cash, all else equal).
MONOTONIC_CONSTRAINTS = (
    [
        1,  # capacity_ratio: more cash on hand -> not less likely to succeed
        -1,  # amount_ratio: bigger ask relative to balance -> not more likely to succeed
        -1,  # burn_rate: faster recent depletion -> not more likely to succeed
        0,  # hours_since_refill: non-monotonic (freshly refilled AND long-stable both look fine)
        0,  # hour_sin
        0,  # hour_cos
        1,  # net_signal: more positive crowd/success signal -> not less likely to succeed
        0,  # is_weekend
        0,  # is_salary_day
        0,  # is_onsite
    ]
    + [0] * len(BRAND_COLUMNS)
)


def extract_brand(identifier: str) -> str:
    """Map an ATM id / cash point name to a known bank brand, or OTHER."""
    ident_upper = str(identifier).upper()
    for brand in KNOWN_BANK_BRANDS:
        if brand in ident_upper:
            return brand
    return "OTHER"


def build_feature_row(
    *,
    current_cash_balance: float,
    standard_float_limit: float,
    requested_amount: float,
    withdrawn_prior_2h: float,
    hours_since_refill: float,
    hour_of_day: int,
    success_count_6h_prior: float,
    fail_count_1h_prior: float,
    is_weekend: int,
    is_salary_day: int,
    is_onsite: int,
    identifier: str,
) -> dict:
    """
    Build a single feature row as a plain dict.

    Called once per historical row during training and once per live
    request during inference -- same function, same math, both times.

    IMPORTANT (leakage): every argument here must be information that was
    genuinely knowable *before* the outcome you're trying to predict.
    `current_cash_balance` is the balance BEFORE this request/hour is
    served; `withdrawn_prior_2h`, `success_count_6h_prior` and
    `fail_count_1h_prior` must only summarize PAST rows, never the
    current one.
    """
    capacity_ratio = min(1.0, max(0.0, current_cash_balance / max(1.0, standard_float_limit)))
    amount_ratio = min(5.0, max(0.0, requested_amount / max(1.0, current_cash_balance)))
    burn_rate = withdrawn_prior_2h / 2.0
    hour_sin = np.sin(2 * np.pi * hour_of_day / 24.0)
    hour_cos = np.cos(2 * np.pi * hour_of_day / 24.0)
    net_signal = success_count_6h_prior - (2 * fail_count_1h_prior)

    row = {
        "capacity_ratio": capacity_ratio,
        "amount_ratio": amount_ratio,
        "burn_rate": burn_rate,
        "hours_since_refill": max(0.0, hours_since_refill),
        "hour_sin": hour_sin,
        "hour_cos": hour_cos,
        "net_signal": net_signal,
        "is_weekend": int(is_weekend),
        "is_salary_day": int(is_salary_day),
        "is_onsite": int(is_onsite),
    }
    brand = extract_brand(identifier)
    for b in KNOWN_BANK_BRANDS:
        row[f"brand_{b}"] = int(brand == b)
    row["brand_OTHER"] = int(brand == "OTHER")
    return row


def to_model_frame(row_dict: dict) -> pd.DataFrame:
    """Single-row DataFrame with columns in the exact order the model expects."""
    return pd.DataFrame([row_dict])[FEATURE_COLUMNS]