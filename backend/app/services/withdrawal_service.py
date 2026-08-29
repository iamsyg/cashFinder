# backend/app/services/withdrawal_service.py

# backend/app/services/withdrawal_service.py
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.models import CashPoint, Transaction, TransactionStatus, TransactionType, TelemetryPing, PingStatus

def process_withdrawal(db: Session, cash_point_id: int, amount: float, upi_ref: str = None) -> Transaction:
    """
    Process a cash withdrawal request:
    1. Checks if the cash point has sufficient balance.
    2. Deducts the withdrawn amount from current_cash_balance and updates total_cash_withdrawn.
    3. Records a successful Transaction and TelemetryPing.
    """
    cash_point = db.query(CashPoint).filter(CashPoint.id == cash_point_id).first()
    if not cash_point:
        raise ValueError("Cash point not found")

    if not cash_point.is_active:
        raise ValueError("Cash point is currently inactive")

    # Create failed transaction record
    now = datetime.now(timezone.utc)
    if cash_point.current_cash_balance < amount:
        tx = Transaction(
            cash_point_id=cash_point_id,
            type=TransactionType.WITHDRAWAL,
            amount_requested=amount,
            status=TransactionStatus.FAILED,
            upi_ref=upi_ref,
            timestamp=now
        )
        db.add(tx)
        
        ping = TelemetryPing(
            cash_point_id=cash_point_id,
            status=PingStatus.OUT_OF_CASH,
            amount_withdrawn=None,
            note="Insufficient balance for withdrawal",
            timestamp=now
        )
        db.add(ping)
        db.commit()
        return tx

    # Sufficient balance -> Deduct cash balance & accumulate total withdrawn
    cash_point.current_cash_balance -= amount
    cash_point.total_cash_withdrawn += amount

    # Create successful transaction
    tx = Transaction(
        cash_point_id=cash_point_id,
        type=TransactionType.WITHDRAWAL,
        amount_requested=amount,
        status=TransactionStatus.SUCCESS,
        upi_ref=upi_ref,
        timestamp=now
    )
    db.add(tx)

    # Create telemetry ping confirming cash dispense
    ping = TelemetryPing(
        cash_point_id=cash_point_id,
        status=PingStatus.GOT_CASH,
        amount_withdrawn=amount,
        note="Withdrawal successful",
        timestamp=now
    )
    db.add(ping)

    db.commit()
    db.refresh(cash_point)
    db.refresh(tx)
    return tx

def process_deposit(db: Session, cash_point_id: int, amount: float, upi_ref: str = None) -> Transaction:
    """
    Process a cash deposit/addition:
    1. Validates that current_cash_balance + amount does not exceed standard_float_limit.
    2. Increases current_cash_balance and total_cash_deposited.
    3. Logs a DEPOSIT transaction record.
    """
    now = datetime.now(timezone.utc)
    if amount <= 0:
        raise ValueError("Deposit amount must be positive")

    cash_point = db.query(CashPoint).filter(CashPoint.id == cash_point_id).first()
    if not cash_point:
        raise ValueError("Cash point not found")

    if cash_point.current_cash_balance + amount > cash_point.standard_float_limit:
        raise ValueError(
            f"Deposit of INR {amount} exceeds max float capacity limit of INR {cash_point.standard_float_limit}. "
            f"Current space available: INR {cash_point.standard_float_limit - cash_point.current_cash_balance}"
        )

    cash_point.current_cash_balance += amount
    cash_point.total_cash_deposited += amount

    tx = Transaction(
        cash_point_id=cash_point_id,
        type=TransactionType.DEPOSIT,
        amount_requested=amount,
        status=TransactionStatus.SUCCESS,
        upi_ref=upi_ref,
        timestamp=now
    )
    db.add(tx)

    ping = TelemetryPing(
        cash_point_id=cash_point_id,
        status=PingStatus.GOT_CASH,
        amount_withdrawn=None,
        note=f"Deposited/Added cash: INR {amount}",
        timestamp=now
    )
    db.add(ping)

    db.commit()
    db.refresh(cash_point)
    db.refresh(tx)
    return tx

def refill_cash_point(db: Session, cash_point_id: int, new_balance: float = None, add_amount: float = None) -> CashPoint:
    """
    Refill or set exact cash float for a cash point:
    - Raises ValueError if both new_balance and add_amount are None.
    - Raises ValueError if the resulting cash balance exceeds standard_float_limit.
    """
    if new_balance is None and add_amount is None:
        raise ValueError("Must specify either new_balance or add_amount")

    cash_point = db.query(CashPoint).filter(CashPoint.id == cash_point_id).first()
    if not cash_point:
        raise ValueError("Cash point not found")

    now = datetime.now(timezone.utc)

    if new_balance is not None:
        if new_balance < 0:
            raise ValueError("New balance cannot be negative")
        if new_balance > cash_point.standard_float_limit:
            raise ValueError(
                f"New balance INR {new_balance} exceeds maximum capacity limit of INR {cash_point.standard_float_limit}"
            )
        cash_point.current_cash_balance = new_balance
        cash_point.last_refilled_amount = new_balance

    elif add_amount is not None:
        if add_amount <= 0:
            raise ValueError("Add amount must be positive")
        if cash_point.current_cash_balance + add_amount > cash_point.standard_float_limit:
            raise ValueError(
                f"Adding INR {add_amount} exceeds maximum capacity limit of INR {cash_point.standard_float_limit}"
            )
        cash_point.current_cash_balance += add_amount
        cash_point.last_refilled_amount = add_amount
        cash_point.total_cash_deposited += add_amount

    cash_point.last_refilled_at = now

    ping = TelemetryPing(
        cash_point_id=cash_point_id,
        status=PingStatus.GOT_CASH,
        amount_withdrawn=None,
        note=f"Refilled cash float. New balance: INR {cash_point.current_cash_balance}",
        timestamp=now
    )
    db.add(ping)

    db.commit()
    db.refresh(cash_point)
    return cash_point
