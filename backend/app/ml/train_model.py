# backend/app/ml/train_model.py
import os
import math
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score

def extract_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforms raw features into engineered cash depletion dynamics signals:
    1. Capacity Ratio = current_cash_balance / standard_float_limit
    2. Amount Ratio = requested_amount / current_cash_balance
    3. Burn Rate = total_withdrawn_2h / 2.0
    4. Hours Since Refill = hours_since_refill
    5. Cyclical Hours = sin(2*pi*hour/24), cos(2*pi*hour/24)
    6. Net Signal = positive_pings_6h - 2 * failure_pings_1h
    """
    X = pd.DataFrame()

    standard_limit = df['standard_float_limit'].replace(0, 50000.0)
    current_balance = df['current_cash_balance'].clip(lower=1.0)
    requested = df['requested_amount']

    X['capacity_ratio'] = (df['current_cash_balance'] / standard_limit).clip(0.0, 1.0)
    X['amount_ratio'] = (requested / current_balance).clip(0.0, 5.0)
    X['burn_rate'] = (df['recent_withdrawals_2h'] / 2.0)
    X['hours_since_refill'] = df['hours_since_last_refill'].clip(lower=0.0)

    hours = df['hour_of_day']
    X['hour_sin'] = np.sin(2 * np.pi * hours / 24.0)
    X['hour_cos'] = np.cos(2 * np.pi * hours / 24.0)

    pos_pings = df['positive_pings_6h']
    fail_pings = df['failure_pings_1h']
    X['net_signal'] = pos_pings - (2 * fail_pings)

    X['is_weekend'] = df['is_weekend']
    X['is_salary_day'] = df['is_salary_day']
    X['is_onsite'] = df['is_onsite']

    return X

def compute_running_balances(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes true chronological running balances, refill tracking, and burn rates
    per ATM from raw transaction logs.
    """
    df = df.sort_values(by=['atm_id', 'timestamp']).reset_index(drop=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    capacity = 100000.0
    df['standard_float_limit'] = capacity
    
    # Sample realistic variable withdrawal requests from users
    withdrawal_options = [500.0, 1000.0, 2000.0, 5000.0, 10000.0]
    df['requested_amount'] = np.random.choice(withdrawal_options, size=len(df), p=[0.2, 0.3, 0.3, 0.15, 0.05])
    df['is_onsite'] = 1

    balances = []
    hours_refilled = []
    burn_rates_2h = []
    pos_pings = []
    fail_pings = []

    for atm_id, group in df.groupby('atm_id', sort=False):
        current_bal = capacity
        last_refill = group['timestamp'].iloc[0]

        for idx, row in group.iterrows():
            ts = row['timestamp']
            withdrawn = row['total_withdrawn_inr']

            # Refill logic: if cash drops below 2000 or 24 hours pass, simulate refill
            hrs_since = (ts - last_refill).total_seconds() / 3600.0
            if current_bal < 2000.0 or hrs_since >= 24.0:
                current_bal = capacity
                last_refill = ts
                hrs_since = 0.0

            balances.append(current_bal)
            hours_refilled.append(hrs_since)

            # Deduct withdrawn amount for next step
            current_bal = max(0.0, current_bal - withdrawn)

            # Simulate rolling 2h burn rate
            tx_count = row['transaction_count']
            burn_rates_2h.append(tx_count * 2000.0)

            # Simulate crowdsourced pings
            if current_bal > 10000.0:
                pos_pings.append(np.random.randint(2, 6))
                fail_pings.append(0)
            elif current_bal > 0:
                pos_pings.append(np.random.randint(0, 3))
                fail_pings.append(np.random.randint(0, 2))
            else:
                pos_pings.append(0)
                fail_pings.append(np.random.randint(2, 5))

    df['current_cash_balance'] = balances
    df['hours_since_last_refill'] = hours_refilled
    df['recent_withdrawals_2h'] = burn_rates_2h
    df['positive_pings_6h'] = pos_pings
    df['failure_pings_1h'] = fail_pings

    return df

def train_and_save_model():
    data_path = os.path.join(os.path.dirname(__file__), '../../../data/historical_atm_transactions.csv')
    if not os.path.exists(data_path):
        print(f"Error: Dataset not found at {data_path}")
        return

    print(f"Loading raw dataset from {data_path}...")
    raw_df = pd.read_csv(data_path)

    print("Computing true chronological running balances and refill cycles...")
    processed_df = compute_running_balances(raw_df)

    # Define target label Y: 1 if balance >= requested_amount AND success_status == 1, else 0
    Y = np.where(
        (processed_df['current_cash_balance'] >= processed_df['requested_amount']) & 
        (processed_df['success_status'] == 1), 
        1, 
        0
    )

    # Feature engineering pipeline X
    X = extract_engineered_features(processed_df)

    # Train / Test split (80/20)
    X_train, X_test, y_train, y_test = train_test_split(X, Y, test_size=0.2, random_state=42, stratify=Y)

    print(f"Training Gradient Boosted Classifier on {len(X_train)} chronological samples...")
    model = HistGradientBoostingClassifier(
        max_iter=150,
        learning_rate=0.08,
        max_depth=6,
        random_state=42
    )
    model.fit(X_train, y_train)

    # Evaluation
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    auc_score = roc_auc_score(y_test, y_proba)

    print("\n--- RETRAINED MODEL EVALUATION REPORT ---")
    print(f"ROC-AUC Score: {auc_score:.4f}")
    print("\nClassification Report:\n", classification_report(y_test, y_pred))

    # Save model artifact
    model_dir = os.path.dirname(__file__)
    model_file = os.path.join(model_dir, "cash_model.pkl")
    with open(model_file, "wb") as f:
        pickle.dump(model, f)

    print(f"[SUCCESS] Retrained model artifact saved to {model_file}")

if __name__ == "__main__":
    train_and_save_model()
