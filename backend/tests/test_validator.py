import sys
import os

# Absolute path positioning override for direct local execution scripts
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from validator import RuleBasedValidator

# Standard seed schema mock data mapping
BASE_VALID_SUBMISSION = {
    "name": "Test User",
    "email": "test@example.com",
    "company": "Google",
    "title": "Software Engineer",
    "level": "L5",
    "location": "Mountain View, CA",
    "years_of_experience": 6,
    "base_salary": 180000,
    "bonus": 30000,
    "stock_rsu": 200000,
    "total_compensation": 410000,
    "ip_address": "192.168.1.1",
    "submitted_at": "2024-01-15T14:30:00"  # Afternoon submission
}

def run_tests():
    engine = RuleBasedValidator()
    print("--- Running Updated Validation Verification ---")

    # Test 1: Clean Baseline Target
    res_clean = engine.validate(BASE_VALID_SUBMISSION)
    print(f"\n[Test 1] Baseline Clean Submission Score: {res_clean['score']}/100")
    assert res_clean['score'] == 100, "Clean payload mapping should yield a flawless 100 score."

    # Test 2: Tier 1 Low Base Salary Constraint ($45k Google SWE entry checking)
    low_tier_data = BASE_VALID_SUBMISSION.copy()
    low_tier_data["base_salary"] = 45000
    low_tier_data["total_compensation"] = 275000  # 45 + 30 + 200
    res_tier = engine.validate(low_tier_data)
    print(f"\n[Test 2] Tier 1 Low Salary Test Score: {res_tier['score']}/100")
    for f in res_tier['flags']:
        print(f" - [{f['severity'].upper()}] {f['rule']}: {f['message']}")
    assert any(f['rule'] == 'tier1_salary_too_low' for f in res_tier['flags']), "Missing low tier classification drop."

    # Test 3: Midnight Window Run Verification (2:30 AM execution block)
    midnight_data = BASE_VALID_SUBMISSION.copy()
    midnight_data["submitted_at"] = "2024-01-15T02:30:00"
    res_time = engine.validate(midnight_data)
    print(f"\n[Test 3] Late Night Submission Score: {res_time['score']}/100")
    assert any(f['rule'] == 'suspicious_submission_time' for f in res_time['flags']), "Late night flag validation bypassed."

    # Test 4: Dynamic IP Velocity Tracking Simulator
    spam_history = [
        {"ip_address": "192.168.1.1", "submitted_at": "2024-01-15T14:22:00"},
        {"ip_address": "192.168.1.1", "submitted_at": "2024-01-15T14:25:00"},
        {"ip_address": "10.0.0.5",    "submitted_at": "2024-01-15T14:24:00"}, # Noise IP
    ]
    res_spam = engine.validate(BASE_VALID_SUBMISSION, recent_submissions=spam_history)
    print(f"\n[Test 4] IP Velocity Spam Test Score: {res_spam['score']}/100")
    for f in res_spam['flags']:
        print(f" - [{f['severity'].upper()}] {f['rule']}: {f['message']}")
    assert any(f['rule'] == 'ip_velocity_spam' for f in res_spam['flags']), "IP velocity check failed to catch the burst."

    print("\n All custom verification checks passing seamlessly. Ready for pipeline merge.")

if __name__ == "__main__":
    run_tests()