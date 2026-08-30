# cashFinder 💵 Mobile/Web App
> **Predictive Cash Availability & Cardless UPI Cash Withdrawal**
> *Solving last-mile physical cash discovery using Calibrated Machine Learning & NPCI Standard UPI Intent Flows.*

---

## 📌 Project Overview
While UPI has revolutionized digital payments in India, finding **available physical cash** remains a last-mile challenge. ATMs often suffer from empty cash bins, hardware jams, or denomination shortages, while local merchant shops (Kirana stores, Micro-ATMs) have available float but lack a discovery layer.

**cashFinder** solves this problem by:
1. **Predicting Real-Time Cash Availability:** Uses a **HistGradientBoosting ML Engine** trained on 113,000+ transaction records to calculate calibrated probability scores (e.g. *"87% chance for ₹2,000"*).
2. **Instant Cardless UPI Withdrawal:** Generates standard NPCI-compliant UPI Intent URIs (`upi://pay?pa=...`) and base64 PNG QR code image payloads for 1-tap mobile withdrawals or desktop scanning.
3. **Crowdsourced Telemetry:** Accepts live user reports (`GOT_CASH`, `OUT_OF_CASH`, `MACHINE_BROKEN`) that dynamically update ML signals in real time.
4. **Double-Entry Merchant Float Management:** Provides a Merchant Panel for local shopkeepers to deposit incoming customer cash float or reset float limits.

---

## 🏗️ Architecture & Tech Stack

### **Backend (FastAPI + Python 3.13)**
* **Framework:** **FastAPI** running on Uvicorn.
* **Database & ORM:** **SQLite** (`cashfinder.db` for local dev) / **PostgreSQL + PostGIS** (`docker-compose.yml`) with **SQLAlchemy 2.0**.
* **ML & Feature Engineering:** **Scikit-Learn** (`HistGradientBoostingClassifier`), **Pandas**, **NumPy**, **Pickle**.
* **UPI & QR Engine:** `qrcode`, **Pillow**, **Base64**.

### **Frontend (React 19 + Vite)**
* **Framework:** **React 19** + **Vite**.
* **Design System:** Installed **`frontend-ui-dark-ts`** (Tailwind CSS, Lucide Icons, Glassmorphism, Probability Badges: 🟢 >80%, 🟡 45-79%, 🔴 <45%).
* **Map Engine:** **React-Leaflet** + **OpenStreetMap** dark tiles (`tile.openstreetmap.org`) — *Zero API keys required*.

---

## 🧠 Machine Learning Engine Pipeline

The prediction service (`backend/app/services/prediction_service.py`) uses a **Gradient Boosted Decision Tree model** trained on sequential transaction logs:

### **Feature Engineering Pipeline (`backend/app/ml/feature_utils.py`)**
* `capacity_ratio` = `current_cash_balance / standard_float_limit`
* `amount_ratio` = `requested_amount / current_cash_balance`
* `burn_rate` = `total cash withdrawn in prior 2 hours / 2.0`
* `hours_since_refill` = `(now - last_refilled_at) / 3600`
* `hour_sin` / `hour_cos` = Cyclical sin/cos encodings for 24-hour time cycles
* `net_signal` = `positive_pings_6h - (2 * failure_pings_1h)`
* Categoricals = `is_weekend`, `is_salary_day`, `is_onsite`

### **Model Calibration & Guardrails**
* **Monotonic Constraints:** Enforces domain invariants (`+1` for capacity, `-1` for burn rate) so higher available cash never decreases probability.
* **Isotonic Probability Calibration (`CalibratedClassifierCV`):** Achieved **0.9730 ROC-AUC** and **0.0557 Brier Loss score**.
* **Hard Unfulfillable Filter:** Automatically suppresses cash points from UI when `requested_amount > current_cash_balance`.

---

## ⚡ Quick Start & Setup Guide

### **Prerequisites**
* **Python 3.11+** installed
* **Node.js 18+** & **npm** installed

---

### **1. Backend Setup (FastAPI)**

```bash
# Navigate to backend directory
cd backend

# Create Python virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On macOS/Linux:
# source .venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt

# Run database & prediction engine tests
python -m tests.test_all_apis

# Start FastAPI server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*Backend API will be live at:* `http://localhost:8000`

---

### **2. Frontend Setup (React + Vite)**

```bash
# Navigate to frontend directory (from project root)
cd frontend

# Install npm packages
npm install

# Start Vite development server
npm run dev
```
*Frontend Web App will be live at:* `http://localhost:5173`

---

## 🧪 Running Verification Tests

Run the backend test suite anytime using the virtual environment runner:

```bash
# Test database models & double-entry cash flow
.\backend\.venv\Scripts\python.exe -m tests.test_db

# Test ML model performance & metrics
.\backend\.venv\Scripts\python.exe -m tests.test_model_performance

# Test dummy data prediction scenarios
.\backend\.venv\Scripts\python.exe -m tests.test_model_direct

# Test end-to-end API endpoints (GET cashpoints, POST telemetry, POST withdraw)
.\backend\.venv\Scripts\python.exe -m tests.test_all_apis
```

---

## 📡 API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `GET /api/cashpoints` | `GET` | Returns nearby cash points sorted by ML probability and distance |
| `POST /api/telemetry` | `POST` | Submits crowd pings (`GOT_CASH`, `OUT_OF_CASH`, `MACHINE_BROKEN`) |
| `GET /api/telemetry/{id}` | `GET` | Retrieves recent telemetry history for a specific cash point |
| `POST /api/upi/withdraw` | `POST` | Deducts float, generates NPCI UPI URI and base64 PNG QR code |
| `POST /api/cashpoints/{id}/deposit` | `POST` | Merchant endpoint to add customer cash float |
| `POST /api/cashpoints/{id}/refill` | `POST` | Admin/Operator endpoint to reset float capacity |

---

## 📄 Documentation & Summary
Detailed technical architecture documentation is available in PDF format at:  
`backend/cashFinder_Technical_Documentation.pdf`
