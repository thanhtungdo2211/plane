import uuid
from django.db import models
from plane.db.mixins import TimeAuditModel


class ZaloUserMetadata(TimeAuditModel):
    id = models.UUIDField(
        default=uuid.uuid4, 
        unique=True, 
        editable=False, 
        db_index=True, 
        primary_key=True
    )
    user = models.OneToOneField(
        "db.User", 
        on_delete=models.CASCADE, 
        related_name="zalo_metadata"
    )
    name = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    cv = models.CharField(max_length=500, null=True, blank=True)  # File path
    cv_data = models.JSONField(null=True, blank=True)  # Extracted CV data
    zalo_user_id = models.CharField(
        max_length=255, 
        unique=True, 
        null=True, 
        blank=True, 
        db_index=True
    )
    description = models.TextField(null=True, blank=True)
    additional_info = models.JSONField(null=True, blank=True, default=dict)
    skills = models.JSONField(null=True, blank=True, default=list)
    role = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        verbose_name = "Zalo User Metadata"
        verbose_name_plural = "Zalo User Metadata"
        db_table = "zalo_user_metadata"
        ordering = ("-created_at",)

    def __str__(self):
        return f"Zalo metadata for {self.user.email}"