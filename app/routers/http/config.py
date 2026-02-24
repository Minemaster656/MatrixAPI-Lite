"""
Configuration API endpoints.

WHY: Provides public configuration to API consumers.
HOW: Returns non-sensitive config values that clients need to know.
"""

from typing import Any

from fastapi import APIRouter

from app.core.config import PUBLIC_CONFIG_KEYS, CHAT_MESSAGE_HISTORY_LIMIT

router = APIRouter(prefix="/api", tags=["api"])

_CONFIG_CACHE: dict[str, Any] = {}


def _build_public_config() -> dict[str, Any]:
    """Build public config from constants."""
    global _CONFIG_CACHE
    if not _CONFIG_CACHE:
        from app.core import config as config_module

        for key in PUBLIC_CONFIG_KEYS:
            if hasattr(config_module, key):
                _CONFIG_CACHE[key] = getattr(config_module, key)
    return _CONFIG_CACHE


@router.get(
    "/config",
    summary="Get public configuration",
    description="Returns public configuration values that API clients should know.",
)
def get_public_config() -> dict[str, Any]:
    """
    Retrieve public configuration values.

    Returns non-sensitive settings like message limits, character limits, etc.
    Server-specific secrets and internal values are not included.
    """
    return _build_public_config()
