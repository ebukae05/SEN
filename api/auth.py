"""API key authentication for the SEN FastAPI backend.

Exposes `verify_api_key`, a FastAPI dependency that enforces a shared-secret
`X-API-Key` header on every request *except* the paths listed under
`security.public_endpoints` in `config.yaml`.

The expected key is read from the environment variable named by
`security.api_key_env` (default: `SEN_API_KEY`) and compared with
`secrets.compare_digest` to avoid timing side-channels.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from secrets import compare_digest
from typing import Any

from fastapi import HTTPException, Request, status

from agents import load_config

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _security_config() -> dict[str, Any]:
    """Return the `security` block from config.yaml (cached)."""
    config = load_config()
    security = config.get("security")
    if not security:
        raise RuntimeError("config.yaml is missing the `security` section")
    return security


def _public_paths() -> frozenset[str]:
    """Return the configured set of unauthenticated endpoint paths."""
    paths = _security_config().get("public_endpoints", []) or []
    return frozenset(str(p) for p in paths)


def _expected_key() -> str:
    """Return the expected API key from the environment.

    Raises RuntimeError if the configured env var is unset, so a misconfigured
    deployment fails loudly at first authenticated request instead of silently
    accepting any header value.
    """
    env_var = _security_config().get("api_key_env", "SEN_API_KEY")
    key = os.environ.get(env_var)
    if not key:
        raise RuntimeError(
            f"Environment variable {env_var} is not set; cannot authenticate API requests"
        )
    return key


def verify_api_key(request: Request) -> None:
    """FastAPI dependency that enforces the `X-API-Key` shared secret.

    Endpoints whose path is listed under `security.public_endpoints` in
    config.yaml are allowed through without a header. Every other request must
    present a header matching the value of the configured environment variable.

    Raises:
        HTTPException(401): The header is missing or does not match.
    """
    if request.url.path in _public_paths():
        return

    header_name = _security_config().get("api_key_header", "X-API-Key")
    provided = request.headers.get(header_name)
    if not provided:
        logger.warning(
            "Rejected unauthenticated request to %s (missing %s header)",
            request.url.path,
            header_name,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": header_name},
        )

    expected = _expected_key()
    if not compare_digest(provided, expected):
        logger.warning(
            "Rejected request to %s with invalid API key", request.url.path
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": header_name},
        )
