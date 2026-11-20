"""Settings from environment variables (and an optional .env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


def _env(name: str, default: str = "") -> str:
    return os.environ.get(f"TELLAL_{name}", default)


@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(_env("DATA_DIR", "data")))
    # "demo" uses a simulated Instagram account; "instagram" talks to the real Graph API.
    mode: str = field(default_factory=lambda: _env("MODE", "demo"))
    # Public base URL of this server. Instagram downloads media from a public URL, so for
    # real publishing this must be reachable from the internet (a domain, tunnel or CDN).
    public_url: str = field(default_factory=lambda: _env("PUBLIC_URL", "http://localhost:8300").rstrip("/"))
    # Instagram API with Instagram Login (a Meta app you own).
    ig_app_id: str = field(default_factory=lambda: _env("IG_APP_ID"))
    ig_app_secret: str = field(default_factory=lambda: _env("IG_APP_SECRET"))
    ig_api_version: str = field(default_factory=lambda: _env("IG_API_VERSION", "v25.0"))
    # Optional LLM (any OpenAI-compatible endpoint: Ollama, OpenAI, OpenRouter, LM Studio ...).
    llm_base_url: str = field(default_factory=lambda: _env("LLM_BASE_URL", "http://localhost:11434/v1"))
    llm_model: str = field(default_factory=lambda: _env("LLM_MODEL", "qwen2.5:7b-instruct"))
    llm_api_key: str = field(default_factory=lambda: _env("LLM_API_KEY", "ollama"))
    llm_enabled: bool = field(default_factory=lambda: _env("LLM", "auto") != "off")
    # Optional password for the web panel (recommended when the server is public).
    admin_password: str = field(default_factory=lambda: _env("ADMIN_PASSWORD"))
    timezone: str = field(default_factory=lambda: _env("TIMEZONE", "Europe/Istanbul"))

    @property
    def db_path(self) -> Path:
        return self.data_dir / "tellal.sqlite"

    @property
    def media_dir(self) -> Path:
        return self.data_dir / "media"


settings = Settings()
