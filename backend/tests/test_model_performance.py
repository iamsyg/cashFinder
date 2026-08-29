# backend/tests/test_model_performance.py
import os
import pickle
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    brier_score_loss,
    confusion_matrix,
)
from app.ml.feature_utils import build_feature_row, to_model_frame

def run_performance_and_fresh_dummy_tests():
    model_path = os.path.join(os.path.dirname(__file__), "../app/ml/cash_model.pkl")
    if not os.path.exists(model_path):
        print(f"Error: Model file not found at {model_path}")
        return

    with open(model_path, "rb") as f:
        bundle = pickle.load(f)

    model = bundle["model"]
    trained_at = bundle.get("trained_at")
    eval_metrics = bundle.get("eval_metrics", {})

    print("=" * 75)
    print("1. MODEL ARCHITECTURE & CHRONOLOGICAL HOLDOUT METRICS")
    print("=" * 75)
    print(f"Trained At: {trained_at}")
    print(f"Holdout ROC-AUC Score : {eval_metrics.get('roc_auc', 0.0):.4f}")
    print(f"Holdout Brier Score   : {eval_metrics.get('brier_score', 0.0):.4f} (Calibrated, 0 = Perfect, 0.25 = Coin-flip)")

    # 2. Generate a completely fresh, unseen synthetic test dataset (5,000 samples)
    print("\n" + "=" * 75)
    print("2. TESTING MODEL ON FRESH UNSEEN SYNTHETIC TEST SET (5,000 SAMPLES)")
    print("=" * 75)

    rng = np.random.default_rng(2026)
    n_samples = 5000

    balances = rng.uniform(500, 100000, size=n_samples)
    limits = np.full(n_samples, 100000.0)
    requests = rng.choice([500.0, 1000.0, 2000.0, 5000.0, 10000.0], size=n_samples, p=[0.2, 0.3, 0.3, 0.15, 0.05])
    withdrawn_2h = rng.uniform(0, 15000, size=n_samples)
    refill_hrs = rng.uniform(0.1, 30.0, size=n_samples)
    hours = rng.integers(0, 24, size=n_samples)
    pos_pings = rng.integers(0, 6, size=n_samples)
    fail_pings = rng.integers(0, 3, size=n_samples)
    is_weekend = rng.choice([0, 1], size=n_samples)
    is_salary = rng.choice([0, 1], size=n_samples)
    is_onsite = rng.choice([0, 1], size=n_samples)
    brands = rng.choice(["HDFC_ATM", "SBI_ATM", "ICICI_ATM", "AXIS_ATM", "KOTAK_ATM", "LOCAL_SHOP"], size=n_samples)

    # Build feature matrix
    rows = []
    ground_truth = []

    for i in range(n_samples):
        bal = balances[i]
        req = requests[i]
        cap = limits[i]
        fp = fail_pings[i]

        row = build_feature_row(
            current_cash_balance=bal,
            standard_float_limit=cap,
            requested_amount=req,
            withdrawn_prior_2h=withdrawn_2h[i],
            hours_since_refill=refill_hrs[i],
            hour_of_day=hours[i],
            success_count_6h_prior=pos_pings[i],
            fail_count_1h_prior=fp,
            is_weekend=is_weekend[i],
            is_salary_day=is_salary[i],
            is_onsite=is_onsite[i],
            identifier=brands[i]
        )
        rows.append(row)

        # Realistic Ground Truth Label
        has_balance = bal >= req
        low_float = (bal / cap) < 0.15
        has_neg = fp > 0

        if not has_balance:
            label = 0
        elif low_float or has_neg:
            fail_prob = 0.70 if (low_float and has_neg) else (0.50 if low_float else 0.40)
            label = 1 if rng.random() > fail_prob else 0
        else:
            label = 1

        ground_truth.append(label)

    feat_df = pd.DataFrame(rows)
    probas = model.predict_proba(feat_df)[:, 1]
    preds = (probas >= 0.50).astype(int)

    acc = accuracy_score(ground_truth, preds)
    prec = precision_score(ground_truth, preds)
    rec = recall_score(ground_truth, preds)
    f1 = f1_score(ground_truth, preds)
    auc = roc_auc_score(ground_truth, probas)
    brier = brier_score_loss(ground_truth, probas)
    cm = confusion_matrix(ground_truth, preds)

    print(f"Accuracy Score   : {acc * 100:.2f}%")
    print(f"Precision Score  : {prec * 100:.2f}%")
    print(f"Recall Score     : {rec * 100:.2f}%")
    print(f"F1-Score         : {f1:.4f}")
    print(f"ROC-AUC Score    : {auc:.4f}")
    print(f"Brier Loss Score : {brier:.4f}")
    print("\nConfusion Matrix:")
    print(f"  True Negatives  (Correct Empty/Fail) : {cm[0][0]}")
    print(f"  False Positives (Predicted OK, Failed): {cm[0][1]}")
    print(f"  False Negatives (Predicted Fail, OK)  : {cm[1][0]}")
    print(f"  True Positives  (Correct Success)    : {cm[1][1]}")

    # 3. New Edge Case Scenarios
    print("\n" + "=" * 75)
    print("3. TESTING ON NEW FRESH DUMMY EDGE CASE SCENARIOS")
    print("=" * 75)

    fresh_scenarios = [
        {
            "name": "Fresh Edge Case 1: High Balance, High Burn Rate (Payday Rush)",
            "balance": 75000.0, "limit": 100000.0, "req": 5000.0, "withdrawn_2h": 25000.0, "refill_hrs": 2.0, "pos": 5, "fail": 0, "onsite": 1, "id": "HDFC_KORAMANGALA"
        },
        {
            "name": "Fresh Edge Case 2: Small Merchant Micro-ATM (Low Capacity, Fresh Float)",
            "balance": 18000.0, "limit": 20000.0, "req": 2000.0, "withdrawn_2h": 1000.0, "refill_hrs": 0.2, "pos": 2, "fail": 0, "onsite": 0, "id": "KIRANA_STORE_MICROATM"
        },
        {
            "name": "Fresh Edge Case 3: ATM with Single Failure Ping & Moderate Balance",
            "balance": 25000.0, "limit": 100000.0, "req": 2000.0, "withdrawn_2h": 4000.0, "refill_hrs": 6.0, "pos": 2, "fail": 1, "onsite": 1, "id": "ICICI_INDIRANAGAR"
        },
        {
            "name": "Fresh Edge Case 4: Critically Low Balance Merchant (Rs. 800 left, asking Rs. 500)",
            "balance": 800.0, "limit": 20000.0, "req": 500.0, "withdrawn_2h": 3000.0, "refill_hrs": 12.0, "pos": 0, "fail": 1, "onsite": 0, "id": "LOCAL_PHARMACY_CASH"
        }
    ]

    for sc in fresh_scenarios:
        row = build_feature_row(
            current_cash_balance=sc["balance"],
            standard_float_limit=sc["limit"],
            requested_amount=sc["req"],
            withdrawn_prior_2h=sc["withdrawn_2h"],
            hours_since_refill=sc["refill_hrs"],
            hour_of_day=18,
            success_count_6h_prior=sc["pos"],
            fail_count_1h_prior=sc["fail"],
            is_weekend=1,
            is_salary_day=1,
            is_onsite=sc["onsite"],
            identifier=sc["id"]
        )
        frame = to_model_frame(row)
        proba = model.predict_proba(frame)[0][1]
        score = int(round(proba * 100))

        confidence = "HIGH" if score >= 80 else ("MEDIUM" if score >= 45 else "LOW")
        badge = "GREEN [OK]" if score >= 80 else ("YELLOW [WARN]" if score >= 45 else "RED [ALERT]")

        print(f"\n--- {sc['name']} ---")
        print(f"Inputs -> Bal: INR {sc['balance']} | Req: INR {sc['req']} | Burn 2h: INR {sc['withdrawn_2h']} | Fail Pings: {sc['fail']}")
        print(f"Features -> Capacity Ratio: {row['capacity_ratio']:.2f} | Net Signal: {row['net_signal']}")
        print(f"PREDICTED PROBABILITY: {score}% | Confidence: {confidence} | Badge: {badge}")

    print("\n" + "=" * 75)
    print("[SUCCESS] All performance metrics and fresh dummy scenarios evaluated!")

if __name__ == "__main__":
    run_performance_and_fresh_dummy_tests()
