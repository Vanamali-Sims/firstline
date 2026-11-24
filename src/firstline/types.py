"""Core records shared by every part of Firstline.

Tool results, agent decisions and the final triage all use these shapes, so
the decision trail, the citation checker and the eval read the same data.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceKind(StrEnum):
    ISSUE = "issue"
    DOC = "doc"
    CODE = "code"


class SourceId(BaseModel):
    """A stable reference to one thing a tool returned.

    Written as ``issue:123``, ``doc:docs/concepts/models.md#validators`` or
    ``code:pydantic/main.py::BaseModel``. Drafted replies cite sources in this
    form, and the citation checker compares them with what tools returned.
    """

    model_config = ConfigDict(frozen=True)

    kind: SourceKind
    ref: str = Field(min_length=1)

    @model_validator(mode="after")
    def _issue_refs_are_numbers(self) -> Self:
        if self.kind is SourceKind.ISSUE and not self.ref.isdigit():
            raise ValueError(f"issue source ref must be a number, got {self.ref!r}")
        return self

    def __str__(self) -> str:
        return f"{self.kind.value}:{self.ref}"

    @classmethod
    def parse(cls, text: str) -> SourceId:
        kind, sep, ref = text.strip().partition(":")
        if not sep or not ref:
            raise ValueError(f"not a source id: {text!r}")
        try:
            source_kind = SourceKind(kind)
        except ValueError as exc:
            raise ValueError(f"unknown source kind {kind!r} in {text!r}") from exc
        return cls(kind=source_kind, ref=ref)


class NewIssue(BaseModel):
    """An issue to triage. Title and body are untrusted text."""

    model_config = ConfigDict(frozen=True)

    title: str = Field(min_length=1)
    body: str = ""


class Issue(NewIssue):
    """A closed issue from the snapshot, with what actually happened to it.

    ``labels``, ``duplicate_of`` and ``fix_files`` are the ground truth the
    eval scores against.
    """

    number: int = Field(gt=0)
    labels: tuple[str, ...] = ()
    created_at: datetime
    closed_at: datetime | None = None
    state_reason: Literal["completed", "not_planned", "duplicate", "reopened"] | None = None
    duplicate_of: int | None = None
    fix_files: tuple[str, ...] = ()
    url: str | None = None

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.closed_at is not None and self.closed_at < self.created_at:
            raise ValueError(f"issue {self.number} closed before it was opened")
        if self.duplicate_of == self.number:
            raise ValueError(f"issue {self.number} can't be a duplicate of itself")
        return self

    @property
    def source_id(self) -> SourceId:
        return SourceId(kind=SourceKind.ISSUE, ref=str(self.number))


class SearchHit(BaseModel):
    """One result from a search tool."""

    model_config = ConfigDict(frozen=True)

    source: SourceId
    title: str
    snippet: str
    score: float
    url: str | None = None


DecisionStep = Literal[
    "D1_safety",
    "D2_type",
    "D3_research",
    "D4_duplicates",
    "D5_labels",
    "D6_fix_location",
    "D7_reply",
    "D8_route",
]


class DecidedBy(StrEnum):
    """Who made a decision. Shown on every line of the decision trail."""

    RULE = "rule"
    DECISION_MODEL = "decision_model"
    LLM = "llm"
    HUMAN = "human"


class Decision(BaseModel):
    """One decision in the trail: what was asked, what was chosen, how sure, by whom."""

    model_config = ConfigDict(frozen=True)

    step: DecisionStep
    question: str = Field(min_length=1)
    answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    decided_by: DecidedBy
    options: tuple[str, ...] = ()
    evidence: tuple[SourceId, ...] = ()
    reason: str = ""

    @model_validator(mode="after")
    def _answer_is_an_option(self) -> Self:
        if self.options and self.answer not in self.options:
            raise ValueError(f"answer {self.answer!r} is not one of {self.options}")
        return self


class Route(StrEnum):
    """What happens to the triage. Code decides this, never a model."""

    AUTO = "auto"
    SUGGEST = "suggest"
    HUMAN = "human"


class TriageResult(BaseModel):
    """Everything Firstline produced for one issue, in decision order."""

    decisions: list[Decision]
    route: Route
    route_reason: str = Field(min_length=1)
    reply: str | None = None

    def decision(self, step: DecisionStep) -> Decision | None:
        """The last decision made at ``step``, if any."""
        for d in reversed(self.decisions):
            if d.step == step:
                return d
        return None
