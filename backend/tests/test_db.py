# backend/tests/test_db.py

# backend/tests/test_db.py
from app.core.database import SessionLocal
from app.models.models import CashPoint, Transaction, TransactionStatus, TransactionType
from app.seed_data import seed_database
from app.services.withdrawal_service import process_withdrawal, process_deposit, refill_cash_point

def test_full_cash_flow_and_validation():
    # 1. Seed database
    seed_database()
    db = SessionLocal()

    cash_points = db.query(CashPoint).all()
    first_cp = cash_points[0] # HDFC Bank ATM, capacity 100,000, starts at 80,000

    print(f"\n[1. INITIAL STATE] {first_cp.name}")
    print(f"   Max Capacity: INR {first_cp.standard_float_limit}")
    print(f"   Current Balance: INR {first_cp.current_cash_balance}\n")

    # 2. Test Withdrawal
    tx_w = process_withdrawal(db, first_cp.id, amount=10000.0, upi_ref="W1234")
    db.refresh(first_cp)
    assert tx_w.status == TransactionStatus.SUCCESS
    assert first_cp.current_cash_balance == 70000.0
    assert first_cp.total_cash_withdrawn == 10000.0
    print(f"[2. WITHDRAWAL] INR 10,000 withdrawn.")
    print(f"   Current Balance: INR {first_cp.current_cash_balance}")
    print(f"   Total Withdrawn: INR {first_cp.total_cash_withdrawn}\n")

    # 3. Test Deposit
    tx_d = process_deposit(db, first_cp.id, amount=15000.0, upi_ref="D5678")
    db.refresh(first_cp)
    assert tx_d.status == TransactionStatus.SUCCESS
    assert tx_d.type == TransactionType.DEPOSIT
    assert first_cp.current_cash_balance == 85000.0
    assert first_cp.total_cash_deposited == 15000.0
    print(f"[3. DEPOSIT] INR 15,000 deposited.")
    print(f"   Current Balance: INR {first_cp.current_cash_balance}")
    print(f"   Total Deposited: INR {first_cp.total_cash_deposited}\n")

    # 4. Test Validation: Refill with both arguments None
    try:
        refill_cash_point(db, first_cp.id)
        assert False, "Should have raised ValueError when both params are None"
    except ValueError as e:
        print(f"[4. VALIDATION PASSED] Caught expected error when both params are None: '{e}'")

    # 5. Test Validation: Exceeding standard_float_limit capacity
    try:
        refill_cash_point(db, first_cp.id, new_balance=150000.0)
        assert False, "Should have raised ValueError when exceeding capacity"
    except ValueError as e:
        print(f"[5. VALIDATION PASSED] Caught expected error on capacity overflow: '{e}'")

    db.close()
    print("\n[SUCCESS] Full double-entry cash flow & validation rules verified successfully!")

if __name__ == "__main__":
    test_full_cash_flow_and_validation()
