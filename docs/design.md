# Firstline design

Firstline reads a new GitHub issue and makes the calls a support engineer would:
what kind of issue it is, whether it's safe and complete, whether it's a
duplicate, which labels it needs, where the fix probably goes, and what to reply.
A fast decision model makes most of those calls. An LLM is used only where
reasoning or writing is needed. Every decision is logged with a confidence and
the evidence it used, and the eval checks it against what actually happened to
real issues.

The question the project answers: **how much of issue triage can a cheap, fast
decision model handle on its own, and how do you know when to hand off to an LLM
or a human?**

## What a user sees

Paste an issue, or pick a real one from the snapshot, and get:

- type (bug / feature / question / docs) and whether there's enough information to act on
- labels, each with a confidence
- likely duplicates with links, each marked *duplicate* or *related*
- the source files the fix probably touches
- relevant docs pages
- a drafted first reply where every sentence cites an issue, doc page or file
- a route: *auto*, *suggest* or *needs a human*, with the reason
- the decision trail: each decision in order, who made it, how sure, on what evidence

## Decisions

Each graph step makes one decision. **Code owns the thresholds and the final
action.** Models return probabilities and drafts; code decides what happens.

| Step | Decision | Made by | What code does with it | Measured by |
|---|---|---|---|---|
| D1 | Safety: instructions aimed at an AI, or spam? | Rules + decision model (yes/no) | Flagged: triage runs, no draft, goes to a human | Red-team set: detection and false-positive rates |
| D2 | Type and completeness (version, repro, error) | Decision model | Incomplete bug: reply asks for exactly what's missing | Accuracy against real type labels |
| D3 | Research: which sources, which queries, when to stop | LLM planner; decision model answers "is the evidence enough?" | Caps on steps and searches, temperature 0 | Steps and tokens per issue; ablation |
| D4 | Duplicate verdict per candidate | Decision model, pairwise | Shown only above a threshold tuned on dev | Hit@5 and precision vs maintainers' duplicate closes |
| D5 | Labels | Decision model, one yes/no per label | Per-label thresholds; uncertain band escalates to the LLM | Precision, recall, macro-F1 |
| D6 | Fix location | Code search, then decision model scores files | Top 5 shown | Hit@5 vs files changed in the linked fix PR |
| D7 | Reply and verification | LLM drafts; code + decision model verify | Citation must come from a tool result in this run; unsupported sentences dropped, one repair attempt | Citation validity, unsupported-claim rate, human rating |
| D8 | Route | Code policy | Human if flagged, low confidence, or the decision model and LLM disagree | Escalation rate; accuracy on what isn't escalated |

### System 1 and System 2

The decision model (Jev, or an open model with the same API) reads a state, a
question and a list of options, and returns a probability per option in one
forward pass. It doesn't write text. The LLM is slower and costs more, but it can
plan and write. Most triage decisions are choices, so each one goes to the
cheapest thing that can make it and escalates on uncertainty:

```
rules ──(can't decide)──► decision model ──(uncertain)──► LLM ──(unsure / disagree)──► human
```

Known limit, designed around: these models decide well about one record at a
time, not about what several records imply together, and they trust a summary
they're given even when it's stale. So every decision-model question is about a
single issue or a single pair, and anything that combines sources goes to the LLM.

## Flow

LangGraph: each decision is a node, each route a conditional edge.

```
            new issue
                │
     ┌──────────▼──────────┐
     │ D1 sanitise + gate  │──flagged───────────────────────────┐
     └──────────┬──────────┘                                     │
     ┌──────────▼──────────┐                                     │
     │ D2 type + complete? │──incomplete──► needs-info reply ────┤
     └──────────┬──────────┘                                     │
     ┌──────────▼────────────────────────────────┐               │
     │ D3 research loop (LLM plans, model stops) │               │
     │ search_issues · search_docs · search_code │               │
     └──────────┬────────────────────────────────┘               │
        ┌───────┼─────────────┐                                  │
   ┌────▼───┐ ┌─▼───────┐ ┌───▼────────┐                         │
   │D4 dups │ │D5 labels│ │D6 fix files│   (in parallel)         │
   └────┬───┘ └─┬───────┘ └───┬────────┘                         │
        └───────┼─────────────┘                                  │
     ┌──────────▼──────────┐                                     │
     │ D7 draft + verify   │                                     │
     └──────────┬──────────┘                                     │
     ┌──────────▼──────────┐◄────────────────────────────────────┘
     │ D8 route            │──► response + decision trail
     └─────────────────────┘
```

## Knowledge

- **Source project:** a mid-size Python project with a permissive licence,
  well-labelled closed issues, duplicate closes and linked fix PRs. Chosen after
  checking those numbers; the choice and the counts go in the README.
- **Snapshot,** frozen with a date and commit SHA: closed issues (labels, state
  reason, duplicate link, fix PR changed files), docs split by heading, source
  split by function and class with `ast`.
- **Index:** Azure AI Search (Free tier) with BM25 + vectors fused by reciprocal
  rank fusion in our code, or a local BM25 + vector backend behind the same
  interface, so everything runs without Azure.
- **Time-travel replay:** when the eval replays an issue, issue search returns
  only issues closed before it was opened. Docs and code come from the snapshot
  commit, which is a small leak for older issues and is stated as a limit.

## Evaluation

Splits are by date, never random:

- **test:** the most recent closed issues; run once per final configuration
- **dev:** the issues before those; all thresholds are tuned here only
- **duplicates:** issues closed as duplicate whose original is older
- **red team:** real issues with planted instructions, plus untouched controls

Systems on the same issues: rules baseline (no models), LLM-only (one prompt,
no graph), decision-model-only, the full cascade, and ablations (no code search,
no docs search, no verifier, no stop check).

Metrics: label precision/recall/macro-F1; duplicate hit@5 and precision;
fix-file hit@5; citation validity and unsupported-claim rate; a human rating of
a reply sample; escalation rate and coverage vs accuracy; injection detection and
false-positive rates; cost, latency and LLM calls per issue.

Reporting: every number comes from a saved run (config, git SHA, date) and has
a bootstrap confidence interval. Anything not run is shown as "not run".

## Guardrails

- Issue text is untrusted: sanitised, length-capped, wrapped as quoted data,
  never followed as instructions.
- Flagged issues get triage but no drafted reply.
- Citations are checked in code against tool results from the same run.
- Nothing is written to the source project. The GitHub integration runs only on
  a separate sandbox repo.
- The public demo has a per-IP rate limit, a daily cap, a token cap per request
  and an API key with a hard credit limit.

## Stack

Python 3.12, uv, ruff, mypy, pytest · LangGraph · Jev via OpenRouter, with an
open Jev-compatible model as fallback · an LLM via OpenRouter · Azure AI Search
or local retrieval · FastAPI and one demo page · Azure Container Apps with images
on GitHub Container Registry · GitHub Actions for CI and the sandbox integration.
