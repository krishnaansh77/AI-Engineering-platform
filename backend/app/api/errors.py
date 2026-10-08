"""Consistent API error payloads for frontend retry and messaging behavior."""


def error_detail(code: str, message: str, retryable: bool = False) -> dict:
    return {"error": {"code": code, "message": message, "retryable": retryable}}
