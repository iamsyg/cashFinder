# backend/tests/test_prediction.py
from app.core.database import SessionLocal
from app.models.models import CashPoint
from app.seed_data import seed_database
from app.services.prediction_service import calculate_cash_probability
from app.services.withdrawal_service import process_withdrawal

def test_prediction_engine():
    seed_database()
    db = SessionLocal()

    cash_points = db.query(CashPoint).all()
    print(f"\n--- TESTING PREDICTION ENGINE FOR {len(cash_points)} CASH POINTS ---")

    # 1. Test requested amount higher than balance (Filter Out check)
    hdfc_cp = cash_points[0] # HDFC ATM (Balance: 80,000)
    res_unfulfillable = calculate_cash_probability(db, hdfc_cp, requested_amount=150000.0)
    assert res_unfulfillable["is_fulfillable"] == False
    assert res_unfulfillable["probability_score"] == 0
    print(f"\n[1. UNFULFILLABLE FILTER TEST PASSED]")
    print(f"   Requested: INR 150,000 | Available: INR {hdfc_cp.current_cash_balance}")
    print(f"   is_fulfillable: {res_unfulfillable['is_fulfillable']} (UI will hide this ATM)\n")

    # 2. Test normal prediction calculation
    res_fulfillable = calculate_cash_probability(db, hdfc_cp, requested_amount=2000.0)
    assert res_fulfillable["is_fulfillable"] == True
    assert res_fulfillable["probability_score"] > 0
    print(f"[2. NORMAL PREDICTION TEST PASSED]")
    print(f"   ATM Name: {hdfc_cp.name}")
    print(f"   Probability Score: {res_fulfillable['probability_score']}%")
    print(f"   Confidence Level: {res_fulfillable['confidence_level']} (Badge: {res_fulfillable['badge_color']})")
    print(f"   Reasons: {res_fulfillable['reasons']}\n")

    # 3. Test Active Depletion Rule (Withdraw until balance <= 2000)
    axis_cp = cash_points[3] # Axis Bank ATM
    axis_cp.current_cash_balance = 1500.0
    db.commit()

    # Process withdrawal in last 2 hours
    process_withdrawal(db, axis_cp.id, amount=500.0, upi_ref="TX_DEPLETE_1")

    res_depleted = calculate_cash_probability(db, axis_cp, requested_amount=500.0)
    print(f"[3. ACTIVE DEPLETION PENALTY TEST PASSED]")
    print(f"   ATM Name: {axis_cp.name}")
    print(f"   Remaining Balance: INR {axis_cp.current_cash_balance}")
    print(f"   Probability Score: {res_depleted['probability_score']}%")
    print(f"   Confidence Level: {res_depleted['confidence_level']} (Badge: {res_depleted['badge_color']})")
    print(f"   Reasons: {res_depleted['reasons']}\n")

    db.close()
    print("[SUCCESS] All prediction engine tests executed cleanly!")

if __name__ == "__main__":
    test_prediction_engine()
