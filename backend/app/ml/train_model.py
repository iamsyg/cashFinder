# backend/app/ml/train_model.py
import os
import pickle
from collections import deque

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report, roc_auc_score, brier_score_loss

try:
    from .feature_utils import (
        FEATURE_COLUMNS,
        MONOTONIC_CONSTRAINTS,
        STANDARD_FLOAT_LIMIT_DEFAULT,
        build_feature_row,
    )
except ImportError:  # allows `python train_model.py` as a standalone script too
    from feature_utils import (
        FEATURE_COLUMNS,
        MONOTONIC_CONSTRAINTS,
        STANDARD_FLOAT_LIMIT_DEFAULT,
        build_feature_row,
    )

try:
    from sklearn.frozen import FrozenEstimator
    _HAS_FROZEN_ESTIMATOR = True
except ImportError:  # sklearn < 1.6
    _HAS_FROZEN_ESTIMATOR = False

RANDOM_SEED = 42

# The raw dataset is hourly per-ATM AGGREGATES (transaction_count,
# total_withdrawn_inr, success_status) -- it has no per-request granularity.
# To train a model that answers "what's the probability THIS specific
# requested amount succeeds", we still need to inject a synthetic per-request
# amount. This is an unavoidable simplification given the data we have; the
# label below is constructed so the REAL recorded success_status dominates.
WITHDRAWAL_OPTIONS = np.array([500.0, 1000.0, 2000.0, 5000.0, 10000.0])
WITHDRAWAL_PROBS = [0.2, 0.3, 0.3, 0.15, 0.05]


def simulate_and_engineer(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    One chronological pass per ATM that:

    1. Simulates a running cash balance, anchored to the REAL recorded
       `success_status` column: a recorded stockout (success_status == 0)
       forces a refill on the NEXT row, instead of an arbitrary invented
       threshold like "balance < 2000". This ties the synthetic balance
       track to ground truth instead of being fully made up.

    2. Builds every engineered feature from ONLY the rows that came before
       the one being labeled (via small rolling deques). This is the fix
       for the leakage in the original pipeline, where "positive_pings_6h"
       / "failure_pings_1h" / burn_rate were derived from the same row
       whose outcome they were meant to predict.
    """
    rng = np.random.default_rng(RANDOM_SEED)
    df = raw_df.sort_values(["atm_id", "timestamp"]).reset_index(drop=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["requested_amount"] = rng.choice(WITHDRAWAL_OPTIONS, size=len(df), p=WITHDRAWAL_PROBS)

    rows = []
    labels = []

    for atm_id, group in df.groupby("atm_id", sort=False):
        capacity = STANDARD_FLOAT_LIMIT_DEFAULT
        current_bal = capacity
        last_refill_ts = group["timestamp"].iloc[0]
        prior_stockout = False

        # Rolling history -- contains ONLY past rows for this ATM at any point
        success_hist_6h = deque(maxlen=6)
        withdrawn_hist_2h = deque(maxlen=2)

        for _, row in group.iterrows():
            ts = row["timestamp"]
            hrs_since_refill = (ts - last_refill_ts).total_seconds() / 3600.0

            if prior_stockout or hrs_since_refill >= 24.0:
                current_bal = capacity
                last_refill_ts = ts
                hrs_since_refill = 0.0

            success_count_6h_prior = float(sum(success_hist_6h))
            fail_count_1h_prior = 1.0 if (len(success_hist_6h) > 0 and success_hist_6h[-1] == 0) else 0.0
            withdrawn_prior_2h = float(sum(withdrawn_hist_2h))

            feature_row = build_feature_row(
                current_cash_balance=current_bal,
                standard_float_limit=capacity,
                requested_amount=row["requested_amount"],
                withdrawn_prior_2h=withdrawn_prior_2h,
                hours_since_refill=hrs_since_refill,
                hour_of_day=row["hour_of_day"],
                success_count_6h_prior=success_count_6h_prior,
                fail_count_1h_prior=fail_count_1h_prior,
                is_weekend=row["is_weekend"],
                is_salary_day=row["is_salary_day"],
                # All 5 ATMs in this dataset are bank-branch machines; the
                # training data contains NO merchant/off-site examples at
                # all (see README caveat), so is_onsite=0 is never seen
                # during training.
                is_onsite=1,
                identifier=atm_id,
            )
            feature_row["timestamp"] = ts
            feature_row["atm_id"] = atm_id
            rows.append(feature_row)

            # Label: the REAL recorded outcome must be a success AND the
            # simulated balance must cover the simulated requested amount.
            # A recorded failure (success_status == 0) always forces
            # label = 0, regardless of the synthetic balance/amount.
            label = 1 if (row["success_status"] == 1 and current_bal >= row["requested_amount"]) else 0
            labels.append(label)

            # Advance state using this row's real, now-known outcome. This
            # happens AFTER the feature row above was built, so it never
            # leaks into that row's own features.
            withdrawn_capped = min(row["total_withdrawn_inr"], current_bal)
            current_bal = max(0.0, current_bal - withdrawn_capped)
            prior_stockout = row["success_status"] == 0

            success_hist_6h.append(row["success_status"])
            withdrawn_hist_2h.append(row["total_withdrawn_inr"])

    feat_df = pd.DataFrame(rows)
    feat_df["label"] = labels
    return feat_df


def chronological_split(feat_df: pd.DataFrame, train_frac: float = 0.70, calib_frac: float = 0.15):
    """
    Time-based split shared across all ATMs (they cover the same date
    range in this dataset). A random row split would put adjacent-in-time
    rows from the same ATM's depletion cycle into both train and test,
    letting the model partially "memorize" the cycle it's evaluated on.
    """
    dates = feat_df["timestamp"]
    train_cutoff = dates.quantile(train_frac)
    calib_cutoff = dates.quantile(train_frac + calib_frac)

    train_df = feat_df[feat_df["timestamp"] <= train_cutoff]
    calib_df = feat_df[(feat_df["timestamp"] > train_cutoff) & (feat_df["timestamp"] <= calib_cutoff)]
    test_df = feat_df[feat_df["timestamp"] > calib_cutoff]
    return train_df, calib_df, test_df


def train_and_save_model():
    data_path = os.path.join(os.path.dirname(__file__), "../../../data/historical_atm_transactions.csv")
    if not os.path.exists(data_path):
        print(f"Error: Dataset not found at {data_path}")
        return

    print(f"Loading raw dataset from {data_path}...")
    raw_df = pd.read_csv(data_path)

    print("Simulating balances and building leakage-safe, lagged features...")
    feat_df = simulate_and_engineer(raw_df)

    print("Splitting chronologically into train / calibration / test (70/15/15)...")
    train_df, calib_df, test_df = chronological_split(feat_df)
    print(f"  train={len(train_df)}  calib={len(calib_df)}  test={len(test_df)}")

    X_train, y_train = train_df[FEATURE_COLUMNS], train_df["label"]
    X_calib, y_calib = calib_df[FEATURE_COLUMNS], calib_df["label"]
    X_test, y_test = test_df[FEATURE_COLUMNS], test_df["label"]

    print("Training Gradient Boosted Classifier with monotonic constraints...")
    base_model = HistGradientBoostingClassifier(
        max_iter=150,
        learning_rate=0.08,
        max_depth=6,
        monotonic_cst=MONOTONIC_CONSTRAINTS,
        random_state=RANDOM_SEED,
    )
    base_model.fit(X_train, y_train)

    print("Calibrating probabilities on the held-out calibration split...")
    # The UI shows this number to users as a literal percentage ("87%
    # chance"), so calibration matters as much as raw discrimination (AUC).
    # We fit the base model on X_train only, then fit isotonic calibration
    # on a SEPARATE calibration split so calibration isn't evaluated on data
    # the trees already memorized.
    if _HAS_FROZEN_ESTIMATOR:
        calibrated_model = CalibratedClassifierCV(FrozenEstimator(base_model), method="isotonic")
    else:  # sklearn < 1.6 fallback
        calibrated_model = CalibratedClassifierCV(base_model, method="isotonic", cv="prefit")
    calibrated_model.fit(X_calib, y_calib)

    # Evaluation on the chronologically final, untouched test split
    y_pred = calibrated_model.predict(X_test)
    y_proba = calibrated_model.predict_proba(X_test)[:, 1]
    auc_score = roc_auc_score(y_test, y_proba)
    brier = brier_score_loss(y_test, y_proba)

    print("\n--- RETRAINED MODEL EVALUATION REPORT (chronological hold-out) ---")
    print(f"ROC-AUC Score: {auc_score:.4f}")
    print(f"Brier Score (lower is better-calibrated, 0.25 = coin-flip baseline): {brier:.4f}")
    print("\nClassification Report:\n", classification_report(y_test, y_pred))

    model_dir = os.path.dirname(__file__)
    model_file = os.path.join(model_dir, "cash_model.pkl")
    bundle = {
        "model": calibrated_model,
        "feature_columns": FEATURE_COLUMNS,
        "trained_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "eval_metrics": {"roc_auc": float(auc_score), "brier_score": float(brier)},
    }
    with open(model_file, "wb") as f:
        pickle.dump(bundle, f)

    print(f"[SUCCESS] Calibrated model bundle saved to {model_file}")


if __name__ == "__main__":
    train_and_save_model()