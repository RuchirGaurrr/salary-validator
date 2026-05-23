"""
seed_data.py
------------
Populates the database by POSTing all sample submissions to the running Django
API.  Run this AFTER `python manage.py runserver` is up.

Usage:
    python seed_data.py                    # uses default http://127.0.0.1:8000
    python seed_data.py --url http://...   # custom base URL
    python seed_data.py --batch            # use batch endpoint instead

What it does:
  1. POSTs each submission from sample_data.py to POST /api/submissions/
  2. Prints a colour-coded result table (score, passed, flags)
  3. Optionally runs a batch POST at the end to test that endpoint too
  4. Exits with code 1 if any HTTP error occurs (useful in CI)
"""

import argparse
import json
import sys
import time
from typing import Any

# ── Try requests; give a clear error if missing ───────────────────────────────
try:
    import requests
except ImportError:
    sys.exit(
        "❌  'requests' not found.  Run:  pip install requests\n"
        "    (it's already in requirements.txt)"
    )

import os

# ── Load submissions from seed_data.json (works from any working directory) ──
_HERE = os.path.dirname(os.path.abspath(__file__))
_JSON_PATH = os.path.join(_HERE, "seed_data.json")

with open(_JSON_PATH) as _f:
    _RAW = json.load(_f)

# Recreate the category splits by index (matches sample_data.py order):
#   0–4   = valid (5 entries)
#   5–8   = suspicious (4 entries)
#   9–11  = fake (3 entries)
#   12–14 = edge cases (3 entries)
VALID_SUBMISSIONS      = _RAW[0:5]
SUSPICIOUS_SUBMISSIONS = _RAW[5:9]
FAKE_SUBMISSIONS       = _RAW[9:12]
EDGE_CASE_SUBMISSIONS  = _RAW[12:15]
ALL_SUBMISSIONS        = _RAW

def get_clean_submissions(submission_list: list) -> list:
    """Already clean — JSON has no _label keys."""
    return submission_list

# ── ANSI colour helpers (degrade gracefully on Windows) ──────────────────────
_SUPPORTS_COLOR = sys.stdout.isatty()

def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _SUPPORTS_COLOR else text

GREEN  = lambda t: _c(t, "32")
YELLOW = lambda t: _c(t, "33")
RED    = lambda t: _c(t, "31")
CYAN   = lambda t: _c(t, "36")
BOLD   = lambda t: _c(t, "1")


# ── Core seeding logic ────────────────────────────────────────────────────────

def post_submission(base_url: str, payload: dict) -> dict | None:
    """
    POST a single submission to the API.
    Returns the parsed JSON response, or None on network/HTTP error.
    """
    url = f"{base_url.rstrip('/')}/api/submissions/"
    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        print(RED(f"  ✗  Cannot connect to {url}  — is the server running?"))
        return None
    except requests.exceptions.HTTPError as exc:
        print(RED(f"  ✗  HTTP {exc.response.status_code}: {exc.response.text[:200]}"))
        return None
    except Exception as exc:
        print(RED(f"  ✗  Unexpected error: {exc}"))
        return None


def post_batch(base_url: str, payloads: list) -> dict | None:
    """POST a batch of submissions to POST /api/submissions/batch/"""
    url = f"{base_url.rstrip('/')}/api/submissions/batch/"
    try:
        resp = requests.post(url, json={"submissions": payloads}, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        print(RED(f"  ✗  Cannot connect to {url}"))
        return None
    except requests.exceptions.HTTPError as exc:
        print(RED(f"  ✗  HTTP {exc.response.status_code}: {exc.response.text[:200]}"))
        return None
    except Exception as exc:
        print(RED(f"  ✗  Unexpected error: {exc}"))
        return None


def _score_colour(score: int) -> str:
    """Colour-code a score: green ≥70, yellow 40–69, red <40."""
    if score >= 70:
        return GREEN(str(score))
    elif score >= 40:
        return YELLOW(str(score))
    return RED(str(score))


def _flag_summary(flags: list) -> str:
    """Return a short human-readable summary of validation flags."""
    if not flags:
        return GREEN("none")
    high   = [f for f in flags if f.get("severity") == "high"]
    medium = [f for f in flags if f.get("severity") == "medium"]
    low    = [f for f in flags if f.get("severity") == "low"]
    parts  = []
    if high:   parts.append(RED(f"{len(high)} high"))
    if medium: parts.append(YELLOW(f"{len(medium)} med"))
    if low:    parts.append(f"{len(low)} low")
    return ", ".join(parts) if parts else "—"


def print_result_row(label: str, payload: dict, result: dict | None) -> None:
    """Print a single formatted result row to stdout."""
    name    = payload.get("company", "?") + " / " + payload.get("title", "?")
    if result is None:
        print(f"  {RED('FAIL')}  {label:<40}  {name}")
        return

    score      = result.get("overall_score", result.get("score", "—"))
    passed     = result.get("passed", False)
    confidence = result.get("confidence_level", "—")
    flags      = result.get("flags", [])

    passed_str = GREEN("✓ PASS") if passed else RED("✗ FAIL")
    score_str  = _score_colour(score) if isinstance(score, int) else str(score)

    print(
        f"  {passed_str}  "
        f"{label:<42}  "
        f"score={score_str:>3}  "
        f"conf={confidence:<6}  "
        f"flags=[{_flag_summary(flags)}]"
    )


def seed_individually(base_url: str, submissions: list, delay: float = 0.3) -> int:
    """
    POST each submission one-by-one.
    Returns the number of failures.
    """
    failures = 0
    for sub in submissions:
        label   = sub.get("_label", "unknown")
        payload = {k: v for k, v in sub.items() if k != "_label"}  # strip internal key
        result  = post_submission(base_url, payload)
        print_result_row(label, payload, result)
        if result is None:
            failures += 1
        time.sleep(delay)  # avoid hammering the server in quick succession
    return failures


def print_section_header(title: str) -> None:
    bar = "─" * 80
    print(f"\n{CYAN(bar)}")
    print(BOLD(f"  {title}"))
    print(CYAN(bar))


def fetch_dashboard_stats(base_url: str) -> None:
    """Print a summary from GET /api/dashboard/stats/"""
    url = f"{base_url.rstrip('/')}/api/dashboard/stats/"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        stats = resp.json()
        print(BOLD("\n  📊  Dashboard Stats"))
        print(f"      Total submissions : {stats.get('total', '—')}")
        print(f"      Passed            : {GREEN(str(stats.get('passed', '—')))}")
        print(f"      Flagged           : {RED(str(stats.get('flagged', '—')))}")
        print(f"      Average score     : {stats.get('average_score', '—')}")
    except Exception as exc:
        print(YELLOW(f"  ⚠  Could not fetch dashboard stats: {exc}"))


# ── CLI entry-point ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the database with sample salary submissions")
    parser.add_argument(
        "--url", default="http://127.0.0.1:8000",
        help="Base URL of the Django API (default: http://127.0.0.1:8000)"
    )
    parser.add_argument(
        "--batch", action="store_true",
        help="Also run a batch POST after individual seeds"
    )
    parser.add_argument(
        "--delay", type=float, default=0.3,
        help="Seconds between individual POSTs (default: 0.3)"
    )
    args = parser.parse_args()

    total_failures = 0

    # ── Section 1: Valid submissions ──────────────────────────────────────────
    print_section_header("1 / 4  —  VALID SUBMISSIONS  (expect: all PASS, score ≥ 70)")
    total_failures += seed_individually(args.url, VALID_SUBMISSIONS, args.delay)

    # ── Section 2: Suspicious submissions ────────────────────────────────────
    print_section_header("2 / 4  —  SUSPICIOUS SUBMISSIONS  (expect: FAIL, score 40–69)")
    total_failures += seed_individually(args.url, SUSPICIOUS_SUBMISSIONS, args.delay)

    # ── Section 3: Fake submissions ───────────────────────────────────────────
    print_section_header("3 / 4  —  OBVIOUSLY FAKE SUBMISSIONS  (expect: FAIL, score < 40)")
    total_failures += seed_individually(args.url, FAKE_SUBMISSIONS, args.delay)

    # ── Section 4: Edge cases ────────────────────────────────────────────────
    print_section_header("4 / 4  —  EDGE CASES  (mixed expectations)")
    total_failures += seed_individually(args.url, EDGE_CASE_SUBMISSIONS, args.delay)

    # ── Optional: Batch endpoint ─────────────────────────────────────────────
    if args.batch:
        print_section_header("BONUS  —  BATCH ENDPOINT  (/api/submissions/batch/)")
        batch_payload = get_clean_submissions(VALID_SUBMISSIONS[:3])
        result = post_batch(args.url, batch_payload)
        if result:
            results = result.get("results", [])
            print(f"  Batch returned {len(results)} result(s)")
            for i, r in enumerate(results, 1):
                score   = r.get("overall_score", r.get("score", "—"))
                passed  = r.get("passed", False)
                status  = GREEN("✓") if passed else RED("✗")
                print(f"  {status}  Entry {i}  score={_score_colour(score) if isinstance(score, int) else score}")
        else:
            print(RED("  Batch request failed."))
            total_failures += 1

    # ── Dashboard summary ─────────────────────────────────────────────────────
    fetch_dashboard_stats(args.url)

    # ── Final report ─────────────────────────────────────────────────────────
    total = len(ALL_SUBMISSIONS)
    print(f"\n{'─'*80}")
    if total_failures == 0:
        print(GREEN(f"  ✅  All {total} submissions seeded successfully."))
    else:
        print(RED(f"  ⚠  {total_failures}/{total} submissions failed to seed."))
    print(f"  Admin panel:  {args.url}/admin/\n")

    sys.exit(1 if total_failures > 0 else 0)


if __name__ == "__main__":
    main()
