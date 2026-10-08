"""ASGI boundary tests for request-size and rate-limit protections."""
import unittest
from importlib.util import find_spec
from unittest.mock import patch

FASTAPI_AVAILABLE = find_spec("fastapi") is not None
if FASTAPI_AVAILABLE:
    from app.main import SafetyMiddleware
    import app.main as main_module
else:  # pragma: no cover - exercised only in minimal local environments
    SafetyMiddleware = None
    main_module = None


class FakeRedis:
    def __init__(self, count=0, failure=None):
        self.count = count
        self.failure = failure
        self.expired = None
        self.closed = False

    async def incr(self, _key):
        if self.failure:
            raise self.failure
        self.count += 1
        return self.count

    async def expire(self, _key, seconds):
        self.expired = seconds

    async def aclose(self):
        self.closed = True


async def call_middleware(middleware, path, headers=None):
    messages = []

    async def receive():
        return {"type": "http.request", "body": b""}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "path": path,
        "headers": headers or [],
        "client": ("127.0.0.1", 1234),
    }
    await middleware(scope, receive, send)
    return messages


async def successful_app(_scope, _receive, send):
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})


@unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI is required for ASGI middleware tests")
class TestSafetyMiddleware(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_oversized_request_before_redis(self):
        middleware = SafetyMiddleware(successful_app)
        with patch.object(main_module.settings, "API_MAX_REQUEST_BYTES", 10):
            messages = await call_middleware(
                middleware,
                "/repos/connect",
                headers=[(b"content-length", b"11")],
            )
        self.assertEqual(messages[0]["status"], 413)

    async def test_expensive_route_uses_expensive_limit(self):
        client = FakeRedis(count=1)
        middleware = SafetyMiddleware(successful_app)
        with patch.object(main_module.redis, "from_url", return_value=client), patch.object(
            main_module.settings, "API_RATE_LIMIT_PER_MINUTE", 100
        ), patch.object(main_module.settings, "API_EXPENSIVE_RATE_LIMIT_PER_MINUTE", 1):
            messages = await call_middleware(middleware, "/repos/id/query")
        self.assertEqual(messages[0]["status"], 429)
        self.assertTrue(client.closed)

    async def test_normal_route_uses_general_limit(self):
        client = FakeRedis(count=1)
        middleware = SafetyMiddleware(successful_app)
        with patch.object(main_module.redis, "from_url", return_value=client), patch.object(
            main_module.settings, "API_RATE_LIMIT_PER_MINUTE", 1
        ), patch.object(main_module.settings, "API_EXPENSIVE_RATE_LIMIT_PER_MINUTE", 100):
            messages = await call_middleware(middleware, "/repos/id/history")
        self.assertEqual(messages[0]["status"], 429)

    async def test_redis_failure_fails_open_for_availability(self):
        client = FakeRedis(failure=RuntimeError("redis unavailable"))
        middleware = SafetyMiddleware(successful_app)
        with patch.object(main_module.redis, "from_url", return_value=client):
            messages = await call_middleware(middleware, "/repos/id/history")
        self.assertEqual(messages[0]["status"], 200)
        self.assertTrue(client.closed)


if __name__ == "__main__":
    unittest.main()
