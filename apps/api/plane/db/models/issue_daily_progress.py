# Python imports
import uuid

# Django imports
from django.db import models
from django.conf import settings

# Module imports
from .base import BaseModel
from .issue import Issue


class IssueDailyProgress(BaseModel):
    """
    Model to track daily progress and tasks for issues
    """
    id = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False, db_index=True, primary_key=True
    )
    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name="daily_progress"
    )
    day = models.DateField(
        help_text="The date for this daily progress entry"
    )
    daily_tasks = models.JSONField(
        default=dict,
        help_text="JSON field containing daily tasks and progress information"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes for the day"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_daily_progress",
        null=True,
        blank=True
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="updated_daily_progress",
        null=True,
        blank=True
    )

    class Meta:
        unique_together = [['issue', 'day', 'created_by']]
        verbose_name = "Issue Daily Progress"
        verbose_name_plural = "Issue Daily Progress"
        db_table = "issue_daily_progress"
        ordering = ["-day", "-created_at"]

    def __str__(self):
        return f"{self.issue.name} - {self.day}"
