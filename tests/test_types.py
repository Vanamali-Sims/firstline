from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from firstline.types import (
    DecidedBy,
    Decision,
    Issue,
    Route,
    SourceId,
    SourceKind,
    TriageResult,
)

OPENED = datetime(2026, 3, 1, tzinfo=UTC)


@pytest.mark.parametrize(
    "text",
    [
        "issue:123",
        "doc:docs/concepts/models.md#validators",
        "code:pydantic/main.py::BaseModel",
    ],
)
def test_source_id_round_trips(text: str) -> None:
    assert str(SourceId.parse(text)) == text


@pytest.mark.parametrize("text", ["issue", "issue:", "wiki:page", "issue:abc", ":12"])
def test_source_id_rejects_malformed(text: str) -> None:
    with pytest.raises(ValueError):
        SourceId.parse(text)


def test_source_ids_compare_by_value() -> None:
    assert SourceId.parse("issue:7") == SourceId(kind=SourceKind.ISSUE, ref="7")
    assert len({SourceId.parse("issue:7"), SourceId.parse("issue:7")}) == 1


def test_issue_source_id() -> None:
    issue = Issue(number=42, title="t", created_at=OPENED)
    assert str(issue.source_id) == "issue:42"


def test_issue_cannot_close_before_it_opens() -> None:
    with pytest.raises(ValidationError):
        Issue(number=1, title="t", created_at=OPENED, closed_at=datetime(2026, 2, 1, tzinfo=UTC))


def test_issue_cannot_duplicate_itself() -> None:
    with pytest.raises(ValidationError):
        Issue(number=5, title="t", created_at=OPENED, duplicate_of=5)


def _decision(**overrides: object) -> Decision:
    fields: dict[str, object] = {
        "step": "D5_labels",
        "question": "Is this a bug?",
        "answer": "yes",
        "confidence": 0.9,
        "decided_by": DecidedBy.DECISION_MODEL,
        "options": ("yes", "no"),
    }
    fields.update(overrides)
    return Decision.model_validate(fields)


def test_decision_answer_must_be_an_option() -> None:
    with pytest.raises(ValidationError):
        _decision(answer="maybe")


def test_open_decisions_have_no_options() -> None:
    assert _decision(options=(), answer="anything").answer == "anything"


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_confidence_is_a_probability(confidence: float) -> None:
    with pytest.raises(ValidationError):
        _decision(confidence=confidence)


def test_unknown_step_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _decision(step="D9_magic")


def test_triage_result_finds_the_latest_decision_for_a_step() -> None:
    first = _decision(answer="no", confidence=0.55)
    second = _decision(answer="yes", confidence=0.95, decided_by=DecidedBy.LLM)
    result = TriageResult(decisions=[first, second], route=Route.SUGGEST, route_reason="r")
    assert result.decision("D5_labels") == second
    assert result.decision("D4_duplicates") is None
