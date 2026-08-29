# backend/app/api/upi.py
from datetime import timezone
import io
import base64
import qrcode
from uuid import uuid4
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import CashPoint
from app.schemas.schemas import WithdrawalRequest, WithdrawalResponse
from app.services.withdrawal_service import process_withdrawal

router = APIRouter(prefix="/api/upi", tags=["UPI & Withdrawal"])

def generate_qr_base64(upi_uri: str) -> str:
    """Generates a base64 encoded PNG image string for a given UPI intent URI."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(upi_uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_str}"

@router.post("/withdraw", response_model=WithdrawalResponse)
def initiate_upi_withdrawal(
    req: WithdrawalRequest,
    db: Session = Depends(get_db)
):
    """
    Initiates a cardless cash withdrawal via UPI:
    1. Validates cash point availability and deducts cash float balance.
    2. Generates a unique UPI transaction reference (upi_ref).
    3. Constructs an NPCI-compliant UPI Intent URI (upi://pay?pa=...).
    4. Renders a base64 PNG QR code payload for desktop scanning or mobile deep-linking.
    """
    cash_point = db.query(CashPoint).filter(CashPoint.id == req.cash_point_id).first()
    if not cash_point:
        raise HTTPException(status_code=404, detail="Cash point not found")

    if not cash_point.is_active:
        raise HTTPException(status_code=400, detail="Cash point is currently inactive")

    # Generate unique transaction reference
    upi_ref = f"CF_TX_{uuid4().hex[:10].upper()}"

    try:
        # Process withdrawal & deduct balance in database
        tx = process_withdrawal(
            db=db,
            cash_point_id=req.cash_point_id,
            amount=req.amount,
            upi_ref=upi_ref
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Payee UPI VPA (fallback to default merchant VPA if not configured)
    payee_vpa = cash_point.upi_id or "cashfinder@upi"
    payee_name = quote(cash_point.name)
    note = quote(f"CashWithdrawal_{tx.id}")

    # Standard NPCI UPI URI string
    upi_intent_uri = (
        f"upi://pay?pa={payee_vpa}&pn={payee_name}"
        f"&am={req.amount:.2f}&cu=INR&tn={note}&tr={upi_ref}&mc=6011"
    )

    # Generate base64 QR code image payload
    qr_code_base64 = generate_qr_base64(upi_intent_uri)

    return WithdrawalResponse(
        transaction_id=tx.id,
        cash_point_id=cash_point.id,
        cash_point_name=cash_point.name,
        amount_requested=tx.amount_requested,
        status=tx.status,
        upi_ref=upi_ref,
        upi_intent_uri=upi_intent_uri,
        qr_code_base64=qr_code_base64,
        remaining_balance=cash_point.current_cash_balance,
        timestamp=tx.timestamp or datetime.now(timezone.utc)
    )
