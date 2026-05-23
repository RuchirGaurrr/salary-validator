import os
import re
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

FALLBACK_RESPONSE = {
    "score": 70,
    "flags": [
        {
            "rule": "ai_unavailable",
            "severity": "low",
            "message": "AI plausibility check could not be completed. Defaulting to neutral score."
        }
    ],
    "verdict": "AI validation unavailable — rule-based score is the primary signal."
}


# Prompt
def _build_prompt(data: dict) -> str:
    """
    Constructs a structured prompt that asks Gemini to reason like a
    compensation analyst. We inject the full submission context and demand
    a strict JSON response so we can parse it reliably.

    Key design decisions:
    - Persona framing ("you are a compensation analyst") improves reasoning quality
    - Explicit market context instruction tells Gemini what to focus on
    - Strict JSON schema instruction prevents free-text responses that break parsing
    - We ask for a verdict string so the output is human-readable in the dashboard
    - All numeric fields default to 0 if missing so :, formatter never crashes
    """
    return f"""
You are a senior compensation data analyst reviewing a self-reported salary submission
for Levels.fyi, a platform that aggregates real compensation data from tech professionals.

Your job is to assess whether this submission is plausible based on:
- Market compensation rates for this role, level, and location
- Whether the experience level matches the job title and seniority
- Whether the total compensation breakdown makes narrative sense
- Any subtle red flags a rule engine would miss (e.g. implausible location/company combos)

Here is the submission to evaluate:

Company: {data.get('company', 'Unknown')}
Job Title: {data.get('title', 'Unknown')}
Level: {data.get('level', 'Unknown')}
Location: {data.get('location', 'Unknown')}
Years of Experience: {data.get('years_of_experience', 'Unknown')}
Base Salary: ${data.get('base_salary', 0):,}
Bonus: ${data.get('bonus', 0):,}
Stock/RSU: ${data.get('stock_rsu', 0):,}
Total Compensation: ${data.get('total_compensation', 0):,}

Respond ONLY with a valid JSON object. No preamble, no explanation outside the JSON.
Use exactly this structure:

{{
  "score": <integer 0-100, where 100 = fully plausible, 0 = clearly implausible>,
  "verdict": "<one sentence summary of your overall assessment>",
  "flags": [
    {{
      "rule": "<snake_case_rule_name>",
      "severity": "<high|medium|low>",
      "message": "<specific, actionable explanation of the issue>"
    }}
  ]
}}

If the submission looks fully plausible, return an empty flags array.
Score guidelines:
- 90-100: Completely plausible, matches market rates well
- 70-89: Mostly plausible, minor concerns
- 50-69: Questionable, notable discrepancies from market norms
- 30-49: Unlikely, significant implausibility
- 0-29: Clearly fake or impossible
"""


# Response Parser
def _parse_response(text: str) -> dict:
    """
    Safely parses Gemini's response text into a dict.
    Uses re.sub() to strip ALL markdown code fences (opening and closing)
    in one pass — much more robust than splitting on backticks.
    """
    text = text.strip()
    text = re.sub(r"```json|```", "", text).strip()
    return json.loads(text)


# AI Validator Class

class AIValidator:
    def validate(self, data: dict) -> dict:
        """
        Sends the submission to Gemini and returns a structured validation result.

        Returns:
            {
                "score": int,       # 0-100 plausibility score
                "flags": list,      # list of flag dicts
                "verdict": str      # one-line analyst summary
            }

        On any failure (API error, parse error, missing key), returns FALLBACK_RESPONSE
        with score 70 — benefit of the doubt, as per the interface contract.
        """
        try:
            prompt = _build_prompt(data)

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2  # Low temp = consistent, structured JSON output
                )
            )

            parsed = _parse_response(response.text)

            if "score" not in parsed or "flags" not in parsed:
                raise ValueError("Gemini response missing required fields")
            score = max(0, min(100, int(parsed["score"])))

            return {
                "score": score,
                "flags": parsed.get("flags", []),
                "verdict": parsed.get("verdict", "No verdict provided.")
            }

        except Exception as e:
            print(f"[AIValidator] Error: {e}")
            return FALLBACK_RESPONSE


# Score Merge

def get_combined_score(rule_score: int, ai_score: int) -> int:
    """
    Merges the rule-based score and AI score into a single final confidence score.
    Weighting: 60% rule-based, 40% AI.

    Why 60/40:
    - Rule-based checks are deterministic and always run — they form the foundation
    - AI score adds semantic nuance but can be unavailable or inconsistent
    - Giving rules more weight keeps the system stable even if Gemini fluctuates

    Args:
        rule_score: 0-100 score from validator.py (Person 1)
        ai_score:   0-100 score from AIValidator.validate() (Person 3)

    Returns:
        Final combined score as an integer (0-100)

    Examples:
        get_combined_score(80, 60) → 72
        get_combined_score(100, 100) → 100
        get_combined_score(50, 70) → 58
    """
    return round((rule_score * 0.6) + (ai_score * 0.4))


# ── Standalone Tests ───────────────────────────────────────────────────────────
# Run this file directly to verify your Gemini key works and the validator
# returns sensible output before integrating with Person 2's backend.
#
# Usage: python ai_validator.py
#
if __name__ == "__main__":

    validator = AIValidator()

    # Test 1: Should score HIGH — realistic Google L5 compensation
    print("\n--- Test 1: Realistic Google L5 (expect high score ~85-95) ---")
    good = {
        "name": "Jane Smith",
        "email": "jane@example.com",
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
        "submitted_at": "2024-01-15T10:30:00"
    }
    result = validator.validate(good)
    print(f"Score: {result['score']}")
    print(f"Verdict: {result['verdict']}")
    print(f"Flags: {result['flags']}")

    # Test 2: Should score LOW — rules would pass this (valid range, consistent math)
    # but Gemini should catch: Netflix L5 in Salt Lake City at $95K is implausible.
    # This is your demo moment — the case that proves the AI layer adds value.
    print("\n--- Test 2: Netflix L5 in SLC at $95K (expect low score ~25-45) ---")
    sneaky = {
        "name": "Bob Jones",
        "email": "bob@example.com",
        "company": "Netflix",
        "title": "Senior Software Engineer",
        "level": "L5",
        "location": "Salt Lake City, UT",
        "years_of_experience": 7,
        "base_salary": 95000,
        "bonus": 10000,
        "stock_rsu": 20000,
        "total_compensation": 125000,
        "ip_address": "10.0.0.1",
        "submitted_at": "2024-01-15T11:00:00"
    }
    result = validator.validate(sneaky)
    print(f"Score: {result['score']}")
    print(f"Verdict: {result['verdict']}")
    print(f"Flags: {result['flags']}")

    # Test 3: Fallback behaviour — trigger by passing a corrupt data type
    # that causes _build_prompt or the API call to fail unexpectedly.
    # (Simulating bad API key via module-level client swap is not clean
    # with the new SDK, so we trigger fallback via a guaranteed parse failure instead.)
    print("\n--- Test 3: Fallback on error (expect score 70) ---")
    validator_broken = AIValidator()
    # Pass an object that will cause :, formatting to fail inside _build_prompt
    # after bypassing the .get() defaults — triggers the except block cleanly.
    try:
        broken_client = genai.Client(api_key="invalid_key_to_trigger_fallback")
        original_client = client
        import sys
        sys.modules[__name__].__dict__['client'] = broken_client
        result = validator_broken.validate(good)
    finally:
        sys.modules[__name__].__dict__['client'] = original_client
    print(f"Score: {result['score']} (should be 70)")
    print(f"Flags: {result['flags']}")

    # Test 4: get_combined_score() — verify the merge function works correctly
    print("\n--- Test 4: Score merging (60% rule, 40% AI) ---")
    print(f"rule=80, ai=60   → combined={get_combined_score(80, 60)}  (expect 72)")
    print(f"rule=100, ai=100 → combined={get_combined_score(100, 100)} (expect 100)")
    print(f"rule=50, ai=70   → combined={get_combined_score(50, 70)}  (expect 58)")

    # Test 5: Missing fields — verify no TypeError from :, formatter
    print("\n--- Test 5: Missing numeric fields (expect no crash) ---")
    incomplete = {
        "name": "Ghost User",
        "company": "Unknown Corp",
        "title": "Engineer",
        "level": "L3",
        "location": "Remote",
        "years_of_experience": 2,
        # base_salary, bonus, stock_rsu, total_compensation intentionally missing
    }
    result = validator.validate(incomplete)
    print(f"Score: {result['score']}")
    print(f"Verdict: {result['verdict']}")