# SPDX-License-Identifier: AGPL-3.0-only
"""Small HTTP client helpers shared by the activity-viewer tests (SPEC-061 T047)."""
import http.client
from urllib.parse import urlsplit

JSON = {"Content-Type": "application/json"}


def http_request(port, method, path, headers=None, body=None, host=None):
    """One request to the loopback server: `(status, response, body)`.

    The `Host` header defaults to the server's own `127.0.0.1:<port>`; pass `host` for another spelling.
    """
    headers = dict(headers or {})
    headers.setdefault("Host", host or f"127.0.0.1:{port}")
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        return response.status, response, response.read()
    finally:
        connection.close()


def read_cookie(port, open_url):
    """Spend the one-time open URL and return the `name=value` read cookie."""
    target = urlsplit(open_url)
    status, response, _ = http_request(port, "GET", f"{target.path}?{target.query}")
    if status != 303:
        raise AssertionError(f"the open URL answered {status}, not 303")
    return response.getheader("Set-Cookie").split(";")[0]
