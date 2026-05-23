import datetime


class RuleBasedValidator:
    """
    Rule-based validation engine for Levels.fyi crowd-sourced data.
    Implements the updated System Interface Contract with history tracking.
    """

    def __init__(self):
        # Global catch-all constraints
        self.MAX_BASE_SALARY = 1000000  # $1M
        self.MIN_BASE_SALARY = 30000    # $30K (global lower bound)
        self.MAX_TOTAL_COMP = 5000000   # $5M

        # Tier 1 Companies for context-aware range validation
        self.TIER1_COMPANIES = {"google", "meta", "apple", "microsoft", "amazon", "netflix"}
        self.TIER1_MIN_BASE = 120000    # $120K floor for Tier 1

    def validate(self, data: dict, recent_submissions: list = None) -> dict:
        """
        Validates submission data using deterministic rules.
        
        Args:
            data (dict): The raw submission matching the system data format.
            recent_submissions (list, optional): List of dicts representing past submissions
                                                 stored in the database for IP tracking.
            
        Returns:
            dict: {"score": int, "flags": list}
        """
        flags = []
        deductions = 0

        try:
            # 1. Safely extract core values
            base = float(data.get("base_salary") or 0)
            bonus = float(data.get("bonus") or 0)
            stock = float(data.get("stock_rsu") or 0)
            tc = float(data.get("total_compensation") or 0)
            yoe = float(data.get("years_of_experience") or 0)
            level = str(data.get("level") or "").upper().strip()
            title = str(data.get("title") or "").lower()
            company = str(data.get("company") or "").lower().strip()
            current_ip = data.get("ip_address")

            # --- Rule 1: IP Duplicate / Velocity Detection ---
            if current_ip and recent_submissions:
                current_time_str = data.get("submitted_at")
                if current_time_str:
                    try:
                        clean_curr_ts = current_time_str.replace("Z", "").split("+")[0]
                        current_time = datetime.datetime.fromisoformat(clean_curr_ts)
                        
                        # Count matches from the same IP within a 10-minute window
                        spam_count = 0
                        for sub in recent_submissions:
                            if sub.get("ip_address") == current_ip:
                                sub_time_str = sub.get("submitted_at")
                                if sub_time_str:
                                    clean_sub_ts = sub_time_str.replace("Z", "").split("+")[0]
                                    sub_time = datetime.datetime.fromisoformat(clean_sub_ts)
                                    
                                    # Check delta window (absolute difference handles out-of-order logs)
                                    time_delta = abs((current_time - sub_time).total_seconds())
                                    if time_delta <= 600:  # 10 minutes = 600 seconds
                                        spam_count += 1

                        # Flag if this IP is hitting the database 3 or more times inside the window
                        if spam_count >= 2:  # 2 historical matches + 1 current submission = 3 total occurrences
                            flags.append({
                                "rule": "ip_velocity_spam",
                                "severity": "high",
                                "message": f"Suspicious activity detection: IP address {current_ip} generated {spam_count + 1} submissions within a 10-minute window."
                            })
                            deductions += 45
                    except (ValueError, TypeError):
                        pass  # Handled safely via timestamp metrics below

            # --- Rule 2: Total Compensation Mathematical Check ---
            calculated_tc = base + bonus + stock
            if abs(tc - calculated_tc) > 100:
                severity = "high" if abs(tc - calculated_tc) > 10000 else "medium"
                flags.append({
                    "rule": "tc_math_mismatch",
                    "severity": severity,
                    "message": f"Reported TC (${tc:,.0f}) does not match calculated sum of Base, Bonus, and RSU (${calculated_tc:,.0f})."
                })
                deductions += 30 if severity == "high" else 15

            # --- Rule 3: Tier-Based and Global Salary Checks ---
            if company in self.TIER1_COMPANIES and base < self.TIER1_MIN_BASE:
                flags.append({
                    "rule": "tier1_salary_too_low",
                    "severity": "high",
                    "message": f"Base salary of ${base:,.0f} is unusually low for a Tier 1 company ({data.get('company')}). Expected minimum: ${self.TIER1_MIN_BASE:,.0f}."
                })
                deductions += 35
            elif base < self.MIN_BASE_SALARY:
                flags.append({
                    "rule": "salary_range_check",
                    "severity": "high",
                    "message": f"Base salary of ${base:,.0f} is suspiciously low for a professional tech role."
                })
                deductions += 40

            if base > self.MAX_BASE_SALARY or tc > self.MAX_TOTAL_COMP:
                flags.append({
                    "rule": "salary_range_check",
                    "severity": "high",
                    "message": f"Compensation metrics are extreme outlier numbers (Base: ${base:,.0f}, TC: ${tc:,.0f})."
                })
                deductions += 50

            # --- Rule 4: Level vs Experience Consistency ---
            is_senior_title = any(kw in title for kw in ["senior", "sr", "lead", "principal", "staff", "manager"])
            is_senior_level = level in {"L5", "L6", "L7", "L8", "E5", "E6", "IC5", "IC6"}
            
            if (is_senior_title or is_senior_level) and yoe < 2:
                flags.append({
                    "rule": "experience_level_mismatch",
                    "severity": "high",
                    "message": f"Senior level/title '{level} {data.get('title')}' reported with unusually low experience ({yoe} YOE)."
                })
                deductions += 25
            elif ("entry" in title or "junior" in title or "jr" in title or level in {"L3", "E3", "L1", "L2"}):
                if yoe > 8:
                    flags.append({
                        "rule": "experience_level_mismatch",
                        "severity": "medium",
                        "message": f"Junior/Entry title reported with very high experience ({yoe} YOE)."
                    })
                    deductions += 15

            # --- Rule 5: Missing Core Fields ---
            required_fields = ["company", "title", "level", "location"]
            for field in required_fields:
                if not data.get(field) or str(data.get(field)).strip() == "":
                    flags.append({
                        "rule": "missing_critical_data",
                        "severity": "high",
                        "message": f"Critical field '{field}' is missing or blank."
                    })
                    deductions += 20

            # --- Rule 6: Timestamps & Suspicious Hours ---
            submitted_at_str = data.get("submitted_at")
            if submitted_at_str:
                try:
                    clean_ts = submitted_at_str.replace("Z", "").split("+")[0]
                    submitted_at = datetime.datetime.fromisoformat(clean_ts)
                    
                    if submitted_at > datetime.datetime.now():
                        flags.append({
                            "rule": "suspicious_timestamp",
                            "severity": "medium",
                            "message": "Submission timestamp points to a future date."
                        })
                        deductions += 15
                    
                    # 1 AM to 4 AM tracking loop
                    if 1 <= submitted_at.hour <= 4:
                        flags.append({
                            "rule": "suspicious_submission_time",
                            "severity": "low",
                            "message": f"Submission made at {submitted_at.hour:02d}:00 AM — unusual hour."
                        })
                        deductions += 5
                        
                except ValueError:
                    flags.append({
                        "rule": "invalid_timestamp_format",
                        "severity": "low",
                        "message": "Timestamp format is invalid or can't be parsed."
                    })
                    deductions += 5

            score = max(0, 100 - deductions)
            return {
                "score": int(score),
                "flags": flags
            }

        except Exception as e:
            # Fixed: Fallback score now set to a neutral 50 instead of 0 to protect valid users
            return {
                "score": 50,
                "flags": [{
                    "rule": "system_validation_exception",
                    "severity": "high",
                    "message": f"Fatal execution exception in rule engine: {str(e)}"
                }]
            }