# Django imports
from rest_framework import serializers

# Module imports
from plane.db.models import IssueDailyProgress


class IssueDailyProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = IssueDailyProgress
        fields = [
            "id",
            "issue",
            "day",
            "daily_tasks",
            "notes",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        # Get user from context first (passed explicitly from view)
        user = self.context.get("user")
        
        # If no user in context or user is anonymous, fall back to request.user
        if not user or not hasattr(user, 'pk') or user.pk is None:
            user = self.context["request"].user
        
        # If still no valid user, set to None (allowed now)
        if not user or not user.is_authenticated:
            user = None
            
        # Use objects.create() to bypass BaseModel.save()
        instance = IssueDailyProgress.objects.create(
            issue=validated_data.get('issue'),
            day=validated_data.get('day'),
            daily_tasks=validated_data.get('daily_tasks', {}),
            notes=validated_data.get('notes', ''),
            created_by=user,
            updated_by=user
        )
        return instance

    def update(self, instance, validated_data):
        # Get user from context first (passed explicitly from view)
        user = self.context.get("user")
        
        # If no user in context or user is anonymous, fall back to request.user  
        if not user or not hasattr(user, 'pk') or user.pk is None:
            user = self.context["request"].user
            
        # If still no valid user, set to None
        if not user or not user.is_authenticated:
            user = None
            
        # Update fields
        instance.day = validated_data.get('day', instance.day)
        instance.daily_tasks = validated_data.get('daily_tasks', instance.daily_tasks)
        instance.notes = validated_data.get('notes', instance.notes)
        instance.updated_by = user
        instance.save()
        return instance


class IssueDailyProgressDetailSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.display_name", read_only=True)
    updated_by_name = serializers.CharField(source="updated_by.display_name", read_only=True)
    issue_name = serializers.CharField(source="issue.name", read_only=True)
    issue_sequence_id = serializers.IntegerField(source="issue.sequence_id", read_only=True)

    class Meta:
        model = IssueDailyProgress
        fields = [
            "id",
            "issue",
            "issue_name",
            "issue_sequence_id",
            "day",
            "daily_tasks",
            "notes",
            "created_by",
            "created_by_name",
            "updated_by",
            "updated_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
