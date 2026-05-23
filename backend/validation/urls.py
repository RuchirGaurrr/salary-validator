"""
urls.py — App-level URL routes
Maps URLs to the view classes in views.py
"""

from django.urls import path
from .views import SubmissionListCreateView, BatchSubmissionView, DashboardStatsView

urlpatterns = [
    # POST to submit one entry, GET to list all
    path("submissions/", SubmissionListCreateView.as_view(), name="submissions"),

    # POST to submit multiple entries at once
    path("submissions/batch/", BatchSubmissionView.as_view(), name="batch-submissions"),

    # GET dashboard summary stats
    path("dashboard/stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
]
