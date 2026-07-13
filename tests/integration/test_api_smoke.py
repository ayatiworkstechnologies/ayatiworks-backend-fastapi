"""
Route-wide API smoke tests.

These tests exercise every registered `/api/v1` route with minimal requests and
assert that the app does not return server errors (5xx) for malformed/unauthenticated
inputs. This gives broad endpoint health coverage without requiring full fixture data.
"""

import re

from app.main import app

ALLOWED_STATUS_CODES = {
    200,
    201,
    202,
    204,
    301,
    302,
    307,
    308,
    400,
    401,
    403,
    404,
    405,
    409,
    415,
    422,
    429,
}


def _iter_api_routes():
    for route in app.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", set())
        if not path.startswith("/api/v1"):
            continue
        for method in methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            yield method, path


def _build_test_path(path: str) -> str:
    # Replace all `{param}` placeholders with a safe test token.
    return re.sub(r"{[^}]+}", "1", path)


def _request(client, method: str, path: str):
    if method in {"POST", "PUT", "PATCH"}:
        return client.request(method, path, json={})
    return client.request(method, path)


def test_all_api_routes_do_not_5xx(client):
    failures = []

    for method, route_path in _iter_api_routes():
        test_path = _build_test_path(route_path)
        response = _request(client, method, test_path)
        code = response.status_code
        if code not in ALLOWED_STATUS_CODES:
            failures.append(f"{method} {route_path} -> {code}")

    assert not failures, "Unexpected API responses:\n" + "\n".join(failures)

