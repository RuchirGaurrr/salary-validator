"""
validation/serializers.py — JSON ↔ Python translation
A serializer does two things:
  1. Validates incoming JSON (did the user send all required fields?)
  2. Converts a Submission object → JSON for the API response

Think of it as a translator between the outside world (JSON) and Django (Python objects).
"""

from rest_framework import serializers
from .models import Submission


class SubmissionSerializer(serializers.ModelSerializer):
    """
    Used for:
    - Reading: GET /api/submissions/ → returns full submission data
    - Writing: POST /api/submissions/ → validates and saves incoming data
    """

    class Meta:
        model = Submission
        # '__all__' means include every field from the model
        fields = "__all__"
        # These fields are set by the server, not the client
        read_only_fields = [
            "id",
            "overall_score",
            "rule_score",
            "ai_score",
            "confidence_level",
            "passed",
            "flags",
            "created_at",
        ]


class SubmissionInputSerializer(serializers.Serializer):
    """
    Used ONLY for validating the incoming POST body.
    Stricter than SubmissionSerializer — we want to catch bad input early.
    """
    name = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    company = serializers.CharField(max_length=200)
    title = serializers.CharField(max_length=200)
    level = serializers.CharField(max_length=50)
    location = serializers.CharField(max_length=200)
    years_of_experience = serializers.IntegerField(min_value=0, max_value=60)
    base_salary = serializers.IntegerField(min_value=0)
    bonus = serializers.IntegerField(min_value=0, default=0)
    stock_rsu = serializers.IntegerField(min_value=0, default=0)
    total_compensation = serializers.IntegerField(min_value=0)
    ip_address = serializers.IPAddressField(required=False, allow_null=True, default=None)
    submitted_at = serializers.DateTimeField(required=False, allow_null=True, default=None)
    
    