# Python imports
from datetime import datetime

# Django imports
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

# Module imports
from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers import (
    IssueDailyProgressSerializer,
    IssueDailyProgressDetailSerializer,
)
from plane.db.models import IssueDailyProgress, Issue, ProjectMember
from plane.app.views import BaseAPIView


class IssueDailyProgressEndpoint(BaseAPIView):
    """
    API endpoint to manage daily progress for issues
    """
    permission_classes = [AllowAny]
    
    def get_permissions(self):
        """Override to allow anonymous access for GET requests"""
        if self.request.method == 'GET':
            return [AllowAny()]
        return super().get_permissions()
    
    def get(self, request, slug, project_id, issue_id):
        """
        Get daily progress entries for an issue
        Query params:
        - day: specific date (YYYY-MM-DD)
        - start_date: filter from this date
        - end_date: filter to this date
        """
        # Verify issue exists and user has access
        issue = Issue.issue_objects.filter(
            workspace__slug=slug,
            project_id=project_id,
            pk=issue_id
        ).first()

        if not issue:
            return Response(
                {"error": "Issue not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Skip permission check for unauthenticated users
        if request.user.is_authenticated:
            # Check guest permissions only for authenticated users
            project_member = ProjectMember.objects.filter(
                workspace__slug=slug,
                project_id=project_id,
                member=request.user,
                role=5,
                is_active=True,
            ).first()

            if project_member and not issue.project.guest_view_all_features:
                if issue.created_by != request.user:
                    return Response(
                        {"error": "You are not allowed to view this issue's progress"},
                        status=status.HTTP_403_FORBIDDEN,
                    )

        # Build query
        queryset = IssueDailyProgress.objects.filter(
            issue_id=issue_id
        ).select_related("created_by", "updated_by", "issue")

        # Filter by specific day
        day = request.GET.get("day")
        if day:
            try:
                day_date = datetime.strptime(day, "%Y-%m-%d").date()
                queryset = queryset.filter(day=day_date)
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Filter by date range
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

        if start_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                queryset = queryset.filter(day__gte=start)
            except ValueError:
                return Response(
                    {"error": "Invalid start_date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        if end_date:
            try:
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
                queryset = queryset.filter(day__lte=end)
            except ValueError:
                return Response(
                    {"error": "Invalid end_date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Filter by created_by if specified
        created_by = request.GET.get("created_by")
        if created_by:
            queryset = queryset.filter(created_by_id=created_by)

        # Order by day descending
        queryset = queryset.order_by("-day", "-created_at")

        serializer = IssueDailyProgressDetailSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def post(self, request, slug, project_id, issue_id):
        """
        Create or update daily progress for an issue
        """
        # Verify issue exists and user has access
        issue = Issue.issue_objects.filter(
            workspace__slug=slug,
            project_id=project_id,
            pk=issue_id
        ).first()

        if not issue:
            return Response(
                {"error": "Issue not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Validate day field
        day = request.data.get("day")
        if not day:
            return Response(
                {"error": "Day field is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            day_date = datetime.strptime(day, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Handle unauthenticated requests - use issue creator as fallback
        user = request.user if request.user.is_authenticated else issue.created_by
        
        # Check if entry already exists for this user, issue, and day
        existing_progress = IssueDailyProgress.objects.filter(
            issue_id=issue_id,
            day=day_date,
            created_by=user
        ).first()

        if existing_progress:
            # Update existing entry
            serializer = IssueDailyProgressSerializer(
                existing_progress,
                data=request.data,
                partial=True,
                context={"request": request, "user": user}
            )
        else:
            # Create new entry
            data = request.data.copy()
            data["issue"] = issue_id
            serializer = IssueDailyProgressSerializer(
                data=data,
                context={"request": request, "user": user}
            )

        if serializer.is_valid():
            try:
                print("About to save...")
                saved_instance = serializer.save()
                print(f"Saved successfully. ID: {saved_instance.id}")
                
                # Return detailed response
                progress = IssueDailyProgress.objects.filter(
                    pk=saved_instance.id
                ).select_related("created_by", "updated_by", "issue").first()
                
                print(f"Fetched progress: {progress}")
                
                detail_serializer = IssueDailyProgressDetailSerializer(progress)
                print(f"Detail serializer data: {detail_serializer.data}")
                
                return Response(
                    detail_serializer.data,
                    status=status.HTTP_201_CREATED if not existing_progress else status.HTTP_200_OK
                )
            except Exception as e:
                print(f"Error during save/response: {e}")
                import traceback
                traceback.print_exc()
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        print("Validation errors:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # @allow_permission([ROLE.ADMIN, ROLE.MEMBER], creator=True, model=IssueDailyProgress)
    def delete(self, request, slug, project_id, issue_id, progress_id):
        """
        Delete a specific daily progress entry
        """
        progress = IssueDailyProgress.objects.filter(
            id=progress_id,
            issue_id=issue_id,
            issue__project_id=project_id,
            issue__workspace__slug=slug
        ).first()

        if not progress:
            return Response(
                {"error": "Daily progress entry not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        progress.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class IssueDailyProgressDetailEndpoint(BaseAPIView):
    """
    API endpoint to get/update/delete a specific daily progress entry
    """
    permission_classes = [AllowAny]
    # @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def get(self, request, slug, project_id, issue_id, progress_id):
        """
        Get a specific daily progress entry
        """
        progress = IssueDailyProgress.objects.filter(
            id=progress_id,
            issue_id=issue_id,
            issue__project_id=project_id,
            issue__workspace__slug=slug
        ).select_related("created_by", "updated_by", "issue").first()

        if not progress:
            return Response(
                {"error": "Daily progress entry not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = IssueDailyProgressDetailSerializer(progress)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # @allow_permission([ROLE.ADMIN, ROLE.MEMBER], creator=True, model=IssueDailyProgress)
    def patch(self, request, slug, project_id, issue_id, progress_id):
        """
        Update a specific daily progress entry
        """
        progress = IssueDailyProgress.objects.filter(
            id=progress_id,
            issue_id=issue_id,
            issue__project_id=project_id,
            issue__workspace__slug=slug
        ).first()

        if not progress:
            return Response(
                {"error": "Daily progress entry not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = IssueDailyProgressSerializer(
            progress,
            data=request.data,
            partial=True,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            
            # Return detailed response
            progress.refresh_from_db()
            detail_serializer = IssueDailyProgressDetailSerializer(progress)
            return Response(detail_serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # @allow_permission([ROLE.ADMIN, ROLE.MEMBER], creator=True, model=IssueDailyProgress)
    def delete(self, request, slug, project_id, issue_id, progress_id):
        """
        Delete a specific daily progress entry
        """
        progress = IssueDailyProgress.objects.filter(
            id=progress_id,
            issue_id=issue_id,
            issue__project_id=project_id,
            issue__workspace__slug=slug
        ).first()

        if not progress:
            return Response(
                {"error": "Daily progress entry not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        progress.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
