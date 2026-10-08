"""Classify API paths for best-effort request throttling."""


EXPENSIVE_PATH_SUFFIXES = (
    "/query",
    "/evaluate",
    "/documentation/generate-preview",
    "/security/secrets/scan",
    "/issues",
)


def rate_limit_for_path(path: str, default_limit: int, expensive_limit: int, auth_limit: int | None = None) -> tuple[int, str]:
    """Return the per-minute limit and bucket for a request path."""
    if auth_limit is not None and path.startswith("/auth/"):
        return auth_limit, "auth"
    if any(path.endswith(suffix) or f"{suffix}/" in path for suffix in EXPENSIVE_PATH_SUFFIXES):
        return expensive_limit, "expensive"
    return default_limit, "default"
