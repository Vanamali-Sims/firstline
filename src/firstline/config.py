"""Settings, read from environment variables and an optional ``.env`` file.

Real environment variables win over ``.env``. Secrets are ``SecretStr`` and are
never printed: ``public_view`` reports only whether each one is set.
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FIRSTLINE_",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    # LLM: plans research and drafts replies. "fake" is the offline test double.
    llm_provider: Literal["openrouter", "fake"] = "openrouter"
    llm_model: str | None = None  # an OpenRouter slug; chosen once prices are checked

    # Decision model: the fast typed decisions (labels, duplicates, support checks).
    decision_provider: Literal["jev", "bosun", "fake"] = "jev"
    decision_model: str = "typesafe/jev-1.13"
    bosun_url: str = "http://localhost:8000"

    openrouter_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENROUTER_API_KEY", "FIRSTLINE_OPENROUTER_API_KEY"),
    )

    # Retrieval: "local" needs nothing; "azure" uses Azure AI Search.
    search_backend: Literal["local", "azure"] = "local"
    azure_search_endpoint: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AZURE_SEARCH_ENDPOINT", "FIRSTLINE_AZURE_SEARCH_ENDPOINT"),
    )
    azure_search_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("AZURE_SEARCH_KEY", "FIRSTLINE_AZURE_SEARCH_KEY"),
    )

    # Hard limits on the agent loop and on untrusted input.
    max_steps: int = Field(default=6, ge=1, le=20)
    max_searches: int = Field(default=4, ge=1, le=20)
    max_issue_chars: int = Field(default=8000, ge=500, le=100_000)

    @model_validator(mode="after")
    def _azure_needs_credentials(self) -> Self:
        if self.search_backend == "azure" and not (
            self.azure_search_endpoint and self.azure_search_key
        ):
            raise ValueError(
                "search_backend=azure needs AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY"
            )
        return self

    def public_view(self) -> dict[str, object]:
        """Settings safe to print or log: secrets show only as set or missing."""
        view: dict[str, object] = {}
        for name, value in self.model_dump().items():
            if isinstance(value, SecretStr) or name.endswith("_key"):
                view[name] = "set" if value else "missing"
            else:
                view[name] = value
        return view
