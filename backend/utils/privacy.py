import re
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Set
import numpy as np

class PrivacyFilter:
    PII_KEYS: Set[str] = {
        "name", "first_name", "last_name", "full_name",
        "ssn", "social_security", "tax_id",
        "account_number", "account_no", "acct_num",
        "card_number", "card_no", "pan",
        "email", "email_address",
        "phone", "phone_number", "mobile",
        "address", "street", "city", "zip", "postal_code",
        "dob", "date_of_birth", "birth_date",
        "passport", "passport_number",
        "license", "drivers_license",
        "ip_address", "device_id", "user_id",
        "customer_id", "client_id"
    }

    def scan_for_pii(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively scan a dictionary for any PII keys.
        Excludes categorical values in distribution dictionaries.
        """
        violations = []
        depth_found = {}

        def recurse(current_dict: Any, current_depth: int, parent_key: str = ""):
            if not isinstance(current_dict, dict):
                if isinstance(current_dict, list):
                    for item in current_dict:
                        recurse(item, current_depth, parent_key)
                return
            
            for k, v in current_dict.items():
                k_lower = k.lower()
                is_dist = parent_key in ["channel_distribution", "country_distribution"]
                if k_lower in self.PII_KEYS and not is_dist:
                    violations.append(k)
                    depth_found[k] = current_depth
                recurse(v, current_depth + 1, k)

        recurse(data, 1)
        # Deduplicate violations while preserving order
        unique_violations = list(dict.fromkeys(violations))
        return {
            "clean": len(unique_violations) == 0,
            "violations": unique_violations,
            "depth_found": depth_found
        }

    def strip_pii(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively remove all PII keys from a dictionary and redact sensitive patterns.
        Excludes categorical values in distribution dictionaries.
        """
        def recurse(obj: Any, parent_key: str = "") -> Any:
            if isinstance(obj, dict):
                is_dist = parent_key in ["channel_distribution", "country_distribution"]
                return {
                    k: recurse(v, k)
                    for k, v in obj.items()
                    if is_dist or k.lower() not in self.PII_KEYS
                }
            elif isinstance(obj, list):
                return [recurse(item, parent_key) for item in obj]
            elif isinstance(obj, str):
                val = obj
                # Redact email pattern (contains @ and .)
                if '@' in val and '.' in val:
                    val = re.sub(
                        r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
                        "[REDACTED_EMAIL]",
                        val
                    )
                # Redact SSN pattern (###-##-####)
                val = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', "[REDACTED_SSN]", val)
                
                # Redact Phone pattern (10+ digits)
                digits = re.sub(r'\D', '', val)
                if len(digits) >= 10:
                    if re.match(r'^[\d\s()+\--]+$', val.strip()):
                        return "[REDACTED_PHONE]"
                    else:
                        val = re.sub(r'\b\d{10,}\b', "[REDACTED_PHONE]", val)
                return val
            else:
                return obj

        return recurse(data)

    def extract_behavioral_only(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extracts only behavioral patterns from transactions with 0 PII.
        """
        if not transactions:
            return {
                "transaction_count": 0,
                "time_span_hours": 0.0,
                "velocity_per_hour": 0.0,
                "amount_stats": {
                    "min": 0.0, "max": 0.0, "mean": 0.0, "std_dev": 0.0,
                    "round_number_ratio": 0.0, "near_10k_ratio": 0.0
                },
                "time_patterns": {
                    "off_hours_ratio": 0.0, "peak_hour": 0, "burst_detected": False
                },
                "account_patterns": {
                    "avg_account_age_days": 0.0, "new_account_ratio": 0.0,
                    "unique_counterparties": 0, "cross_border_ratio": 0.0
                },
                "channel_distribution": {},
                "country_distribution": {},
                "risk_indicators": []
            }

        total_count = len(transactions)
        amounts = [float(tx['amount']) for tx in transactions]
        
        # Parse Timestamps
        t_dates = []
        for tx in transactions:
            ts = tx['timestamp']
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            t_dates.append(ts)
        
        sorted_dates = sorted(t_dates)
        if len(sorted_dates) > 1:
            span_seconds = (sorted_dates[-1] - sorted_dates[0]).total_seconds()
            time_span_hours = max(span_seconds / 3600.0, 0.001)
        else:
            time_span_hours = 0.0
            
        velocity = total_count / time_span_hours if time_span_hours > 0 else 0.0
        
        # Amount calculations
        amt_min = float(np.min(amounts))
        amt_max = float(np.max(amounts))
        amt_mean = float(np.mean(amounts))
        amt_std = float(np.std(amounts)) if len(amounts) > 1 else 0.0
        
        # Round number ratio (multiple of 100)
        round_count = sum(1 for a in amounts if a % 100 == 0)
        round_ratio = round_count / total_count
        
        # Near 10k ratio (9000 to 10000 inclusive)
        near_10k_count = sum(1 for a in amounts if 9000 <= a <= 10000)
        near_10k_ratio = near_10k_count / total_count
        
        # Off-hours ratio (UTC hours < 6 or > 22)
        off_hours_count = sum(1 for dt in t_dates if dt.hour < 6 or dt.hour > 22)
        off_hours_ratio = off_hours_count / total_count
        
        from collections import Counter
        hours = [dt.hour for dt in t_dates]
        peak_hour = Counter(hours).most_common(1)[0][0]
        
        # Burst detection (> 5 transactions in any 30min window)
        burst_detected = False
        for i, t1 in enumerate(sorted_dates):
            count_in_window = 0
            for t2 in sorted_dates[i:]:
                if t2 - t1 <= timedelta(minutes=30):
                    count_in_window += 1
                else:
                    break
            if count_in_window > 5:
                burst_detected = True
                break
                
        # Account features
        ages = [float(tx.get('account_age_days', 0)) for tx in transactions]
        avg_age = float(np.mean(ages))
        new_acct_count = sum(1 for age in ages if age < 30)
        new_ratio = new_acct_count / total_count
        
        unique_cp = len(set(tx.get('counterparty_hash', '') for tx in transactions))
        
        cross_border_count = sum(1 for tx in transactions if tx.get('cross_border') is True)
        cross_border_ratio = cross_border_count / total_count
        
        # Channel & Country counts
        channels = [tx.get('channel', 'unknown') for tx in transactions]
        channel_counts = Counter(channels)
        channel_dist = {ch: count / total_count for ch, count in channel_counts.items()}
        
        countries = [tx.get('country', 'unknown') for tx in transactions]
        country_counts = Counter(countries)
        country_dist = {co: count / total_count for co, count in country_counts.items()}
        
        # Rule-based risk flags
        risk_indicators = []
        if new_ratio > 0.5 and velocity > 2.0:
            risk_indicators.append("High velocity of transactions on newly created accounts")
        if near_10k_ratio > 0.1:
            risk_indicators.append("Potential structuring activity with transaction amounts near $10,000")
        if round_ratio > 0.5:
            risk_indicators.append("Unusual proportion of round-number transaction amounts")
        if cross_border_ratio > 0.4:
            risk_indicators.append("High volume of cross-border transfers")
        if burst_detected:
            risk_indicators.append("High-frequency transaction burst (over 5 transactions in 30 minutes)")
        if avg_age < 10:
            risk_indicators.append("Extremely low average account age across transactions")
        if off_hours_ratio > 0.4:
            risk_indicators.append("Significant transaction activity during off-hours (11PM - 6AM UTC)")
        if unique_cp > 5 and velocity > 2.0:
            risk_indicators.append("Rapid transaction routing to multiple distinct counterparties")

        return {
            "transaction_count": total_count,
            "time_span_hours": float(round(time_span_hours, 4)),
            "velocity_per_hour": float(round(velocity, 4)),
            "amount_stats": {
                "min": float(round(amt_min, 2)),
                "max": float(round(amt_max, 2)),
                "mean": float(round(amt_mean, 2)),
                "std_dev": float(round(amt_std, 2)),
                "round_number_ratio": float(round(round_ratio, 4)),
                "near_10k_ratio": float(round(near_10k_ratio, 4))
            },
            "time_patterns": {
                "off_hours_ratio": float(round(off_hours_ratio, 4)),
                "peak_hour": int(peak_hour),
                "burst_detected": bool(burst_detected)
            },
            "account_patterns": {
                "avg_account_age_days": float(round(avg_age, 2)),
                "new_account_ratio": float(round(new_ratio, 4)),
                "unique_counterparties": int(unique_cp),
                "cross_border_ratio": float(round(cross_border_ratio, 4))
            },
            "channel_distribution": {k: float(round(v, 4)) for k, v in channel_dist.items()},
            "country_distribution": {k: float(round(v, 4)) for k, v in country_dist.items()},
            "risk_indicators": risk_indicators
        }

    def generate_pattern_hash(self, behavioral_data: Dict[str, Any]) -> str:
        """
        Deterministically hash the sorted behavioral JSON structure.
        """
        serialized = json.dumps(behavioral_data, sort_keys=True)
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()

    def validate_signal_privacy(self, signal_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform a comprehensive safety scan of the signal dict before egress.
        """
        # Scan keys
        scan_res = self.scan_for_pii(signal_dict)
        violations = list(scan_res["violations"])
        
        # Check string values for raw email, ssn, phone patterns
        value_violations = []
        
        def check_val(obj: Any, path: str = ""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    check_val(v, f"{path}.{k}" if path else k)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_val(item, f"{path}[{i}]")
            elif isinstance(obj, str):
                if '@' in obj and '.' in obj:
                    if re.search(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b', obj):
                        if "[REDACTED_EMAIL]" not in obj:
                            value_violations.append(f"Unredacted email pattern in '{path}'")
                if re.search(r'\b\d{3}-\d{2}-\d{4}\b', obj):
                    if "[REDACTED_SSN]" not in obj:
                        value_violations.append(f"Unredacted SSN pattern in '{path}'")
                
                # Check for phone pattern (10+ digits) in non-identifier fields
                digits = re.sub(r'\D', '', obj)
                if len(digits) >= 10:
                    if "[REDACTED_PHONE]" not in obj:
                        # Exclude normal hashes, UUIDs or timestamp strings
                        is_identifier = any(x in path.lower() for x in ["hash", "id", "session_id", "timestamp", "region"])
                        if not is_identifier and re.match(r'^[\d\s()+\--]+$', obj.strip()):
                            value_violations.append(f"Unredacted phone pattern in '{path}'")

        check_val(signal_dict)
        violations.extend(value_violations)
        
        approved = len(violations) == 0
        if approved:
            message = "Signal cleared for transmission. No PII detected."
        else:
            message = f"Signal rejected. Detected PII violations: {', '.join(violations)}"
            
        return {
            "approved": approved,
            "violations": violations,
            "message": message
        }
