from django.urls import path

from plane.app.views import (
    AccountEndpoint,
    ProfileEndpoint,
    UpdateUserOnBoardedEndpoint,
    UpdateUserTourCompletedEndpoint,
    UserActivityEndpoint,
    UserActivityGraphEndpoint,
    ## User
    UserEndpoint,
    UserIssueCompletedGraphEndpoint,
    UserWorkspaceDashboardEndpoint,
    UserSessionEndpoint,
    UserCreateEndpoint,
    ## End User
    ## Workspaces
    UserWorkSpacesEndpoint,
    # Zalo metadata
    UserWithZaloMetadataEndpoint,
    ZaloUserMetadataEndpoint,
    ZaloUserByZaloIdEndpoint,
)

urlpatterns = [
    # User Profile
    path(
        "users/me/",
        UserEndpoint.as_view({"get": "retrieve", "patch": "partial_update", "delete": "deactivate"}),
        name="users",
    ),
    path(
        "users/",
        UserCreateEndpoint.as_view(http_method_names=["post"]),
        name="user-create",
    ),
    path("users/session/", UserSessionEndpoint.as_view(), name="user-session"),
    path(
        "users/me/settings/",
        UserEndpoint.as_view({"get": "retrieve_user_settings"}),
        name="users",
    ),
    # Profile
    path("users/me/profile/", ProfileEndpoint.as_view(), name="accounts"),
    # End profile
    # Accounts
    path("users/me/accounts/", AccountEndpoint.as_view(), name="accounts"),
    path("users/me/accounts/<uuid:pk>/", AccountEndpoint.as_view(), name="accounts"),
    ## End Accounts
    path(
        "users/me/instance-admin/",
        UserEndpoint.as_view({"get": "retrieve_instance_admin"}),
        name="users",
    ),
    path("users/me/onboard/", UpdateUserOnBoardedEndpoint.as_view(), name="user-onboard"),
    path(
        "users/me/tour-completed/",
        UpdateUserTourCompletedEndpoint.as_view(),
        name="user-tour",
    ),
    path("users/me/activities/", UserActivityEndpoint.as_view(), name="user-activities"),
    # user workspaces
    path("users/me/workspaces/", UserWorkSpacesEndpoint.as_view(), name="user-workspace"),
    # User Graphs
    path(
        "users/me/workspaces/<str:slug>/activity-graph/",
        UserActivityGraphEndpoint.as_view(),
        name="user-activity-graph",
    ),
    path(
        "users/me/workspaces/<str:slug>/issues-completed-graph/",
        UserIssueCompletedGraphEndpoint.as_view(),
        name="completed-graph",
    ),
    path(
        "users/me/workspaces/<str:slug>/dashboard/",
        UserWorkspaceDashboardEndpoint.as_view(),
        name="user-workspace-dashboard",
    ),
    
    # Get user with zalo metadata
    path(
        "users/with-zalo/",
        UserWithZaloMetadataEndpoint.as_view(),
        name="user-with-zalo",
    ),
    path(
        "users/<uuid:user_id>/with-zalo/",
        UserWithZaloMetadataEndpoint.as_view(),
        name="user-with-zalo-by-id",
    ),
    path(
        "users/email/<str:email>/with-zalo/",
        UserWithZaloMetadataEndpoint.as_view(),
        name="user-with-zalo-by-email",
    ),
    
    # Zalo metadata endpoints for authenticated user
    path(
        "users/me/zalo-metadata/",
        ZaloUserMetadataEndpoint.as_view(),
        name="zalo-user-metadata",
    ),
    
    # Get user by Zalo ID
    path(
        "zalo-users/<str:zalo_user_id>/",
        ZaloUserByZaloIdEndpoint.as_view(),
        name="zalo-user-by-id",
    ),
    
    ## End User Graph
]
