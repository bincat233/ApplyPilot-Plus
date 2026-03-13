# AGENTS.md

## Purpose
ApplyPilot-Plus is a maintained fork of ApplyPilot for:
- job discovery and enrichment
- LLM scoring, resume tailoring, and cover letters
- browser-based auto-apply

Keep changes pragmatic. Prefer small, local fixes over broad rewrites.

## Environment
- Use the repo-local virtualenv: `.venv`
- Run from the repository root
- Prefer local source execution with `PYTHONPATH=src`

Typical setup:

```bash
source .venv/bin/activate
export PYTHONPATH=src
```

## Common Commands
- `python -m applypilot.cli doctor`
- `python -m applypilot.cli status`
- `python -m applypilot.cli run discover`
- `python -m applypilot.cli run enrich`
- `python -m applypilot.cli run score`
- `python -m applypilot.cli run tailor`
- `python -m applypilot.cli run cover`
- `python -m applypilot.cli apply`
- `python -m applypilot.cli dashboard`
- `pytest -q`

## Artifact Flow
- Base input resume: `resume.txt`
- Tailor intermediate artifact: `~/.applypilot/tailored_resumes/*.json`
- Tailor final artifact: `~/.applypilot/tailored_resumes/*.pdf`
- Tailor metadata/report files:
  - `*_REPORT.json`
  - `*_JOB.txt`

Database expectations:
- `tailored_resume_path` points to the final PDF
- `tailored_resume_json_path` points to the structured JSON artifact

Do not reintroduce tailored resume `.txt` files as the primary artifact.

## Tailor Schema
Structured tailored resumes use these field names:

- Experience entries:
  - `title`
  - `company_dates`
  - `bullets`
- Project entries:
  - `title`
  - `tech_dates`
  - `bullets`

If you change tailor schema semantics, update these together:
- prompt in `src/applypilot/scoring/tailor.py`
- validator in `src/applypilot/scoring/validator.py`
- renderer/assembly in `src/applypilot/scoring/tailor.py`
- any tests that assert structured output

## Logging
- Default local runs should be readable at `--log-level info`
- `--log-level debug` may include SDK / HTTP detail
- Keep file logs plain-text; terminal-only styling is fine

## Validation
For code changes:
- run `python -m py_compile` on changed Python files
- run targeted `pytest` for changed behavior
- for pipeline-stage changes, verify with the affected CLI command

Useful examples:

```bash
python -m py_compile src/applypilot/scoring/tailor.py
pytest -q tests/test_tailor_projects_optional.py
python -m applypilot.cli status
```

## Known Pitfalls
- If local code and installed package behavior differ, prefer `PYTHONPATH=src`
- `tailor` only processes jobs with `COALESCE(tailor_attempts, 0) < 5`
- `preserved_companies` is enforced during tailor validation
- PDF generation requires Playwright/Chromium to be installed
- `cover` should reconstruct tailored resume text from JSON when available

## Change Discipline
- Keep attribution and external tracking in GitHub issue `#1`
- Do not add fast-changing TODO tracking back into the repo root
- If adopting patches from upstream PRs or other forks, prefer selective merges over large dump merges
