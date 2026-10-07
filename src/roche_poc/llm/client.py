"""Connection to the local LM Studio server (no data leaves the machine)."""

from __future__ import annotations

from roche_poc import config


def get_client(base_url: str | None = None, timeout: float | None = None):
    """OpenAI-compatible client. The base URL MUST end with ``/v1``."""
    from openai import OpenAI

    return OpenAI(
        base_url=base_url or config.LM_STUDIO_BASE_URL,
        api_key="lm-studio",  # ignored by LM Studio
        timeout=timeout or config.LM_STUDIO_TIMEOUT,
    )


def list_models(client=None) -> list[str]:
    client = client or get_client()
    return [m.id for m in client.models.list().data]


def is_server_available(client=None) -> bool:
    """True when the server answers (avoids crashing the dashboard)."""
    try:
        list_models(client)
        return True
    except Exception:
        return False
