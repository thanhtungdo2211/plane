from rest_framework import serializers
from plane.db.models import ZaloUserMetadata


class ZaloUserMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ZaloUserMetadata
        fields = [
            "id",
            "user",
            "name",
            "phone",
            "cv",
            "cv_data",
            "zalo_user_id",
            "description",
            "additional_info",
            "skills",
            "role",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]