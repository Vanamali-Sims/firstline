import pytest
from pydantic import SecretStr, ValidationError

from firstline.cli import main
from firstline.config import Settings


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("OPENROUTER_API_KEY", "AZURE_SEARCH_ENDPOINT", "AZURE_SEARCH_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir("/")  # keep a developer's real .env out of the tests


def test_defaults_run_offline_ready() -> None:
    s = Settings(_env_file=None)
    assert s.search_backend == "local"
    assert s.decision_provider == "jev"
    assert s.openrouter_api_key is None


def test_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIRSTLINE_DECISION_PROVIDER", "bosun")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    s = Settings(_env_file=None)
    assert s.decision_provider == "bosun"
    assert s.openrouter_api_key == SecretStr("sk-test")


def test_unknown_provider_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIRSTLINE_LLM_PROVIDER", "azure_openai")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_azure_backend_needs_credentials() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, search_backend="azure")


def test_public_view_never_shows_secrets() -> None:
    s = Settings(_env_file=None, openrouter_api_key="sk-very-secret")
    view = s.public_view()
    assert view["openrouter_api_key"] == "set"
    assert view["azure_search_key"] == "missing"
    assert "sk-very-secret" not in repr(view)


def test_cli_config_prints_masked_settings(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-very-secret")
    assert main(["config"]) == 0
    out = capsys.readouterr().out
    assert '"openrouter_api_key": "set"' in out
    assert "sk-very-secret" not in out
