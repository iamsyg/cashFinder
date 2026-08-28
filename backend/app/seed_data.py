# backend/app/seed_data.py

# backend/app/seed_data.py
import random
from datetime import datetime, timedelta, timezone
from app.core.database import Base, engine, SessionLocal
from app.models.models import CashPoint, CashPointType, TelemetryPing, PingStatus, Transaction, TransactionStatus

def seed_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Clear existing data
    db.query(Transaction).delete()
    db.query(TelemetryPing).delete()
    db.query(CashPoint).delete()
    db.commit()

    # Center location: Koramangala, Bangalore (12.9352° N, 77.6245° E)
    sample_cash_points = [
        # ATMs
        {"name": "HDFC Bank ATM - 80ft Road", "type": CashPointType.ATM, "lat": 12.9352, "lng": 77.6245, "limit": 100000.0, "upi": "hdfcatm80ft@hdfcbank"},
        {"name": "SBI ATM - Forum Mall Junction", "type": CashPointType.ATM, "lat": 12.9360, "lng": 77.6180, "limit": 150000.0, "upi": "sbi0012@sbi"},
        {"name": "ICICI Bank ATM - 5th Block", "type": CashPointType.ATM, "lat": 12.9310, "lng": 77.6290, "limit": 80000.0, "upi": "icici5th@icici"},
        {"name": "Axis Bank ATM - Sony World Signal", "type": CashPointType.ATM, "lat": 12.9378, "lng": 77.6262, "limit": 50000.0, "upi": "axissoyny@axisbank"},
        {"name": "Kotak Mahindra ATM - 100ft Road", "type": CashPointType.ATM, "lat": 12.9390, "lng": 77.6310, "limit": 40000.0, "upi": "kotak100ft@kotak"},
        
        # Merchant Cash Points
        {"name": "Gupta General Store & Cash Point", "type": CashPointType.MERCHANT, "lat": 12.9340, "lng": 77.6230, "limit": 20000.0, "upi": "guptastore@paytm"},
        {"name": "Nandi Medicals (Micro-ATM)", "type": CashPointType.MERCHANT, "lat": 12.9325, "lng": 77.6275, "limit": 15000.0, "upi": "nandimed@ybl"},
        {"name": "Sri Lakshmi Supermarket", "type": CashPointType.MERCHANT, "lat": 12.9385, "lng": 77.6220, "limit": 30000.0, "upi": "lakshmisuper@okicici"},
    ]

    created_points = []
    now = datetime.now(timezone.utc)
    for cp_data in sample_cash_points:
        cp = CashPoint(
            name=cp_data["name"],
            type=cp_data["type"],
            address="Koramangala, Bengaluru, Karnataka",
            latitude=cp_data["lat"],
            longitude=cp_data["lng"],
            standard_float_limit=cp_data["limit"],
            current_cash_balance=cp_data["limit"] * 0.8,  # Start at 80% capacity for realism
            last_refilled_amount=cp_data["limit"],
            last_refilled_at=now - timedelta(hours=random.randint(2, 12)),
            is_active=True,
            upi_id=cp_data["upi"],
        )
        db.add(cp)
        created_points.append(cp)

    db.commit()

    # Generate telemetry pings for each cash point
    now = datetime.now(timezone.utc)
    for cp in created_points:
        # Generate 3-6 historical pings over the last 2 hours
        for i in range(random.randint(3, 6)):
            ping_time = now - timedelta(minutes=random.randint(5, 120))
            
            # First ATM high chance of success, 4th ATM out of cash
            if "SBI" in cp.name or "Gupta" in cp.name:
                status = PingStatus.GOT_CASH
                amt = random.choice([500.0, 1000.0, 2000.0])
            elif "Axis" in cp.name:
                status = PingStatus.OUT_OF_CASH
                amt = None
            else:
                status = random.choice([PingStatus.GOT_CASH, PingStatus.GOT_CASH, PingStatus.OUT_OF_CASH])
                amt = 2000.0 if status == PingStatus.GOT_CASH else None

            ping = TelemetryPing(
                cash_point_id=cp.id,
                status=status,
                amount_withdrawn=amt,
                note="Simulated crowd report",
                timestamp=ping_time
            )
            db.add(ping)

    db.commit()
    db.close()
    print(f"Database successfully seeded with {len(created_points)} cash points!")

if __name__ == "__main__":
    seed_database()
