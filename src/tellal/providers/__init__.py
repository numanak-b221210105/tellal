from __future__ import annotations

from .base import Provider, ProviderError, PublishRequest, PublishResult

__all__ = ["Provider", "ProviderError", "PublishRequest", "PublishResult", "get_provider"]


def get_provider(name: str, settings) -> Provider:  # noqa: ANN001
    if name == "instagram":
        from .instagram import InstagramProvider

        return InstagramProvider(settings)
    from .demo import DemoProvider

    return DemoProvider()
