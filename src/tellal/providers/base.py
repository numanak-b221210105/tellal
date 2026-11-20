"""What a social platform connection must offer. Instagram is the first; the shape is kept general."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class ProviderError(Exception):
    """A publishing or API error. `retry` tells the scheduler whether trying again later can help."""

    def __init__(self, message: str, retry: bool = True, code: str = ""):
        super().__init__(message)
        self.retry = retry
        self.code = code


@dataclass
class PublishRequest:
    format: str  # post | carousel | reel | story
    media: list[dict[str, Any]]  # media rows with a "url" key (public URL the platform can download)
    caption: str = ""
    alt_text: str = ""
    cover_ms: int | None = None
    ai_label: bool = False
    first_comment: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class PublishResult:
    remote_id: str = ""
    permalink: str = ""
    # Set when the platform is still processing (videos): call resume() with it later.
    pending: str = ""


class Provider(Protocol):
    name: str

    def profile(self, account: dict[str, Any]) -> dict[str, Any]: ...

    def publish(self, account: dict[str, Any], req: PublishRequest) -> PublishResult: ...

    def resume(self, account: dict[str, Any], pending: str, req: PublishRequest) -> PublishResult: ...

    def insights(
        self, account: dict[str, Any], remote_id: str, fmt: str, published_at: float, post: dict[str, Any] | None = None
    ) -> dict[str, int]: ...

    def comments(self, account: dict[str, Any], remote_id: str, published_at: float) -> list[dict[str, Any]]: ...

    def reply(self, account: dict[str, Any], comment_remote_id: str, text: str) -> str: ...

    def quota(self, account: dict[str, Any]) -> dict[str, int]: ...
