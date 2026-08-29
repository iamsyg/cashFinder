# backend/tests/test_all_apis.py
import urllib.request
import json

BASE_URL = "http://localhost:8000"

def test_full_api_suite():
    print("=" * 75)
    print("RUNNING END-TO-END API TEST SUITE (CASHPOINTS, TELEMETRY, UPI WITHDRAWAL)")
    print("=" * 75)

    # 1. GET /api/cashpoints
    get_url = f"{BASE_URL}/api/cashpoints?lat=12.9352&lng=77.6245&radius_km=5.0&amount=2000.0"
    print(f"\n[1. GET /api/cashpoints] -> {get_url}")
    req = urllib.request.Request(get_url)
    with urllib.request.urlopen(req) as resp:
        cps = json.loads(resp.read().decode())
        print(f"HTTP Status: {resp.status} | Retrieved {len(cps)} cash points.")
        assert len(cps) > 0
        target = cps[0]
        target_id = target['id']
        initial_bal = target['current_cash_balance']
        print(f"Target Point: '{target['name']}' (ID: {target_id}) | Initial Float: INR {initial_bal}")

    # 2. POST /api/telemetry
    tel_url = f"{BASE_URL}/api/telemetry"
    print(f"\n[2. POST /api/telemetry] -> Submitting GOT_CASH report for CashPoint #{target_id}")
    tel_payload = json.dumps({
        "cash_point_id": target_id,
        "status": "GOT_CASH",
        "amount_withdrawn": 2000.0,
        "note": "Smooth withdrawal via UPI"
    }).encode('utf-8')

    req_tel = urllib.request.Request(tel_url, data=tel_payload, headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req_tel) as resp_tel:
        ping_res = json.loads(resp_tel.read().decode())
        print(f"HTTP Status: {resp_tel.status} | Ping Created (ID: {ping_res['id']})")
        assert ping_res['cash_point_id'] == target_id

    # 3. GET /api/telemetry/{cash_point_id}
    tel_hist_url = f"{BASE_URL}/api/telemetry/{target_id}"
    print(f"\n[3. GET /api/telemetry/{target_id}] -> Fetching ping history")
    req_hist = urllib.request.Request(tel_hist_url)
    with urllib.request.urlopen(req_hist) as resp_hist:
        hist_data = json.loads(resp_hist.read().decode())
        print(f"HTTP Status: {resp_hist.status} | Total pings retrieved: {len(hist_data)}")
        assert len(hist_data) > 0

    # 4. POST /api/upi/withdraw
    withdraw_url = f"{BASE_URL}/api/upi/withdraw"
    withdraw_amount = 2000.0
    print(f"\n[4. POST /api/upi/withdraw] -> Initiating INR {withdraw_amount} withdrawal for CashPoint #{target_id}")
    withdraw_payload = json.dumps({
        "cash_point_id": target_id,
        "amount": withdraw_amount
    }).encode('utf-8')

    req_w = urllib.request.Request(withdraw_url, data=withdraw_payload, headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req_w) as resp_w:
        w_res = json.loads(resp_w.read().decode())
        print(f"HTTP Status: {resp_w.status}")
        print(f"Transaction ID: {w_res['transaction_id']} | Status: {w_res['status']}")
        print(f"UPI Ref: {w_res['upi_ref']}")
        print(f"UPI Intent URI: {w_res['upi_intent_uri']}")
        print(f"QR Base64 Length: {len(w_res['qr_code_base64'])} chars")
        print(f"Remaining Float Balance: INR {w_res['remaining_balance']}")
        
        expected_bal = initial_bal - withdraw_amount
        assert w_res['remaining_balance'] == expected_bal, f"Expected {expected_bal}, got {w_res['remaining_balance']}"
        assert w_res['upi_intent_uri'].startswith("upi://pay?")
        assert w_res['qr_code_base64'].startswith("data:image/png;base64,")

    print("\n" + "=" * 75)
    print("[SUCCESS] All API endpoints (CashPoints, Telemetry, UPI Withdraw) verified!")

if __name__ == "__main__":
    test_full_api_suite()
