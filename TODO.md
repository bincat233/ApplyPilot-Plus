# TODO

- Continue merging valuable upstream PRs into ApplyPilot-Plus.
- Finish reviewing and selectively merging the remaining parts of upstream PR [#29](https://github.com/Pickle-Pixel/ApplyPilot/pull/29), especially:
  - `src/applypilot/scoring/pdf.py`
  - `src/applypilot/scoring/cover_letter.py`
  - `src/applypilot/apply/launcher.py`
  - `src/applypilot/apply/prompt.py`
  - `src/applypilot/enrichment/detail.py`
- Review upstream PR [#24](https://github.com/Pickle-Pixel/ApplyPilot/pull/24) (`litellm` migration) as a separate batch with real scoring/tailoring/cover regression checks before merging.
- Review upstream PR [#20](https://github.com/Pickle-Pixel/ApplyPilot/pull/20) (OpenCode backend support) as a separate batch on an isolated branch before considering merge.
