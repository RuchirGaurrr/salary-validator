"""
validation/models.py — Database table definition
Each class = one table in SQLite.
Django auto-creates the SQL from this — you never write SQL yourself!
"""

from django.db import models


class Submission(models.Model):
    """
    Stores one salary submission + its validation result.
    When someone POSTs to /api/submissions/, a row is created here.
    """

    # ── Submission fields
    name = models.CharField(max_length=200)
    email = models.EmailField()
    company = models.CharField(max_length=200)
    title = models.CharField(max_length=200)
    level = models.CharField(max_length=50)
    location = models.CharField(max_length=200)
    years_of_experience = models.IntegerField()
    base_salary = models.IntegerField()
    bonus = models.IntegerField(default=0)
    stock_rsu = models.IntegerField(default=0)
    total_compensation = models.IntegerField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    # ── Validation result fields (filled after running validators) ─────────────
    # overall_score: 0-100, calculated as (rule_score * 0.6) + (ai_score * 0.4)
    overall_score = models.IntegerField(null=True, blank=True)

    # rule_score: score from validator.py (Person 1's file)
    rule_score = models.IntegerField(null=True, blank=True)

    # ai_score: score from ai_validator.py (Person 3's file)
    ai_score = models.IntegerField(null=True, blank=True)

    # confidence_level: "high", "medium", or "low"
    confidence_level = models.CharField(max_length=20, null=True, blank=True)

    # passed: True if overall_score >= 60
    passed = models.BooleanField(null=True, blank=True)

    # flags: stored as JSON — list of {rule, severity, message} dicts
    flags = models.JSONField(default=list)

    # When this record was created in our DB
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]   # Newest submissions first

    def __str__(self):
        # This shows up in the admin panel
        return f"{self.name} @ {self.company} — Score: {self.overall_score}"
