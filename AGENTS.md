# AGENTS.md

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
- `python -m applypilot.cli run ...`
- `python -m applypilot.cli apply`
- `python -m applypilot.cli dashboard`
- `pytest -q`

## Editing Rules
- Prefer small, local changes over broad rewrites.
- Keep runtime behavior consistent across CLI, pipeline, and database-backed stages.
- When changing a data contract, update its prompt/input, validator, renderer, and tests together.
- Do not add fast-changing planning or tracking files to the repo root.

## Validation
- Run `python -m py_compile` on changed Python files.
- Run targeted `pytest` for changed behavior.
- For pipeline-stage changes, verify with the affected CLI command.

## Logging
- Default runs should stay readable at `--log-level info`.
- More verbose SDK / HTTP detail may appear at `--log-level debug`.
- Keep file logs plain-text.

## Notes
- If local code and installed package behavior differ, prefer `PYTHONPATH=src`.
- PDF generation depends on Playwright / Chromium being installed.
- For simple database inspection or updates, prefer `sqlite3` over ad hoc Python scripts.
- Add a short artifact-flow summary here later, but only after the current JSON/PDF pipeline has stabilized.
