# AGENTS.md

Instructions for AI coding agents working in this repo. Humans: see `README.md`
and `docs/design.md`.

## Setup and commands

Python 3.12, managed with [uv](https://docs.astral.sh/uv/). The dev machine is
Windows/PowerShell and CI is Linux, so don't write shell-specific code, and use
`pathlib` for paths.

```bash
uv sync --extra dev                  # install
uv run ruff check src tests          # lint
uv run ruff format --check src tests # format
uv run mypy                          # types (strict)
uv run pytest                        # tests
uv run firstline config              # effective settings, secrets masked
```

**Definition of done:** ruff check, ruff format check, mypy and pytest all pass.
This mirrors `.github/workflows/ci.yml`. Run them yourself; don't report success
without doing so.

## Must not break

If a task seems to need breaking one of these, stop and ask.

1. **Code owns decisions.** Models return probabilities and drafts. Thresholds,
   routing and what gets shown live in code and have tests. Never let model
   output choose the route directly.
2. **Every decision is recorded** as a `Decision` in the trail, with its step,
   confidence, who decided and the evidence it used.
3. **Issue text is untrusted.** Sanitise it, cap its length, wrap it as quoted
   data in every prompt. Never let it become instructions.
4. **Citations come from tool results in the same run.** The citation checker is
   code, not a model. Don't loosen it to make a reply pass; fix the cause.
5. **The rules baseline stays.** It is the CI path, the outage fallback and the
   eval baseline. Fallbacks are marked as degraded, never silent.
6. **Frozen data is frozen.** Don't edit the snapshot or the split files by hand.
   Ground truth comes from the GitHub data, never typed in.
7. **The test split is run once per final configuration.** Tune on dev only.
8. **No invented numbers.** README results come from saved runs. Anything not
   run says "not run".
9. **Never write to the source project's GitHub repo.** Integrations run only
   against the sandbox repo.
10. **Never read, print or commit `.env`.** Use `.env.example` to see what
    variables exist.

## Where things live

```
src/firstline/
  types.py     SourceId, NewIssue, Issue, SearchHit, Decision, Route, TriageResult
  config.py    Settings (env + .env), provider switches, hard limits
  cli.py       `firstline` command
tests/         one test file per module
docs/design.md the design: decisions, flow, knowledge, eval, guardrails
```

## Adding things

- **A tool:** typed pydantic input, returns `SearchHit`s with `SourceId`s, never
  raises into the agent loop (bad input raises a clear error; missing data
  returns nothing with a reason). Add tests, including the time-travel filter if
  it searches issues.
- **A decision:** give it a step, a rules fallback or a written reason it has
  none, a threshold in code, and a metric in the eval.
- **An eval case:** cases come from the snapshot and the split files, never
  written by hand to improve a score. Red-team cases are labelled as synthetic.

## Commits

Small commits on a feature branch, merged to `main` with `--no-ff`. The subject
says what changed; the body lists what and why in short bullets.
