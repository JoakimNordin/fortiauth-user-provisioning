from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

import requests


class FACError(Exception):
    def __init__(self, message: str, status: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status = status
        self.payload = payload


class FACClient:
    def __init__(self, host: str, username: str, api_key: str, verify_tls: bool = False, timeout: float = 15.0):
        self.base_url = f"https://{host}/api/v1/"
        self.auth = (username, api_key)
        self.verify_tls = verify_tls
        self.timeout = timeout
        self._session = requests.Session()

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = urljoin(self.base_url, path.lstrip("/"))
        kwargs.setdefault("auth", self.auth)
        kwargs.setdefault("verify", self.verify_tls)
        kwargs.setdefault("timeout", self.timeout)
        kwargs.setdefault("headers", {}).setdefault("Accept", "application/json")

        response = self._session.request(method, url, **kwargs)

        if response.status_code == 401:
            raise FACError(
                "Ogiltig API-nyckel eller behörighet saknas",
                status=401,
            )
        if response.status_code == 403:
            raise FACError(
                f"Förbjudet ({path}) - profilen saknar scope för denna endpoint",
                status=403,
            )
        if response.status_code == 404:
            raise FACError(f"Hittades inte: {path}", status=404)
        if 400 <= response.status_code < 500:
            payload = _safe_json(response)
            raise FACError(
                f"FAC avvisade payload ({response.status_code}): {payload}",
                status=response.status_code,
                payload=payload,
            )
        if response.status_code >= 500:
            raise FACError(
                f"FAC-serverfel {response.status_code}", status=response.status_code
            )

        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def get(self, path: str, params: dict | None = None) -> Any:
        return self._request("GET", path, params=params)

    def post(self, path: str, json: dict | None = None) -> Any:
        return self._request("POST", path, json=json)

    def patch(self, path: str, json: dict | None = None) -> Any:
        return self._request("PATCH", path, json=json)

    def delete(self, path: str) -> Any:
        return self._request("DELETE", path)


def _safe_json(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text[:500]
