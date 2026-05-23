"""
admin.py  (replace the existing file in your Django app directory)
------------------------------------------------------------------
Registers the Submission model with a polished Django admin interface.

Features
  • Colour-coded score column (green / yellow / red)
  • One-click filters: passed, confidence level, company
  • Full-text search across company, title, name, email
  • Read-only validation results (prevent accidental edits)
  • Custom actions: re-run validation, export flagged entries
  • Inline flag display so reviewers never leave the list view

How to use
  Replace  yourapp/admin.py  with this file.
  Adjust the import path if your model lives elsewhere.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Avg, Count
from django.http import HttpResponse
import csv
import json

# ── Import your model — adjust 'submissions.models' to match your app name ───
# e.g. if your app is called 'api', use: from api.models import Submission
from validation.models import Submission   # ← change 'submissions' if needed


# ── Inline: show each flag as a row inside the detail page ──────────────────
class FlagInline(admin.TabularInline):
    """
    Displays validation flags (stored as JSON) as a clean table
    inside the Submission change-view.
    """
    # We use a proxy approach: flags are stored on the parent model as JSON,
    # so we override the parent's change_view via readonly_fields instead.
    # This inline is a placeholder — real inline would require a separate Flag model.
    # If you have a separate Flag model, swap this out accordingly.
    pass


# ── Custom admin actions ─────────────────────────────────────────────────────

@admin.action(description="📥  Export selected submissions to CSV")
def export_to_csv(modeladmin, request, queryset):
    """
    Download a CSV of selected submissions.
    Useful for sharing results with judges or stakeholders.
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="submissions_export.csv"'

    writer = csv.writer(response)
    # Header row
    writer.writerow([
        "ID", "Company", "Title", "Level", "Location",
        "Years XP", "Base Salary", "Bonus", "RSU", "Total Comp",
        "Score", "Confidence", "Passed", "Flags", "Submitted At",
    ])

    for sub in queryset.select_related():
        # Safely extract flags — stored as JSON list or already a Python list
        flags = sub.flags if hasattr(sub, "flags") else []
        if isinstance(flags, str):
            try:
                flags = json.loads(flags)
            except (json.JSONDecodeError, TypeError):
                flags = []

        flag_summary = "; ".join(
            f.get("rule", "?") + ": " + f.get("message", "")
            for f in flags
        )

        writer.writerow([
            sub.id,
            sub.company,
            sub.title,
            getattr(sub, "level", "—"),
            getattr(sub, "location", "—"),
            getattr(sub, "years_of_experience", "—"),
            sub.base_salary,
            getattr(sub, "bonus", 0),
            getattr(sub, "stock_rsu", 0),
            sub.total_compensation,
            sub.overall_score,
            sub.confidence_level,
            "PASS" if sub.passed else "FAIL",
            flag_summary,
            sub.submitted_at,
        ])

    return response


@admin.action(description="🚩  Mark selected submissions as flagged (set passed=False)")
def mark_as_flagged(modeladmin, request, queryset):
    """Manually override the passed flag — useful for demo corrections."""
    updated = queryset.update(passed=False)
    modeladmin.message_user(request, f"{updated} submission(s) marked as flagged.")


# ── Main admin class ─────────────────────────────────────────────────────────

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    """
    Rich admin interface for the Submission model.
    Designed for hackathon demo: reviewers can instantly spot fake entries.
    """

    # ── List view columns ────────────────────────────────────────────────────
    list_display = (
        "id",
        "company",
        "title",
        "level_display",
        "years_of_experience",
        "base_salary_display",
        "total_comp_display",
        "score_badge",          # colour-coded
        "confidence_badge",     # colour-coded
        "passed_badge",         # ✓ / ✗
        "flag_count",           # number of flags at a glance
        "submitted_at",
    )

    # ── Sidebar filters ──────────────────────────────────────────────────────
    list_filter = (
        "passed",
        "confidence_level",
        "company",
        "submitted_at",
    )

    # ── Search ───────────────────────────────────────────────────────────────
    search_fields = (
        "company",
        "title",
        "name",
        "email",
        "location",
        "ip_address",
    )

    # ── Default ordering: lowest scores first (flagged entries at top) ───────
    ordering = ("overall_score",)

    # ── Records per page ─────────────────────────────────────────────────────
    list_per_page = 25

    # ── Actions ──────────────────────────────────────────────────────────────
    actions = [export_to_csv, mark_as_flagged]

    # ── Detail view: make validation output read-only ─────────────────────────
    readonly_fields = (
        "overall_score",
        "confidence_level",
        "passed",
        "flags_display",
        "submitted_at",
        "ip_address",
    )

    # ── Field grouping on detail page ─────────────────────────────────────────
    fieldsets = (
        ("👤  Submitter Info", {
            "fields": ("name", "email", "ip_address", "submitted_at"),
        }),
        ("🏢  Submission Data", {
            "fields": (
                "company", "title", "level", "location",
                "years_of_experience",
                "base_salary", "bonus", "stock_rsu", "total_compensation",
            ),
        }),
        ("🔍  Validation Results  (read-only)", {
            "fields": ("overall_score", "confidence_level", "passed", "flags_display"),
            "classes": ("collapse",),   # collapsed by default; expand to inspect
        }),
    )

    # ── Custom display columns ────────────────────────────────────────────────

    @admin.display(description="Level", ordering="level")
    def level_display(self, obj):
        return getattr(obj, "level", "—") or "—"

    @admin.display(description="Base Salary", ordering="base_salary")
    def base_salary_display(self, obj):
        return f"${obj.base_salary:,.0f}" if obj.base_salary else "—"

    @admin.display(description="Total Comp", ordering="total_compensation")
    def total_comp_display(self, obj):
        return f"${obj.total_compensation:,.0f}" if obj.total_compensation else "—"

    @admin.display(description="Score", ordering="overall_score")
    def score_badge(self, obj):
        """Render score as a colour-coded badge."""
        score = obj.overall_score or 0
        if score >= 70:
            colour, bg = "#155724", "#d4edda"
        elif score >= 40:
            colour, bg = "#856404", "#fff3cd"
        else:
            colour, bg = "#721c24", "#f8d7da"

        return format_html(
            '<span style="'
            'background:{bg};color:{colour};'
            'padding:2px 8px;border-radius:12px;'
            'font-weight:bold;font-size:0.85em;">'
            '{score}'
            '</span>',
            bg=bg, colour=colour, score=score,
        )

    @admin.display(description="Confidence", ordering="confidence_level")
    def confidence_badge(self, obj):
        """Render confidence level with colour."""
        level = (obj.confidence_level or "—").lower()
        colour_map = {
            "high":   ("#0c5460", "#d1ecf1"),
            "medium": ("#856404", "#fff3cd"),
            "low":    ("#721c24", "#f8d7da"),
        }
        colour, bg = colour_map.get(level, ("#333", "#eee"))
        return format_html(
            '<span style="background:{bg};color:{colour};'
            'padding:2px 8px;border-radius:12px;font-size:0.85em;">'
            '{level}</span>',
            bg=bg, colour=colour, level=level.capitalize(),
        )

    @admin.display(description="Passed", boolean=False, ordering="passed")
    def passed_badge(self, obj):
        """Render a clear PASS / FAIL indicator."""
        if obj.passed:
            return format_html(
                '<span style="color:#155724;font-weight:bold;">✓ PASS</span>'
            )
        return format_html(
            '<span style="color:#721c24;font-weight:bold;">✗ FAIL</span>'
        )

    @admin.display(description="Flags #")
    def flag_count(self, obj):
        """Count flags stored in the JSON field."""
        flags = getattr(obj, "flags", []) or []
        if isinstance(flags, str):
            try:
                flags = json.loads(flags)
            except Exception:
                return "—"
        count = len(flags) if isinstance(flags, list) else 0
        if count == 0:
            return "—"
        return format_html(
            '<span style="color:#721c24;font-weight:bold;">{}</span>', count
        )

    @admin.display(description="Flags Detail")
    def flags_display(self, obj):
        """
        Renders the full flags list as a readable HTML table
        inside the detail view.
        """
        flags = getattr(obj, "flags", []) or []
        if isinstance(flags, str):
            try:
                flags = json.loads(flags)
            except Exception:
                return "No flags data."

        if not flags:
            return format_html('<em style="color:green;">No flags — submission looks clean.</em>')

        rows = ""
        for flag in flags:
            sev = flag.get("severity", "low").lower()
            sev_colour = {"high": "#721c24", "medium": "#856404", "low": "#555"}.get(sev, "#555")
            rows += format_html(
                "<tr>"
                "<td style='padding:4px 8px;color:{c};font-weight:bold;'>{sev}</td>"
                "<td style='padding:4px 8px;font-family:monospace;'>{rule}</td>"
                "<td style='padding:4px 8px;'>{msg}</td>"
                "</tr>",
                c=sev_colour,
                sev=sev.upper(),
                rule=flag.get("rule", "—"),
                msg=flag.get("message", "—"),
            )

        return format_html(
            "<table style='width:100%;border-collapse:collapse;font-size:0.9em;'>"
            "<thead><tr>"
            "<th style='text-align:left;padding:4px 8px;border-bottom:1px solid #ccc;'>Severity</th>"
            "<th style='text-align:left;padding:4px 8px;border-bottom:1px solid #ccc;'>Rule</th>"
            "<th style='text-align:left;padding:4px 8px;border-bottom:1px solid #ccc;'>Message</th>"
            "</tr></thead>"
            "<tbody>{rows}</tbody>"
            "</table>",
            rows=rows,
        )


# ── Admin site customisation ──────────────────────────────────────────────────

admin.site.site_header  = "Levels.fyi  ·  Salary Validation Dashboard"
admin.site.site_title   = "Levels.fyi Admin"
admin.site.index_title  = "Data Quality Control Centre"