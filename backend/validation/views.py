import datetime
from django.db.models import Avg, Count, Q
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Submission
# Standard SubmissionSerializer handles output formatting
# SubmissionInputSerializer handles user input validation boundaries
from .serializers import SubmissionSerializer, SubmissionInputSerializer

from .validator import RuleBasedValidator
from .ai_validator import AIValidator, get_combined_score


class SubmissionListCreateView(APIView):
    """
    Handles POST /api/submissions/ (Submit + Validate)
    Handles GET /api/submissions/  (List with query filtering)
    """

    def get(self, request):
        queryset = Submission.objects.all()

        # Query filter: ?filter=flagged
        filter_param = request.query_params.get("filter", None)
        if filter_param == "flagged":
            queryset = queryset.filter(Q(passed=False) | ~Q(flags=[]))

        serializer = SubmissionSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        # Explicit validation pass using SubmissionInputSerializer
        serializer = SubmissionInputSerializer(data=request.data)

        if serializer.is_valid():
            submission_data = serializer.validated_data

            # Instantiate processing layers
            rule_engine = RuleBasedValidator()
            ai_engine = AIValidator()

            # Fetch recent submissions from the last 10 minutes for IP velocity detection
            # This feeds Rule 1 (ip_velocity_spam) in validator.py
            ten_mins_ago = timezone.now() - datetime.timedelta(minutes=10)
            recent_submissions = list(
                Submission.objects.filter(
                    submitted_at__gte=ten_mins_ago
                ).values("ip_address", "submitted_at")
            )

            # Process parallel analytics engines
            rule_result = rule_engine.validate(submission_data, recent_submissions=recent_submissions)
            ai_result = ai_engine.validate(submission_data)

            rule_score = rule_result.get("score", 0)
            ai_score = ai_result.get("score", 0)

            # Combined scoring via get_combined_score (60% rule, 40% AI)
            final_score = get_combined_score(rule_score, ai_score)

            # Join flag data lists cleanly
            combined_flags = rule_result.get("flags", []) + ai_result.get("flags", [])

            # Dynamic assignment of confidence categorization metric
            if final_score >= 80:
                confidence = "high"
            elif final_score >= 50:
                confidence = "medium"
            else:
                confidence = "low"

            # Create entry directly inside model layer using custom values
            submission = Submission.objects.create(
                name=submission_data["name"],
                email=submission_data["email"],
                company=submission_data["company"],
                title=submission_data["title"],
                level=submission_data["level"],
                location=submission_data["location"],
                years_of_experience=submission_data["years_of_experience"],
                base_salary=submission_data["base_salary"],
                bonus=submission_data.get("bonus", 0),
                stock_rsu=submission_data.get("stock_rsu", 0),
                total_compensation=submission_data["total_compensation"],
                ip_address=self.get_client_ip(request),
                submitted_at=submission_data.get("submitted_at"),
                rule_score=rule_score,
                ai_score=ai_score,
                overall_score=final_score,
                confidence_level=confidence,
                passed=True if final_score >= 60 else False,
                flags=combined_flags,
            )

            return Response(
                SubmissionSerializer(submission).data,
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


class BatchSubmissionView(APIView):
    """
    Handles POST /api/submissions/batch/
    Expects Body Format: {"submissions": [ {...}, {...} ]}
    """

    def post(self, request):
        submissions_data = request.data.get("submissions", [])
        if not isinstance(submissions_data, list):
            return Response(
                {"error": "Expected a dict wrapper containing a 'submissions' list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        results = []
        rule_engine = RuleBasedValidator()
        ai_engine = AIValidator()

        # Fetch recent submissions once for the entire batch
        ten_mins_ago = timezone.now() - datetime.timedelta(minutes=10)
        recent_submissions = list(
            Submission.objects.filter(
                submitted_at__gte=ten_mins_ago
            ).values("ip_address", "submitted_at")
        )

        for item in submissions_data:
            serializer = SubmissionInputSerializer(data=item)
            if serializer.is_valid():
                sub_data = serializer.validated_data
                r_res = rule_engine.validate(sub_data, recent_submissions=recent_submissions)
                a_res = ai_engine.validate(sub_data)

                r_score = r_res.get("score", 0)
                a_score = a_res.get("score", 0)

                # Combined scoring via get_combined_score (60% rule, 40% AI)
                f_score = get_combined_score(r_score, a_score)

                submission = Submission.objects.create(
                    name=sub_data["name"],
                    email=sub_data["email"],
                    company=sub_data["company"],
                    title=sub_data["title"],
                    level=sub_data["level"],
                    location=sub_data["location"],
                    years_of_experience=sub_data["years_of_experience"],
                    base_salary=sub_data["base_salary"],
                    bonus=sub_data.get("bonus", 0),
                    stock_rsu=sub_data.get("stock_rsu", 0),
                    total_compensation=sub_data["total_compensation"],
                    submitted_at=sub_data.get("submitted_at"),
                    rule_score=r_score,
                    ai_score=a_score,
                    overall_score=f_score,
                    confidence_level="high" if f_score >= 80 else "medium" if f_score >= 50 else "low",
                    passed=True if f_score >= 60 else False,
                    flags=r_res.get("flags", []) + a_res.get("flags", []),
                )
                results.append(SubmissionSerializer(submission).data)
            else:
                results.append({"error": serializer.errors, "raw_data": item})

        return Response({"results": results}, status=status.HTTP_201_CREATED)


class DashboardStatsView(APIView):
    """
    Handles GET /api/dashboard/stats/
    """

    def get(self, request):
        stats = Submission.objects.aggregate(
            total=Count("id"),
            passed_count=Count("id", filter=Q(passed=True)),
            flagged_count=Count("id", filter=Q(passed=False)),
            avg_score=Avg("overall_score"),
        )

        all_submissions = Submission.objects.all()
        high_severity_count = 0
        for sub in all_submissions:
            for flag in sub.flags:
                if isinstance(flag, dict) and flag.get("severity") == "high":
                    high_severity_count += 1

        return Response(
            {
                "total_submissions": stats["total"] or 0,
                "passed": stats["passed_count"] or 0,
                "flagged": stats["flagged_count"] or 0,
                "average_score": round(stats["avg_score"], 1) if stats["avg_score"] else 0.0,
                "high_severity_flags": high_severity_count,
            }
        )