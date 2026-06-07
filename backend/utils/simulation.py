import hashlib
import random
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

class TransactionSimulator:
    def generate_coordinated_fraud_scenario(self) -> List[Dict[str, Any]]:
        """
        Scenario: Fraudster opens accounts at multiple banks simultaneously.
        Generates 3 accounts x 15 transactions each = 45 total.
        """
        transactions = []
        base_time = datetime.now(timezone.utc) - timedelta(hours=6)
        
        for account_idx in range(3):
            # Compute account hash: sha256 of "synthetic_fraud_acct_{account_idx}"[:12]
            acct_str = f"synthetic_fraud_acct_{account_idx}"
            account_hash = hashlib.sha256(acct_str.encode('utf-8')).hexdigest()[:12]
            
            for i in range(15):
                # Compute tx hash: sha256 of "tx_{account_idx}_{i}"[:8]
                tx_str = f"tx_{account_idx}_{i}"
                tx_hash = hashlib.sha256(tx_str.encode('utf-8')).hexdigest()[:8]
                
                # Compute counterparty hash: sha256 of "counterparty_{i}"[:8]
                cp_str = f"counterparty_{i}"
                counterparty_hash = hashlib.sha256(cp_str.encode('utf-8')).hexdigest()[:8]
                
                # Select a round number amount (indicator of fraud)
                amount = random.choice([500, 1000, 2500, 5000, 9900])
                
                # Timestamp: base_time + timedelta(minutes=i*8)
                tx_time = base_time + timedelta(minutes=i*8)
                
                transactions.append({
                    "tx_hash": tx_hash,
                    "account_hash": account_hash,
                    "counterparty_hash": counterparty_hash,
                    "amount": float(amount),
                    "timestamp": tx_time.isoformat().replace('+00:00', 'Z'),
                    "cross_border": random.random() > 0.6,
                    "account_age_days": 2,
                    "channel": random.choice(["mobile", "atm", "wire", "online"]),
                    "country": random.choice(["US", "US", "US", "MX", "NG"]),
                    "is_synthetic": True
                })
                
        return transactions

    def generate_linked_accounts(self) -> List[Dict[str, Any]]:
        """
        Scenario: Bank B accounts receiving money from the fraud network.
        Generates 8 transactions.
        """
        transactions = []
        base_time = datetime.now(timezone.utc) - timedelta(hours=3)
        receiving_hash = hashlib.sha256(b"receiving_account_fraud").hexdigest()[:12]
        
        for i in range(8):
            tx_hash = hashlib.sha256(f"linked_tx_{i}".encode('utf-8')).hexdigest()[:8]
            counterparty_hash = hashlib.sha256(f"sender_{i}".encode('utf-8')).hexdigest()[:8]
            amount = random.choice([500, 1000, 2500])
            tx_time = base_time + timedelta(minutes=i*15)
            
            transactions.append({
                "tx_hash": tx_hash,
                "account_hash": receiving_hash,
                "counterparty_hash": counterparty_hash,
                "amount": float(amount),
                "timestamp": tx_time.isoformat().replace('+00:00', 'Z'),
                "cross_border": False,
                "account_age_days": 5,
                "channel": "wire",
                "country": "US",
                "is_synthetic": True
            })
            
        return transactions

    def generate_synthetic_identity_scenario(self) -> List[Dict[str, Any]]:
        """
        Scenario: Fake identity that accumulated credit over 18 months, then drains everything.
        Generates 12 transactions.
        """
        transactions = []
        base_time = datetime.now(timezone.utc) - timedelta(hours=2)
        account_hash = hashlib.sha256(b"synthetic_identity_main").hexdigest()[:12]
        
        for i in range(12):
            tx_hash = hashlib.sha256(f"synth_tx_{i}".encode('utf-8')).hexdigest()[:8]
            counterparty_hash = hashlib.sha256(f"synth_cp_{i}".encode('utf-8')).hexdigest()[:8]
            # Near $10,000 structuring threshold
            amount = random.randint(8000, 12000)
            tx_time = base_time + timedelta(minutes=i*5)
            
            transactions.append({
                "tx_hash": tx_hash,
                "account_hash": account_hash,
                "counterparty_hash": counterparty_hash,
                "amount": float(amount),
                "timestamp": tx_time.isoformat().replace('+00:00', 'Z'),
                "cross_border": i % 3 == 0,
                "account_age_days": 540,
                "channel": "wire",
                "country": "US",
                "is_synthetic": True
            })
            
        return transactions

    def generate_normal_transactions(self, count: int = 50) -> List[Dict[str, Any]]:
        """
        Generates count normal baseline transactions across 5 rotating account hashes.
        """
        transactions = []
        base_time = datetime.now(timezone.utc) - timedelta(hours=24)
        acct_hashes = [hashlib.sha256(f"normal_acct_{k}".encode('utf-8')).hexdigest()[:12] for k in range(5)]
        
        for i in range(count):
            tx_hash = hashlib.sha256(f"normal_tx_{i}".encode('utf-8')).hexdigest()[:8]
            account_hash = random.choice(acct_hashes)
            counterparty_hash = hashlib.sha256(f"normal_cp_{i}".encode('utf-8')).hexdigest()[:8]
            amount = random.randint(10, 3000)
            # Spread randomly over the last 24 hours
            tx_time = base_time + timedelta(seconds=random.randint(0, 86400))
            
            transactions.append({
                "tx_hash": tx_hash,
                "account_hash": account_hash,
                "counterparty_hash": counterparty_hash,
                "amount": float(amount),
                "timestamp": tx_time.isoformat().replace('+00:00', 'Z'),
                "cross_border": random.random() > 0.9,
                "account_age_days": random.randint(180, 3650),
                "channel": random.choice(["mobile", "atm", "wire", "online"]),
                "country": random.choice(["US", "US", "US", "CA", "GB"]),
                "is_synthetic": True
            })
            
        return transactions

    def get_scenario_description(self, scenario: str) -> Dict[str, Any]:
        """
        Returns scenario descriptive metadata.
        """
        scenario_upper = scenario.upper()
        if scenario_upper == "COORDINATED_FRAUD":
            return {
                "name": "Coordinated Fraud Scenario",
                "description": "Fraudster opens new accounts at multiple banks simultaneously to execute rapid, coordinated round-sum transfers.",
                "expected_outcome": "Detect high-frequency, round-sum patterns spanning multiple distinct originating institutions.",
                "fraud_indicators": [
                    "Newly opened accounts (age < 30 days)",
                    "Round-number transaction amounts (multiples of $100/$500)",
                    "High transaction velocity (multiple transactions per hour)",
                    "Frequent cross-border transfers"
                ]
            }
        elif scenario_upper == "SYNTHETIC_IDENTITY":
            return {
                "name": "Synthetic Identity Bust-Out",
                "description": "An established synthetic account built over 18 months suddenly initiates multiple high-value wire transfers to empty the credit line.",
                "expected_outcome": "Detect sudden spike in transaction volume and amounts nearing the $10,000 regulatory reporting limit.",
                "fraud_indicators": [
                    "Transaction amounts structuring near the $10,000 compliance limit",
                    "Sudden surge in transaction frequency on an established account",
                    "Large international wire transfers"
                ]
            }
        elif scenario_upper == "NORMAL_BASELINE":
            return {
                "name": "Normal Baseline Activity",
                "description": "A stream of standard daily transaction behavior representing low-risk account actions.",
                "expected_outcome": "No anomalies or fraud alerts triggered; indicators fall within historical norms.",
                "fraud_indicators": []
            }
        else:
            return {
                "name": f"Scenario {scenario}",
                "description": "Custom transaction simulation scenario.",
                "expected_outcome": "Standard network routing and monitoring.",
                "fraud_indicators": []
            }
