import os
import json
from unittest.mock import patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

import httpx
from django.test import Client, TestCase, override_settings


class CompatibilityApiTests(TestCase):
    def test_health_is_local_and_does_not_require_legacy_api(self):
        response = Client().get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["service"], "django-compatibility-api")

    def test_native_repository_list_requires_authentication(self):
        response = Client().get("/api/repos")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Authentication required.")

    def test_native_repository_detail_rejects_invalid_token(self):
        response = Client().get(
            "/api/repos/00000000-0000-0000-0000-000000000000",
            HTTP_AUTHORIZATION="Bearer invalid-token",
        )

        self.assertEqual(response.status_code, 401)

    def test_native_registration_validates_payload_before_database_access(self):
        response = Client().post(
            "/api/auth/register",
            data="{}",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 422)

    def test_native_me_requires_authentication(self):
        response = Client().get("/api/auth/me")

        self.assertEqual(response.status_code, 401)

    def test_native_workspaces_requires_authentication(self):
        response = Client().get("/api/auth/workspaces")

        self.assertEqual(response.status_code, 401)

    def test_native_workspace_creation_validates_auth_before_database_access(self):
        response = Client().post(
            "/api/auth/workspaces",
            data=json.dumps({"name": "Platform"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)

    def test_native_invitation_and_member_routes_require_authentication(self):
        workspace_id = "00000000-0000-0000-0000-000000000000"
        invitation = Client().get(f"/api/auth/workspaces/{workspace_id}/invitations")
        members = Client().get(f"/api/auth/workspaces/{workspace_id}/members")

        self.assertEqual(invitation.status_code, 401)
        self.assertEqual(members.status_code, 401)

    def test_native_repository_connect_rejects_invalid_url_before_database_access(self):
        response = Client().post(
            "/api/repos/connect",
            data=json.dumps({"github_url": "https://example.com/project"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)

    def test_native_repository_read_routes_require_authentication(self):
        repo_id = "00000000-0000-0000-0000-000000000000"
        stats = Client().get(f"/api/repos/{repo_id}/stats")
        files = Client().get(f"/api/repos/{repo_id}/files")
        source = Client().get(f"/api/repos/{repo_id}/source/backend/app/main.py")

        self.assertEqual(stats.status_code, 401)
        self.assertEqual(files.status_code, 401)
        self.assertEqual(source.status_code, 401)

    def test_native_structural_routes_require_authentication(self):
        repo_id = "00000000-0000-0000-0000-000000000000"
        for suffix in ("graph/files", "architecture", "test-intelligence", "tour", "technical-debt", "documentation/quality"):
            response = Client().get(f"/api/repos/{repo_id}/{suffix}")
            self.assertEqual(response.status_code, 401)

    def test_native_history_routes_require_authentication(self):
        repo_id = "00000000-0000-0000-0000-000000000000"
        history = Client().get(f"/api/repos/{repo_id}/history")
        latest = Client().get(f"/api/repos/{repo_id}/pr-analysis/latest")
        compare = Client().post(f"/api/repos/{repo_id}/pr-analysis/compare", data="{}", content_type="application/json")

        self.assertEqual(history.status_code, 401)
        self.assertEqual(latest.status_code, 401)
        self.assertEqual(compare.status_code, 401)

    @override_settings(LEGACY_API_URL="https://legacy.example")
    @patch("api.views.httpx.request")
    def test_proxy_forwards_method_query_body_and_auth(self, request):
        request.return_value = httpx.Response(
            200,
            json={"ok": True},
            headers={"content-type": "application/json"},
        )

        response = Client().post(
            "/api/repos/123/query?mode=semantic",
            data=b'{"question":"where is auth?"}',
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer test-token",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})
        request.assert_called_once_with(
            method="POST",
            url="https://legacy.example/repos/123/query",
            params={"mode": "semantic"},
            content=b'{"question":"where is auth?"}',
            headers={
                "Authorization": "Bearer test-token",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    @patch("api.views.httpx.request", side_effect=httpx.TimeoutException("slow"))
    def test_proxy_returns_retryable_timeout_error(self, request):
        response = Client().get("/api/repos")

        self.assertEqual(response.status_code, 504)
        self.assertEqual(response.json()["detail"]["code"], "LEGACY_API_TIMEOUT")
        self.assertTrue(response.json()["detail"]["retryable"])

    @patch("api.views.httpx.request", side_effect=httpx.ConnectError("offline"))
    def test_proxy_returns_retryable_unavailable_error(self, request):
        response = Client().get("/api/repos")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["code"], "LEGACY_API_UNAVAILABLE")
        self.assertTrue(response.json()["detail"]["retryable"])
