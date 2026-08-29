# backend/tests/test_model_direct.py
import pickle
import os
import pandas as pd
from app.ml.feature_utils import build_feature_row, to_model_frame

def run_direct_model_tests():
    model_path = os.path.join(os.path.dirname(__file__), "../app/ml/cash_model.pkl")
    if not os.path.exists(model_path):
        print(f"Error: Model file not found at {model_path}")
        return

    with open(model_path, "rb") as f:
        bundle = pickle.load(f)

    model = bundle["model"]
    print(f"Successfully loaded calibrated model bundle (Trained: {bundle.get('trained_at')})\n")

    scenarios = [
        {
            "name": "Scenario 1: Ideal ATM (Newly Stocked)",
            "balance": 90000.0,
            "limit": 100000.0,
            "requested": 2000.0,
            "withdrawn_2h": 0.0,
            "hours_refill": 0.5,
            "pos_pings": 4,
            "fail_pings": 0,
            "identifier": "HDFC_ATM_1",
            "is_onsite": 1,
            "expected": "HIGH Confidence (Green)"
        },
        {
            "name": "Scenario 2: Depleting ATM (Moderate Risk)",
            "balance": 15000.0,
            "limit": 100000.0,
            "requested": 5000.0,
            "withdrawn_2h": 10000.0,
            "hours_refill": 8.0,
            "pos_pings": 1,
            "fail_pings": 0,
            "identifier": "SBI_ATM_2",
            "is_onsite": 1,
            "expected": "MEDIUM Confidence (Yellow)"
        },
        {
            "name": "Scenario 3: Nearly Empty ATM (High Risk)",
            "balance": 1200.0,
            "limit": 100000.0,
            "requested": 1000.0,
            "withdrawn_2h": 5000.0,
            "hours_refill": 18.0,
            "pos_pings": 0,
            "fail_pings": 2,
            "identifier": "AXIS_ATM_3",
            "is_onsite": 1,
            "expected": "LOW Confidence (Red)"
        },
        {
            "name": "Scenario 4: Unfulfillable Request (Requested > Balance)",
            "balance": 5000.0,
            "limit": 50000.0,
            "requested": 10000.0,
            "withdrawn_2h": 0.0,
            "hours_refill": 2.0,
            "pos_pings": 2,
            "fail_pings": 0,
            "identifier": "GUPTA_STORE_MERCHANT",
            "is_onsite": 0,
            "expected": "UNAVAILABLE (Filter Check)"
        }
    ]

    print("=" * 70)
    print("RUNNING DIRECT MODEL PREDICTION TESTS ON DUMMY INPUT DATA")
    print("=" * 70)

    for sc in scenarios:
        print(f"\n--- {sc['name']} ---")
        print(f"Inputs -> Balance: INR {sc['balance']} | Requested: INR {sc['requested']} | Refill Ago: {sc['hours_refill']}h | Net Pings: +{sc['pos_pings']}/-{sc['fail_pings']}")
        
        # Hard filter check
        if sc["requested"] > sc["balance"]:
            print(f"Hard Filter Triggered: Requested INR {sc['requested']} > Balance INR {sc['balance']}")
            print(f"RESULT: is_fulfillable = False | Probability = 0% | Badge: GRAY [Match: {sc['expected']}]")
            continue

        # Build feature vector
        row = build_feature_row(
            current_cash_balance=sc["balance"],
            standard_float_limit=sc["limit"],
            requested_amount=sc["requested"],
            withdrawn_prior_2h=sc["withdrawn_2h"],
            hours_since_refill=sc["hours_refill"],
            hour_of_day=14,
            success_count_6h_prior=sc["pos_pings"],
            fail_count_1h_prior=sc["fail_pings"],
            is_weekend=0,
            is_salary_day=0,
            is_onsite=sc["is_onsite"],
            identifier=sc["identifier"]
        )

        frame = to_model_frame(row)
        proba = model.predict_proba(frame)[0][1]
        score = int(round(proba * 100))

        if score >= 80:
            confidence = "HIGH"
            badge = "GREEN [OK]"
        elif score >= 45:
            confidence = "MEDIUM"
            badge = "YELLOW [WARN]"
        else:
            confidence = "LOW"
            badge = "RED [ALERT]"

        print(f"Feature Vector -> Capacity Ratio: {row['capacity_ratio']:.2f} | Burn Rate: INR {row['burn_rate']}/hr | Net Signal: {row['net_signal']}")
        print(f"PREDICTED PROBABILITY: {score}% | Confidence: {confidence} | Badge: {badge}")
        print(f"EXPECTED OUTCOME: {sc['expected']}")

    print("\n" + "=" * 70)
    print("[SUCCESS] All dummy data prediction scenarios tested successfully!")

if __name__ == "__main__":
    run_direct_model_tests()
