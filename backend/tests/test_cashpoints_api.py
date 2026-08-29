# backend/tests/test_cashpoints_api.py
import urllib.request
import json

BASE_URL = "http://localhost:8000"

def test_cashpoints_endpoints():
    print("=" * 70)
    print("TESTING CASHPOINTS API ENDPOINTS (GET, REFILL, DEPOSIT)")
    print("=" * 70)

    # 1. Test GET /api/cashpoints
    get_url = f"{BASE_URL}/api/cashpoints?lat=12.9352&lng=77.6245&radius_km=5.0&amount=2000.0"
    print(f"\n[1. TESTING GET /api/cashpoints] -> {get_url}")
    
    req = urllib.request.Request(get_url)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        print(f"HTTP Status: {resp.status}")
        print(f"Retrieved {len(data)} nearby cash points.")
        assert len(data) > 0, "Expected at least one cash point"
        first_cp = data[0]
        print(f"Top CashPoint: {first_cp['name']} | Prob: {first_cp['probability_score']}% | Distance: {first_cp['distance_km']}km | Balance: INR {first_cp['current_cash_balance']}")

    target_id = first_cp['id']
    initial_balance = first_cp['current_cash_balance']

    # 2. Test POST /api/cashpoints/{id}/deposit
    deposit_url = f"{BASE_URL}/api/cashpoints/{target_id}/deposit"
    print(f"\n[2. TESTING POST /api/cashpoints/{target_id}/deposit] -> Depositing INR 5,000")
    deposit_payload = json.dumps({"cash_point_id": target_id, "amount": 5000.0}).encode('utf-8')
    
    req_dep = urllib.request.Request(deposit_url, data=deposit_payload, headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req_dep) as resp_dep:
        dep_data = json.loads(resp_dep.read().decode())
        print(f"HTTP Status: {resp_dep.status}")
        expected_dep_bal = initial_balance + 5000.0
        print(f"Updated Balance: INR {dep_data['current_cash_balance']} (Expected: INR {expected_dep_bal})")
        assert dep_data['current_cash_balance'] == expected_dep_bal, "Deposit failed to update balance correctly"

    # 3. Test POST /api/cashpoints/{id}/refill
    refill_url = f"{BASE_URL}/api/cashpoints/{target_id}/refill"
    print(f"\n[3. TESTING POST /api/cashpoints/{target_id}/refill] -> Setting exact balance to INR 100,000")
    refill_payload = json.dumps({"new_balance": 100000.0}).encode('utf-8')

    req_ref = urllib.request.Request(refill_url, data=refill_payload, headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req_ref) as resp_ref:
        ref_data = json.loads(resp_ref.read().decode())
        print(f"HTTP Status: {resp_ref.status}")
        print(f"Refilled Balance: INR {ref_data['current_cash_balance']} | Probability Score: {ref_data['probability_score']}%")
        assert ref_data['current_cash_balance'] == 100000.0, "Refill failed to update balance correctly"

    print("\n" + "=" * 70)
    print("[SUCCESS] All 3 CashPoints API endpoints tested & verified successfully!")

if __name__ == "__main__":
    test_cashpoints_endpoints()
