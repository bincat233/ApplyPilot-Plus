# TODO

- Decide whether to merge upstream PR [#24](https://github.com/Pickle-Pixel/ApplyPilot/pull/24) after isolated-branch validation.
  Notes:
  - doctor, LLM tests, single-job score, and single-job cover all passed on `review/litellm-pr24`
  - single-job tailor failed, but the same sample also failed on `main`
  - known tradeoff: LiteLLM path makes `doctor` fetch remote model metadata on startup
- Revisit upstream PR [#29](https://github.com/Pickle-Pixel/ApplyPilot/pull/29) only if more remaining pieces prove useful after real-world use.
- Keep upstream PR [#20](https://github.com/Pickle-Pixel/ApplyPilot/pull/20) isolated unless there is a clear reason to adopt the OpenCode backend architecture.
- Review targeted patches from `jbegarek/ApplyPilot-Enhanced` instead of treating it as a merge target.
  Priorities:
  - Lensa discovery improvements
  - Gemini compatibility/rate-limit handling
  - apply workflow quality-of-life fixes
