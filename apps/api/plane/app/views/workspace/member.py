# Django imports
from django.db.models import Count, Q, OuterRef, Subquery, IntegerField
from django.utils import timezone
from django.db.models.functions import Coalesce

# Third party modules
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from plane.app.permissions import WorkspaceEntityPermission, allow_permission, ROLE

# Module imports
from plane.app.serializers import (
    ProjectMemberRoleSerializer,
    WorkspaceMemberAdminSerializer,
    WorkspaceMemberMeSerializer,
    WorkSpaceMemberSerializer,
)
from plane.app.views.base import BaseAPIView
from plane.db.models import Project, ProjectMember, WorkspaceMember, DraftIssue, User, Workspace
from plane.utils.cache import invalidate_cache

from .. import BaseViewSet


class WorkSpaceMemberViewSet(BaseViewSet):
    serializer_class = WorkspaceMemberAdminSerializer
    model = WorkspaceMember

    search_fields = ["member__display_name", "member__first_name"]
    use_read_replica = True

    def get_queryset(self):
        return self.filter_queryset(
            super()
            .get_queryset()
            .filter(workspace__slug=self.kwargs.get("slug"))
            .select_related("member", "member__avatar_asset")
        )

    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="WORKSPACE")
    def list(self, request, slug):
        workspace_member = WorkspaceMember.objects.get(member=request.user, workspace__slug=slug, is_active=True)

        # Get all active workspace members
        workspace_members = self.get_queryset()
        if workspace_member.role > 5:
            serializer = WorkspaceMemberAdminSerializer(workspace_members, fields=("id", "member", "role"), many=True)
        else:
            serializer = WorkSpaceMemberSerializer(workspace_members, fields=("id", "member", "role"), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="WORKSPACE")
    def partial_update(self, request, slug, pk):
        workspace_member = WorkspaceMember.objects.get(
            pk=pk, workspace__slug=slug, member__is_bot=False, is_active=True
        )
        if request.user.id == workspace_member.member_id:
            return Response(
                {"error": "You cannot update your own role"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # If a user is moved to a guest role he can't have any other role in projects
        if "role" in request.data and int(request.data.get("role")) == 5:
            ProjectMember.objects.filter(workspace__slug=slug, member_id=workspace_member.member_id).update(role=5)

        serializer = WorkSpaceMemberSerializer(workspace_member, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="WORKSPACE")
    def destroy(self, request, slug, pk):
        # Check the user role who is deleting the user
        workspace_member = WorkspaceMember.objects.get(
            workspace__slug=slug, pk=pk, member__is_bot=False, is_active=True
        )

        # check requesting user role
        requesting_workspace_member = WorkspaceMember.objects.get(
            workspace__slug=slug, member=request.user, is_active=True
        )

        if str(workspace_member.id) == str(requesting_workspace_member.id):
            return Response(
                {"error": "You cannot remove yourself from the workspace. Please use leave workspace"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if requesting_workspace_member.role < workspace_member.role:
            return Response(
                {"error": "You cannot remove a user having role higher than you"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            Project.objects.annotate(
                total_members=Count("project_projectmember"),
                member_with_role=Count(
                    "project_projectmember",
                    filter=Q(
                        project_projectmember__member_id=workspace_member.id,
                        project_projectmember__role=20,
                    ),
                ),
            )
            .filter(total_members=1, member_with_role=1, workspace__slug=slug)
            .exists()
        ):
            return Response(
                {
                    "error": "User is a part of some projects where they are the only admin, they should either leave that project or promote another user to admin."  # noqa: E501
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Deactivate the users from the projects where the user is part of
        _ = ProjectMember.objects.filter(
            workspace__slug=slug, member_id=workspace_member.member_id, is_active=True
        ).update(is_active=False, updated_at=timezone.now())

        workspace_member.is_active = False
        workspace_member.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @invalidate_cache(
        path="/api/workspaces/:slug/members/",
        url_params=True,
        user=False,
        multiple=True,
    )
    @invalidate_cache(path="/api/users/me/settings/")
    @invalidate_cache(path="api/users/me/workspaces/", user=False, multiple=True)
    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="WORKSPACE")
    def leave(self, request, slug):
        workspace_member = WorkspaceMember.objects.get(workspace__slug=slug, member=request.user, is_active=True)

        # Check if the leaving user is the only admin of the workspace
        if (
            workspace_member.role == 20
            and not WorkspaceMember.objects.filter(workspace__slug=slug, role=20, is_active=True).count() > 1
        ):
            return Response(
                {
                    "error": "You cannot leave the workspace as you are the only admin of the workspace you will have to either delete the workspace or promote another user to admin."  # noqa: E501
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            Project.objects.annotate(
                total_members=Count("project_projectmember"),
                member_with_role=Count(
                    "project_projectmember",
                    filter=Q(
                        project_projectmember__member_id=request.user.id,
                        project_projectmember__role=20,
                    ),
                ),
            )
            .filter(total_members=1, member_with_role=1, workspace__slug=slug)
            .exists()
        ):
            return Response(
                {
                    "error": "You are a part of some projects where you are the only admin, you should either leave the project or promote another user to admin."  # noqa: E501
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # # Deactivate the users from the projects where the user is part of
        _ = ProjectMember.objects.filter(
            workspace__slug=slug, member_id=workspace_member.member_id, is_active=True
        ).update(is_active=False, updated_at=timezone.now())

        # # Deactivate the user
        workspace_member.is_active = False
        workspace_member.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkspaceMemberUserViewsEndpoint(BaseAPIView):
    def post(self, request, slug):
        workspace_member = WorkspaceMember.objects.get(workspace__slug=slug, member=request.user, is_active=True)
        workspace_member.view_props = request.data.get("view_props", {})
        workspace_member.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

class WorkspaceAddMemberEndpoint(BaseAPIView):
    """
    Endpoint to add member directly to workspace using API key authentication
    Bypass normal invitation flow
    """
    permission_classes = [AllowAny]  # Allow API key auth without user context
    
    def post(self, request, slug):
        """
        Add a user directly to workspace without invitation
        
        Request body:
        - user_id or email (required) - User ID or email to add
        - role (optional) - Member role (default: 15 - Member)
          Roles: 5=Guest, 10=Viewer, 15=Member, 20=Admin
        """
        # Get workspace
        try:
            workspace = Workspace.objects.get(slug=slug)
        except Workspace.DoesNotExist:
            return Response(
                {"error": "Workspace not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get user by ID or email
        user_id = request.data.get('user_id')
        email = request.data.get('email')
        role = request.data.get('role', 15)  # Default role is Member (15)
        
        if not user_id and not email:
            return Response(
                {"error": "Either user_id or email is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find user
        try:
            if user_id:
                user = User.objects.get(id=user_id, is_active=True)
            else:
                user = User.objects.get(email=email.lower().strip(), is_active=True)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if user is already a member
        existing_member = WorkspaceMember.objects.filter(
            workspace=workspace, 
            member=user
        ).first()
        
        if existing_member and existing_member.is_active:
            return Response(
                {
                    "error": "User is already a member of this workspace",
                    "member": {
                        "id": str(existing_member.id),
                        "role": existing_member.role,
                        "email": user.email
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate role
        valid_roles = [5, 10, 15, 20]  # Guest, Viewer, Member, Admin
        if role not in valid_roles:
            return Response(
                {"error": f"Invalid role. Valid roles are: {valid_roles}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reactivate or create workspace member
        if existing_member:
            # Reactivate existing member
            existing_member.is_active = True
            existing_member.role = role
            existing_member.save()
            workspace_member = existing_member
        else:
            # Create new workspace member
            workspace_member = WorkspaceMember.objects.create(
                workspace=workspace,
                member=user,
                role=role,
                is_active=True
            )
        
        serializer = WorkspaceMemberAdminSerializer(workspace_member)
        return Response(
            {
                "message": "User added to workspace successfully",
                "member": serializer.data
            }, 
            status=status.HTTP_201_CREATED
        )

class WorkspaceRemoveMemberEndpoint(BaseAPIView):
    """
    Remove member from workspace using API key authentication
    """
    permission_classes = [AllowAny]
    
    def delete(self, request, slug, member_id):
        """
        Remove a member from workspace
        
        URL params:
        - member_id: UUID of the USER (not WorkspaceMember) to remove
        
        Or use query param:
        - ?email=user@example.com
        """
        try:
            workspace = Workspace.objects.get(slug=slug)
        except Workspace.DoesNotExist:
            return Response(
                {"error": "Workspace not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get user by ID or email
        email = request.query_params.get('email')
        
        try:
            if email:
                user = User.objects.get(email=email.lower().strip(), is_active=True)
            else:
                # member_id is the User ID
                user = User.objects.get(id=member_id, is_active=True)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get workspace member by user
        try:
            workspace_member = WorkspaceMember.objects.get(
                member=user,  # ← Tìm theo User object
                workspace=workspace,
                member__is_bot=False,
                is_active=True
            )
        except WorkspaceMember.DoesNotExist:
            return Response(
                {"error": "User is not a member of this workspace"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if user is the only admin
        if workspace_member.role == 20:
            admin_count = WorkspaceMember.objects.filter(
                workspace=workspace,
                role=20,
                is_active=True
            ).count()
            
            if admin_count <= 1:
                return Response(
                    {"error": "Cannot remove the only admin of the workspace"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Check if user is the only admin in some projects
        if (
            Project.objects.annotate(
                total_members=Count("project_projectmember"),
                member_with_role=Count(
                    "project_projectmember",
                    filter=Q(
                        project_projectmember__member_id=user.id,  # ← Dùng user.id
                        project_projectmember__role=20,
                    ),
                ),
            )
            .filter(total_members=1, member_with_role=1, workspace=workspace)
            .exists()
        ):
            return Response(
                {
                    "error": "User is the only admin in some projects. Promote another user to admin first."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Deactivate from all projects in workspace
        ProjectMember.objects.filter(
            workspace=workspace,
            member_id=user.id,  # ← Dùng user.id
            is_active=True
        ).update(is_active=False, updated_at=timezone.now())
        
        # Deactivate from workspace
        workspace_member.is_active = False
        workspace_member.save()
        
        return Response(
            {"message": "Member removed from workspace successfully"},
            status=status.HTTP_200_OK
        )

class WorkspaceMemberUserEndpoint(BaseAPIView):
    use_read_replica = True

    def get(self, request, slug):
        draft_issue_count = (
            DraftIssue.objects.filter(created_by=request.user, workspace_id=OuterRef("workspace_id"))
            .values("workspace_id")
            .annotate(count=Count("id"))
            .values("count")
        )

        workspace_member = (
            WorkspaceMember.objects.filter(member=request.user, workspace__slug=slug, is_active=True)
            .annotate(draft_issue_count=Coalesce(Subquery(draft_issue_count, output_field=IntegerField()), 0))
            .first()
        )
        serializer = WorkspaceMemberMeSerializer(workspace_member)
        return Response(serializer.data, status=status.HTTP_200_OK)


class WorkspaceProjectMemberEndpoint(BaseAPIView):
    serializer_class = ProjectMemberRoleSerializer
    model = ProjectMember

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        # Fetch all project IDs where the user is involved
        project_ids = (
            ProjectMember.objects.filter(member=request.user, is_active=True)
            .values_list("project_id", flat=True)
            .distinct()
        )

        # Get all the project members in which the user is involved
        project_members = ProjectMember.objects.filter(
            workspace__slug=slug, project_id__in=project_ids, is_active=True
        ).select_related("project", "member", "workspace")
        project_members = ProjectMemberRoleSerializer(project_members, many=True).data

        project_members_dict = dict()

        # Construct a dictionary with project_id as key and project_members as value
        for project_member in project_members:
            project_id = project_member.pop("project")
            if str(project_id) not in project_members_dict:
                project_members_dict[str(project_id)] = []
            project_members_dict[str(project_id)].append(project_member)

        return Response(project_members_dict, status=status.HTTP_200_OK)

class ProjectAddMemberEndpoint(BaseAPIView):
    """
    Endpoint to add member directly to project using API key authentication
    Bypass normal invitation flow
    """
    permission_classes = [AllowAny]
    
    def post(self, request, slug, project_id):
        """
        Add a user directly to project without invitation
        
        Request body:
        - user_id or email (required) - User ID or email to add
        - role (optional) - Member role (default: 15 - Member)
          Roles: 5=Guest, 10=Viewer, 15=Member, 20=Admin
        """
        # Get workspace and project
        try:
            workspace = Workspace.objects.get(slug=slug)
            project = Project.objects.get(id=project_id, workspace=workspace)
        except Workspace.DoesNotExist:
            return Response(
                {"error": "Workspace not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Project.DoesNotExist:
            return Response(
                {"error": "Project not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get user by ID or email
        user_id = request.data.get('user_id')
        email = request.data.get('email')
        role = request.data.get('role', 15)
        
        if not user_id and not email:
            return Response(
                {"error": "Either user_id or email is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find user
        try:
            if user_id:
                user = User.objects.get(id=user_id, is_active=True)
            else:
                user = User.objects.get(email=email.lower().strip(), is_active=True)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if user is a workspace member
        workspace_member = WorkspaceMember.objects.filter(
            workspace=workspace,
            member=user,
            is_active=True
        ).first()
        
        if not workspace_member:
            return Response(
                {"error": "User is not a member of this workspace. Add them to workspace first."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already a project member
        existing_member = ProjectMember.objects.filter(
            project=project,
            member=user
        ).first()
        
        if existing_member and existing_member.is_active:
            return Response(
                {
                    "error": "User is already a member of this project",
                    "member": {
                        "id": str(existing_member.id),
                        "role": existing_member.role,
                        "email": user.email
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate role
        valid_roles = [5, 10, 15, 20]
        if role not in valid_roles:
            return Response(
                {"error": f"Invalid role. Valid roles are: {valid_roles}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Workspace guest can only be project guest
        if workspace_member.role == 5 and role > 5:
            return Response(
                {"error": "Workspace guest can only have guest role in projects"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reactivate or create project member
        if existing_member:
            existing_member.is_active = True
            existing_member.role = role
            existing_member.save()
            project_member = existing_member
        else:
            project_member = ProjectMember.objects.create(
                project=project,
                member=user,
                workspace=workspace,
                role=role,
                is_active=True
            )
        
        from plane.app.serializers import ProjectMemberAdminSerializer
        serializer = ProjectMemberAdminSerializer(project_member)
        
        return Response(
            {
                "message": "User added to project successfully",
                "member": serializer.data
            },
            status=status.HTTP_201_CREATED
        )

class ProjectRemoveMemberEndpoint(BaseAPIView):
    """
    Remove member from project using API key authentication
    """
    permission_classes = [AllowAny]
    
    def delete(self, request, slug, project_id, member_id):
        """
        Remove a member from project
        
        URL params:
        - member_id: UUID of the USER (not ProjectMember) to remove
        
        Or use query param:
        - ?email=user@example.com
        """
        try:
            workspace = Workspace.objects.get(slug=slug)
            project = Project.objects.get(id=project_id, workspace=workspace)
        except Workspace.DoesNotExist:
            return Response(
                {"error": "Workspace not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Project.DoesNotExist:
            return Response(
                {"error": "Project not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get user by ID or email (from query params)
        email = request.query_params.get('email')
        
        # Find user
        try:
            if email:
                user = User.objects.get(email=email.lower().strip(), is_active=True)
            else:
                # member_id is the User ID
                user = User.objects.get(id=member_id, is_active=True)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get project member by user
        try:
            project_member = ProjectMember.objects.get(
                member=user,  # ← Tìm theo User object
                project=project,
                is_active=True
            )
        except ProjectMember.DoesNotExist:
            return Response(
                {"error": "User is not a member of this project"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if user is the only admin
        if project_member.role == 20:
            admin_count = ProjectMember.objects.filter(
                project=project,
                role=20,
                is_active=True
            ).count()
            
            if admin_count <= 1:
                return Response(
                    {"error": "Cannot remove the only admin of the project"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Deactivate project member
        project_member.is_active = False
        project_member.save()
        
        return Response(
            {"message": "Member removed from project successfully"},
            status=status.HTTP_200_OK
        )