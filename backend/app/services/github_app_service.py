"""GitHub App authentication for installation-scoped repository access."""
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from jose import jwt


class GitHubAppService:
    """Mint short-lived installation tokens without exposing app credentials."""

    def __init__(self, app_id: str, private_key: str, installation_id: str):
        self.app_id = app_id.strip()
        self.private_key = private_key.replace("\\n", "\n").strip()
        self.installation_id = installation_id.strip()

    @property
    def configured(self) -> bool:
        return bool(self.app_id and self.private_key and self.installation_id)

    def app_jwt(self) -> str:
        if not self.configured:
            raise ValueError("GitHub App credentials are not configured.")
        now = datetime.now(timezone.utc)
        claims = {"iat": int(now.timestamp()) - 30, "exp": int((now + timedelta(minutes=9)).timestamp()), "iss": self.app_id}
        return jwt.encode(claims, self.private_key, algorithm="RS256")

    async def installation_token(self) -> str:
        url = f"https://api.github.com/app/installations/{self.installation_id}/access_tokens"
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {self.app_jwt()}", "X-GitHub-Api-Version": "2022-11-28"})
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        access_token = payload.get("token")
        if not access_token:
            raise RuntimeError("GitHub App token response did not include an access token.")
        return str(access_token)
