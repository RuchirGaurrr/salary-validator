"""
test_flow.py
------------
Standalone QA test suite for the entire validation pipeline.
Runs BEFORE integration — no Django server required for the validator unit tests,
and WITH a running server for the API / end-to-end tests.

Test Layers
  Layer 1: Data integrity  — verify sample_data.py is well-formed
  Layer 2: Validator unit  — import and call validator.py directly (no server)
  Layer 3: API contract    — POST/GET against the live Django API
  Layer 4: Edge cases      — missing fields, batch endpoint, duplicate IP
  Layer 5: Dashboard stats — verify aggregated metrics update correctly

Usage
  # Run all layers (server must be running for layers 3–5)
  python test_flow.py

  # Run only offline layers (no server needed)
  python test_flow.py --offline

  # Target a remote/different URL
  python test_flow.py --url http://127.0.0.1:8000
"""

import argparse
import importlib
import json
import sys
import traceback
from typing import Any, Optional

try:
    import requests
except ImportError:
    sys.exit("❌  Run:  pip install requests")

from sample_data import (
    ALL_SUBMISSIONS,
    VALID_SUBMISSIONS,
    SUSPICIOUS_SUBMISSIONS,
    FAKE_SUBMISSIONS,
    EDGE_CASE_SUBMISSIONS,
    EXPECTED_OUTCOMES,
    get_clean_submissions,
)

# ── Colour helpers ────────────────────────────────────────────────────────────
_TTY = sys.stdout.isatty()

def _c(t, code): return f"\033[{code}m{t}\033[0m" if _TTY else t

OK   = lambda t: _c(t, "32")
WARN = lambda t: _c(t, "33")
FAIL = lambda t: _c(t, "31")
CYAN = lambda t: _c(t, "36")
BOLD = lambda t: _c(t, "1")


# ── Test harness helpers ──────────────────────────────────────────────────────

_passed = 0
_failed = 0
_skipped = 0

def _result(name: str, ok: bool, detail: str = "") -> None:
    global _passed, _failed
    if ok:
        _passed += 1
        print(f"  {OK('✓')}  {name}")
    else:
        _failed += 1
        msg = f"  {FAIL('✗')}  {name}"
        if detail:
            msg += f"\n      {FAIL('→')} {detail}"
        print(msg)

def _skip(name: str, reason: str) -> None:
    global _skipped
    _skipped += 1
    print(f"  {WARN('–')}  {name}  {WARN(f'(skipped: {reason})')}")

def _section(title: str) -> None:
    bar = "─" * 72
    print(f"\n{CYAN(bar)}\n{BOLD('  ' + title)}\n{CYAN(bar)}")


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 1  —  Data integrity (no imports beyond sample_data)
# ═══════════════════════════════════════════════════════════════════════════════

def test_layer_1_data_integrity() -> None:
    _section("LAYER 1  —  Data Integrity (sample_data.py)")

    required_fields = {
        "company", "title", "level", "location",
        "years_of_experience", "base_salary", "total_compensation",
    }

    # 1.1  Total count
    _result("Sample data has 15 submissions", len(ALL_SUBMISSIONS) == 15,
            f"got {len(ALL_SUBMISSIONS)}")

    # 1.2  Each submission has required fields
    all_have_fields = all(
        required_fields.issubset(s.keys()) for s in ALL_SUBMISSIONS
    )
    _result("All submissions contain required fields", all_have_fields)

    # 1.3  No submission is missing a _label (used by tests)
    all_labeled = all("_label" in s for s in ALL_SUBMISSIONS)
    _result("All submissions have an internal _label key", all_labeled)

    # 1.4  EXPECTED_OUTCOMES covers every label
    labels_in_data     = {s["_label"] for s in ALL_SUBMISSIONS}
    labels_in_expected = set(EXPECTED_OUTCOMES.keys())
    _result(
        "EXPECTED_OUTCOMES covers all submission labels",
        labels_in_data == labels_in_expected,
        f"missing: {labels_in_data - labels_in_expected}",
    )

    # 1.5  get_clean_submissions strips _label
    clean = get_clean_submissions(ALL_SUBMISSIONS[:3])
    _result(
        "get_clean_submissions() removes _label key",
        all("_label" not in s for s in clean),
    )

    # 1.6  total_compensation ≥ base_salary for valid entries
    for sub in VALID_SUBMISSIONS:
        ok = sub["total_compensation"] >= sub["base_salary"]
        _result(
            f"  total_comp ≥ base_salary  [{sub['_label']}]",
            ok,
            f"total={sub['total_compensation']} < base={sub['base_salary']}",
        )

    # 1.7  At least one fake entry has obviously wrong numbers
    fake_salaries = [s["base_salary"] for s in FAKE_SUBMISSIONS]
    has_outlier = any(s > 400_000 or s < 0 for s in fake_salaries)
    _result("Fake submissions contain at least one obvious outlier", has_outlier)


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 2  —  Validator unit tests (no server required)
# ═══════════════════════════════════════════════════════════════════════════════

def test_layer_2_validator_unit(offline: bool) -> None:
    _section("LAYER 2  —  Rule-Based Validator Unit Tests (validator.py)")

    # Try to import Person 1's validator
    try:
        validator_module = importlib.import_module("validator")
        # Validator class names may vary; try common names
        ValidatorClass = None
        for name in ("SalaryValidator", "Validator", "RuleBasedValidator"):
            if hasattr(validator_module, name):
                ValidatorClass = getattr(validator_module, name)
                break
        if ValidatorClass is None:
            raise ImportError("No recognisable validator class found in validator.py")
        v = ValidatorClass()
    except (ModuleNotFoundError, ImportError) as exc:
        _skip("All validator unit tests", f"validator.py not importable: {exc}")
        return

    # 2.1  Interface contract: validate() exists
    _result("Validator exposes .validate() method", hasattr(v, "validate") and callable(v.validate))

    def _run(label: str, sub: dict) -> Optional[dict]:
        """Call validate(), catch exceptions, return result or None."""
        payload = {k: v for k, v in sub.items() if k != "_label"}
        try:
            return v.validate(payload)
        except Exception as exc:
            _result(f"  validate() did not raise for [{label}]", False, str(exc))
            return None

    # 2.2  Output structure check
    sample_result = _run("valid_google_l4", VALID_SUBMISSIONS[0])
    if sample_result is not None:
        has_score = "score" in sample_result and isinstance(sample_result["score"], (int, float))
        has_flags = "flags" in sample_result and isinstance(sample_result["flags"], list)
        _result("validate() returns dict with 'score' (int/float)", has_score,
                f"got keys: {list(sample_result.keys())}")
        _result("validate() returns dict with 'flags' (list)", has_flags)

    # 2.3  Score is in 0–100 range for each submission
    for sub in ALL_SUBMISSIONS[:6]:  # run first 6 to keep tests fast
        label  = sub["_label"]
        result = _run(label, sub)
        if result:
            score = result.get("score", -1)
            _result(f"  score in [0, 100]  [{label}]", 0 <= score <= 100,
                    f"got score={score}")

    # 2.4  Valid entries score higher than fake entries (sanity check)
    valid_scores = []
    fake_scores  = []
    for sub in VALID_SUBMISSIONS:
        r = _run(sub["_label"], sub)
        if r: valid_scores.append(r.get("score", 0))
    for sub in FAKE_SUBMISSIONS:
        r = _run(sub["_label"], sub)
        if r: fake_scores.append(r.get("score", 0))

    if valid_scores and fake_scores:
        avg_valid = sum(valid_scores) / len(valid_scores)
        avg_fake  = sum(fake_scores)  / len(fake_scores)
        _result(
            f"Avg valid score ({avg_valid:.0f}) > avg fake score ({avg_fake:.0f})",
            avg_valid > avg_fake,
        )

    # 2.5  Validator handles negative salary gracefully (no crash)
    neg_sub = {k: v for k, v in FAKE_SUBMISSIONS[2].items() if k != "_label"}
    try:
        r = v.validate(neg_sub)
        _result("Validator handles negative salary without crashing", True)
        has_flags = len(r.get("flags", [])) > 0
        _result("Validator flags negative salary", has_flags)
    except Exception as exc:
        _result("Validator handles negative salary without crashing", False, str(exc))

    # 2.6  Validator handles completely empty dict gracefully
    try:
        r = v.validate({})
        _result("Validator handles empty dict without crashing", True)
    except Exception as exc:
        _result("Validator handles empty dict without crashing", False, str(exc))


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 3  —  API contract tests (server required)
# ═══════════════════════════════════════════════════════════════════════════════

def _api_post(base_url: str, path: str, payload: dict) -> Optional[dict]:
    """POST helper — returns parsed JSON or None."""
    try:
        r = requests.post(f"{base_url}{path}", json=payload, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def _api_get(base_url: str, path: str, params: dict = None) -> Optional[dict]:
    """GET helper — returns parsed JSON or None."""
    try:
        r = requests.get(f"{base_url}{path}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def _server_reachable(base_url: str) -> bool:
    try:
        requests.get(base_url, timeout=3)
        return True
    except Exception:
        return False


def test_layer_3_api_contract(base_url: str) -> None:
    _section("LAYER 3  —  API Contract Tests (requires running server)")

    if not _server_reachable(base_url):
        _skip("All API tests", f"Server not reachable at {base_url}")
        return

    # ── 3.1  POST /api/submissions/ — valid submission ─────────────────────
    payload = get_clean_submissions([VALID_SUBMISSIONS[0]])[0]
    resp = _api_post(base_url, "/api/submissions/", payload)

    _result("POST /api/submissions/ returns 200", resp is not None)
    if resp:
        _result("Response contains 'overall_score'",
                "overall_score" in resp or "score" in resp,
                f"keys: {list(resp.keys())}")
        _result("Response contains 'passed'",  "passed"  in resp)
        _result("Response contains 'flags'",   "flags"   in resp)
        _result("Response contains 'confidence_level'", "confidence_level" in resp)

        score = resp.get("overall_score", resp.get("score", -1))
        _result(f"Valid entry score ≥ 70  (got {score})", score >= 70, f"score={score}")
        _result("Valid entry passed=True", resp.get("passed") is True)

    # ── 3.2  POST /api/submissions/ — fake submission ──────────────────────
    fake_payload = get_clean_submissions([FAKE_SUBMISSIONS[0]])[0]
    fake_resp = _api_post(base_url, "/api/submissions/", fake_payload)

    _result("POST /api/submissions/ handles fake entry", fake_resp is not None)
    if fake_resp:
        fake_score = fake_resp.get("overall_score", fake_resp.get("score", 100))
        _result(f"Fake entry score < 70  (got {fake_score})", fake_score < 70)
        _result("Fake entry passed=False", fake_resp.get("passed") is False)
        _result("Fake entry has flags", len(fake_resp.get("flags", [])) > 0)

    # ── 3.3  GET /api/submissions/ ─────────────────────────────────────────
    list_resp = _api_get(base_url, "/api/submissions/")
    _result("GET /api/submissions/ returns data", list_resp is not None)
    if list_resp:
        is_list_or_paginated = isinstance(list_resp, list) or "results" in list_resp
        _result("Response is a list or paginated object", is_list_or_paginated)

    # ── 3.4  GET /api/submissions/?filter=flagged ──────────────────────────
    flagged_resp = _api_get(base_url, "/api/submissions/", {"filter": "flagged"})
    _result("GET /api/submissions/?filter=flagged returns data", flagged_resp is not None)

    # ── 3.5  GET /api/dashboard/stats/ ────────────────────────────────────
    stats = _api_get(base_url, "/api/dashboard/stats/")
    _result("GET /api/dashboard/stats/ returns data", stats is not None)
    if stats:
        for key in ("total", "passed", "flagged", "average_score"):
            _result(f"  stats contains '{key}'", key in stats)


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 4  —  Edge case and stress tests (server required)
# ═══════════════════════════════════════════════════════════════════════════════

def test_layer_4_edge_cases(base_url: str) -> None:
    _section("LAYER 4  —  Edge Cases & Stress Tests")

    if not _server_reachable(base_url):
        _skip("All edge case tests", f"Server not reachable at {base_url}")
        return

    # ── 4.1  Missing optional fields ──────────────────────────────────────
    minimal = {
        "name": "Minimal User",
        "email": "minimal@test.com",
        "company": "Stripe",
        "title": "Software Engineer",
        "level": "L4",
        "location": "Remote",
        "years_of_experience": 5,
        "base_salary": 160000,
        "bonus": 0,
        "stock_rsu": 0,
        "total_compensation": 160000,
        "ip_address": "203.0.113.200",
        "submitted_at": "2024-06-01T10:00:00",
    }
    r = _api_post(base_url, "/api/submissions/", minimal)
    _result("Minimal fields submission accepted (no 500)", r is not None)

    # ── 4.2  Negative salary ───────────────────────────────────────────────
    neg = get_clean_submissions([FAKE_SUBMISSIONS[2]])[0]
    r = _api_post(base_url, "/api/submissions/", neg)
    _result("Negative salary does not crash API (no 500)", r is not None)
    if r:
        score = r.get("overall_score", r.get("score", 100))
        _result(f"Negative salary scores low  (got {score})", score < 40)

    # ── 4.3  Batch endpoint ────────────────────────────────────────────────
    batch_payload = get_clean_submissions(VALID_SUBMISSIONS[:3])
    r = _api_post(base_url, "/api/submissions/batch/", {"submissions": batch_payload})
    _result("POST /api/submissions/batch/ returns data", r is not None)
    if r:
        results = r.get("results", r if isinstance(r, list) else [])
        _result(f"Batch returns 3 results  (got {len(results)})", len(results) == 3)

    # ── 4.4  Duplicate IP ─────────────────────────────────────────────────
    dup_ip_sub = get_clean_submissions([SUSPICIOUS_SUBMISSIONS[2]])[0]
    r = _api_post(base_url, "/api/submissions/", dup_ip_sub)
    _result("Duplicate IP submission accepted (no 500)", r is not None)
    if r:
        flags = r.get("flags", [])
        has_dup_flag = any("ip" in str(f).lower() or "duplicate" in str(f).lower() for f in flags)
        _result("Duplicate IP triggers an IP-related flag", has_dup_flag,
                "no flag mentioning 'ip' or 'duplicate' found")

    # ── 4.5  Total comp mismatch ──────────────────────────────────────────
    mismatch = get_clean_submissions([SUSPICIOUS_SUBMISSIONS[1]])[0]
    r = _api_post(base_url, "/api/submissions/", mismatch)
    _result("Math-mismatch submission accepted (no 500)", r is not None)
    if r:
        score = r.get("overall_score", r.get("score", 100))
        _result(f"Math-mismatch scores below 70  (got {score})", score < 70)


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 5  —  Dashboard stats sanity check
# ═══════════════════════════════════════════════════════════════════════════════

def test_layer_5_dashboard(base_url: str) -> None:
    _section("LAYER 5  —  Dashboard Stats Sanity Checks")

    if not _server_reachable(base_url):
        _skip("All dashboard tests", f"Server not reachable at {base_url}")
        return

    stats = _api_get(base_url, "/api/dashboard/stats/")
    if not stats:
        _result("Dashboard stats reachable", False)
        return

    _result("Dashboard stats reachable", True)

    total  = stats.get("total", 0)
    passed = stats.get("passed", 0)
    flagged = stats.get("flagged", 0)
    avg_score = stats.get("average_score", 0)

    _result(f"total ≥ 1  (got {total})",  total >= 1)
    _result(f"passed ≤ total  (got {passed}/{total})", passed <= total)
    _result(f"flagged ≤ total  (got {flagged}/{total})", flagged <= total)
    _result(
        f"passed + flagged ≤ total  ({passed}+{flagged}≤{total})",
        passed + flagged <= total,
    )
    _result(f"avg_score in [0, 100]  (got {avg_score})", 0 <= avg_score <= 100)


# ═══════════════════════════════════════════════════════════════════════════════
# Main runner
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full validation pipeline test suite")
    parser.add_argument("--url",     default="http://127.0.0.1:8000",
                        help="API base URL  (default: http://127.0.0.1:8000)")
    parser.add_argument("--offline", action="store_true",
                        help="Only run offline tests (layers 1–2)")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")

    # Always run offline layers
    test_layer_1_data_integrity()
    test_layer_2_validator_unit(offline=args.offline)

    # Online layers
    if not args.offline:
        test_layer_3_api_contract(base_url)
        test_layer_4_edge_cases(base_url)
        test_layer_5_dashboard(base_url)
    else:
        print(WARN("\n  ⚠  Skipped API tests (--offline mode)"))

    # ── Final summary ─────────────────────────────────────────────────────
    total = _passed + _failed + _skipped
    bar   = "═" * 72
    print(f"\n{CYAN(bar)}")
    print(BOLD("  RESULTS"))
    print(f"  {OK(f'Passed:  {_passed}')}")
    if _failed:
        print(f"  {FAIL(f'Failed:  {_failed}')}")
    if _skipped:
        print(f"  {WARN(f'Skipped: {_skipped}')}")
    print(f"  Total:   {total}")
    print(CYAN(bar))

    if _failed > 0:
        print(FAIL(f"\n  ❌  {_failed} test(s) failed — review output above before integrating.\n"))
        sys.exit(1)
    else:
        print(OK(f"\n  ✅  All tests passed!  Safe to integrate.\n"))
        sys.exit(0)


if __name__ == "__main__":
    main()