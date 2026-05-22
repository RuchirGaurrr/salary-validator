"""
sample_data.py
--------------
Defines 15 richly varied salary submissions used by seed_data.py and tests.
Each entry is tagged with an expected outcome so test scripts can assert
results without hardcoding magic numbers.

Categories
  VALID       — realistic, should pass validation
  SUSPICIOUS  — plausible but has red-flag combos (low XP + senior title, etc.)
  FAKE        — obviously fabricated (impossible salaries, intern millionaires)
  EDGE        — boundary / stress cases (missing optional fields, max values)
"""

from datetime import datetime, timedelta, timezone

# ── helpers ──────────────────────────────────────────────────────────────────
_NOW = datetime.now(timezone.utc)

def _ts(minutes_ago: int = 0) -> str:
    """Return an ISO-8601 timestamp offset from now."""
    return (_NOW - timedelta(minutes=minutes_ago)).isoformat()


# ── VALID submissions (should score ≥ 70, passed = True) ─────────────────────
VALID_SUBMISSIONS = [
    {
        # Classic mid-level Google SWE — textbook Levels.fyi entry
        "_label": "valid_google_l4",
        "name": "Priya Sharma",
        "email": "priya.sharma@gmail.com",
        "company": "Google",
        "title": "Software Engineer",
        "level": "L4",
        "location": "Mountain View, CA",
        "years_of_experience": 4,
        "base_salary": 175000,
        "bonus": 22000,
        "stock_rsu": 90000,
        "total_compensation": 287000,
        "ip_address": "203.0.113.10",
        "submitted_at": _ts(30),
    },
    {
        # Senior Meta engineer — numbers align with public Levels.fyi data
        "_label": "valid_meta_e5",
        "name": "James O'Brien",
        "email": "jobrien@outlook.com",
        "company": "Meta",
        "title": "Senior Software Engineer",
        "level": "E5",
        "location": "Menlo Park, CA",
        "years_of_experience": 8,
        "base_salary": 210000,
        "bonus": 40000,
        "stock_rsu": 250000,
        "total_compensation": 500000,
        "ip_address": "203.0.113.20",
        "submitted_at": _ts(60),
    },
    {
        # Microsoft SDE-II in a lower-cost hub — realistic for Seattle
        "_label": "valid_microsoft_sde2",
        "name": "Wei Zhang",
        "email": "wei.zhang@hotmail.com",
        "company": "Microsoft",
        "title": "Software Development Engineer II",
        "level": "SDE-II",
        "location": "Redmond, WA",
        "years_of_experience": 5,
        "base_salary": 165000,
        "bonus": 25000,
        "stock_rsu": 120000,
        "total_compensation": 310000,
        "ip_address": "203.0.113.30",
        "submitted_at": _ts(90),
    },
    {
        # Amazon L5 — known for lower base, heavy RSU
        "_label": "valid_amazon_l5",
        "name": "Fatima Al-Hassan",
        "email": "fatima.h@yahoo.com",
        "company": "Amazon",
        "title": "Software Development Engineer",
        "level": "L5",
        "location": "Seattle, WA",
        "years_of_experience": 6,
        "base_salary": 155000,
        "bonus": 20000,
        "stock_rsu": 200000,
        "total_compensation": 375000,
        "ip_address": "203.0.113.40",
        "submitted_at": _ts(120),
    },
    {
        # Entry-level Apple new grad — no stock vested yet, modest numbers
        "_label": "valid_apple_newgrad",
        "name": "Carlos Mendez",
        "email": "c.mendez@icloud.com",
        "company": "Apple",
        "title": "Software Engineer",
        "level": "ICT2",
        "location": "Cupertino, CA",
        "years_of_experience": 1,
        "base_salary": 130000,
        "bonus": 15000,
        "stock_rsu": 40000,
        "total_compensation": 185000,
        "ip_address": "203.0.113.50",
        "submitted_at": _ts(150),
    },
]


# ── SUSPICIOUS submissions (should score 40–69, passed = False, flagged) ─────
SUSPICIOUS_SUBMISSIONS = [
    {
        # E6 with only 1 year XP — almost impossible to reach in practice
        "_label": "suspicious_meta_e6_lowxp",
        "name": "Alex Kim",
        "email": "alexkim@gmail.com",
        "company": "Meta",
        "title": "Staff Software Engineer",
        "level": "E6",
        "location": "New York, NY",
        "years_of_experience": 1,
        "base_salary": 250000,
        "bonus": 50000,
        "stock_rsu": 300000,
        "total_compensation": 600000,
        "ip_address": "203.0.113.60",
        "submitted_at": _ts(10),
    },
    {
        # Total comp doesn't add up (base+bonus+rsu = 360k, reported 600k)
        "_label": "suspicious_google_math_mismatch",
        "name": "Raj Patel",
        "email": "raj.patel@gmail.com",
        "company": "Google",
        "title": "Software Engineer",
        "level": "L5",
        "location": "Sunnyvale, CA",
        "years_of_experience": 7,
        "base_salary": 200000,
        "bonus": 60000,
        "stock_rsu": 100000,
        "total_compensation": 600000,   # ← should be ~360k; overstated by 240k
        "ip_address": "203.0.113.70",
        "submitted_at": _ts(5),
    },
    {
        # Duplicate IP — same IP already used in seed (203.0.113.10 = valid_google_l4)
        "_label": "suspicious_duplicate_ip",
        "name": "Anonymous User",
        "email": "anon123@protonmail.com",
        "company": "Netflix",
        "title": "Senior Software Engineer",
        "level": "E5",
        "location": "Los Gatos, CA",
        "years_of_experience": 10,
        "base_salary": 300000,
        "bonus": 80000,
        "stock_rsu": 400000,
        "total_compensation": 780000,
        "ip_address": "203.0.113.10",   # ← duplicate
        "submitted_at": _ts(2),
    },
    {
        # Startup listing inflated equity as guaranteed RSU
        "_label": "suspicious_startup_inflated_rsu",
        "name": "Dana Rivers",
        "email": "dana.rivers@techstartup.io",
        "company": "OpenAI",
        "title": "ML Engineer",
        "level": "L4",
        "location": "San Francisco, CA",
        "years_of_experience": 3,
        "base_salary": 190000,
        "bonus": 30000,
        "stock_rsu": 800000,    # ← unrealistically high RSU for L4
        "total_compensation": 1020000,
        "ip_address": "203.0.113.80",
        "submitted_at": _ts(20),
    },
]


# ── FAKE submissions (should score < 40, passed = False) ─────────────────────
FAKE_SUBMISSIONS = [
    {
        # Intern claiming half-million base — classic troll entry
        "_label": "fake_google_intern_millionaire",
        "name": "Rich Kid",
        "email": "rich@money.com",
        "company": "Google",
        "title": "Intern",
        "level": "L1",
        "location": "Mountain View, CA",
        "years_of_experience": 0,
        "base_salary": 500000,
        "bonus": 400000,
        "stock_rsu": 1000000,
        "total_compensation": 1900000,
        "ip_address": "10.0.0.1",
        "submitted_at": _ts(0),
    },
    {
        # Absurdly low salary for a senior role
        "_label": "fake_amazon_lowball",
        "name": "Test User",
        "email": "test@test.com",
        "company": "Amazon",
        "title": "Senior Principal Engineer",
        "level": "L8",
        "location": "Seattle, WA",
        "years_of_experience": 20,
        "base_salary": 45000,   # ← ~$20/hr for a principal — clearly fake
        "bonus": 5000,
        "stock_rsu": 0,
        "total_compensation": 50000,
        "ip_address": "192.168.0.1",
        "submitted_at": _ts(0),
    },
    {
        # Negative salary — input manipulation attempt
        "_label": "fake_negative_salary",
        "name": "Hacker",
        "email": "hacker@evil.com",
        "company": "Microsoft",
        "title": "Software Engineer",
        "level": "SDE-I",
        "location": "Redmond, WA",
        "years_of_experience": 2,
        "base_salary": -999999,
        "bonus": -100000,
        "stock_rsu": 9999999,
        "total_compensation": 0,
        "ip_address": "0.0.0.0",
        "submitted_at": _ts(0),
    },
]


# ── EDGE CASE submissions (boundary / stress conditions) ─────────────────────
EDGE_CASE_SUBMISSIONS = [
    {
        # Missing optional fields — only required fields present
        "_label": "edge_minimal_fields",
        "name": "Jane Doe",
        "email": "jane.doe@gmail.com",
        "company": "Stripe",
        "title": "Software Engineer",
        "level": "L4",
        "location": "Remote",
        "years_of_experience": 5,
        "base_salary": 160000,
        "bonus": 0,             # no bonus is legitimate
        "stock_rsu": 0,         # no RSU reported
        "total_compensation": 160000,
        "ip_address": "203.0.113.90",
        "submitted_at": _ts(200),
    },
    {
        # Extremely high but legitimate-looking staff/principal comp
        "_label": "edge_high_but_plausible",
        "name": "Veteran Engineer",
        "email": "senior@bigtech.com",
        "company": "Google",
        "title": "Distinguished Engineer",
        "level": "L9",
        "location": "San Francisco, CA",
        "years_of_experience": 25,
        "base_salary": 400000,
        "bonus": 200000,
        "stock_rsu": 1500000,
        "total_compensation": 2100000,
        "ip_address": "203.0.113.100",
        "submitted_at": _ts(300),
    },
    {
        # Submitted less than 1 second ago — rapid-fire / bot behaviour
        "_label": "edge_rapid_submit",
        "name": "SpeedBot",
        "email": "bot@spam.net",
        "company": "Twitter",
        "title": "Software Engineer",
        "level": "L4",
        "location": "San Francisco, CA",
        "years_of_experience": 4,
        "base_salary": 180000,
        "bonus": 20000,
        "stock_rsu": 80000,
        "total_compensation": 280000,
        "ip_address": "172.16.0.1",
        "submitted_at": _ts(0),   # submitted right now
    },
]


# ── Master list (all 15 submissions) ─────────────────────────────────────────
ALL_SUBMISSIONS = (
    VALID_SUBMISSIONS
    + SUSPICIOUS_SUBMISSIONS
    + FAKE_SUBMISSIONS
    + EDGE_CASE_SUBMISSIONS
)


# ── Expected outcomes (used by test_flow.py for assertions) ──────────────────
EXPECTED_OUTCOMES = {
    # label                          : (min_score, max_score, should_pass)
    "valid_google_l4":               (70, 100, True),
    "valid_meta_e5":                 (70, 100, True),
    "valid_microsoft_sde2":          (70, 100, True),
    "valid_amazon_l5":               (70, 100, True),
    "valid_apple_newgrad":           (70, 100, True),
    "suspicious_meta_e6_lowxp":      (30, 69,  False),
    "suspicious_google_math_mismatch":(30, 69, False),
    "suspicious_duplicate_ip":       (30, 69,  False),
    "suspicious_startup_inflated_rsu":(30, 69, False),
    "fake_google_intern_millionaire": (0,  39,  False),
    "fake_amazon_lowball":            (0,  39,  False),
    "fake_negative_salary":           (0,  39,  False),
    "edge_minimal_fields":            (50, 100, True),   # valid but incomplete
    "edge_high_but_plausible":        (50, 100, True),   # high comp, senior role
    "edge_rapid_submit":              (30, 69,  False),  # flagged for timing
}


# ── Batch payload (for POST /api/submissions/batch/) ─────────────────────────
# Strip internal _label key before sending to API
def get_clean_submissions(submission_list: list) -> list:
    """Return a copy of the list with _label keys removed (API-safe)."""
    return [{k: v for k, v in s.items() if k != "_label"} for s in submission_list]