"""
validation/admin.py — Admin panel configuration
This makes your submissions visible and searchable at http://localhost:8000/admin/
This IS your demo dashboard — no extra frontend needed for the presentation!
"""

from django.contrib import admin
from .models import Submission


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    # Columns shown in the submissions list table
    list_display = [
        "name",
        "company",
        "title",
        "level",
        "base_salary",
        "overall_score",
        "confidence_level",
        "passed",
        "created_at",
    ]

    # Clickable filters on the right sidebar
    list_filter = [
        "passed",
        "confidence_level",
        "company",
    ]

    # Search bar at the top — searches these fields
    search_fields = [
        "name",
        "email",
        "company",
        "title",
        "location",
    ]

    # Default sort: newest first
    ordering = ["-created_at"]

    # Make validation result fields read-only (set by the system, not manually)
    readonly_fields = [
        "overall_score",
        "rule_score",
        "ai_score",
        "confidence_level",
        "passed",
        "flags",
        "created_at",
    ]

    # Group fields nicely in the detail view
    fieldsets = (
        ("Submission Info", {
            "fields": ("name", "email", "company", "title", "level", "location",
                       "years_of_experience", "submitted_at", "ip_address")
        }),
        ("Compensation", {
            "fields": ("base_salary", "bonus", "stock_rsu", "total_compensation")
        }),
        ("Validation Results", {
            "fields": ("overall_score", "rule_score", "ai_score",
                       "confidence_level", "passed", "flags")
        }),
        ("Metadata", {
            "fields": ("created_at",)
        }),
    )
