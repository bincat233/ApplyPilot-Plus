# TODO

- Continue merging valuable upstream PRs into ApplyPilot-Plus.
- Revisit upstream PR [#29](https://github.com/Pickle-Pixel/ApplyPilot/pull/29) only if additional remaining pieces turn out to be worth merging after real-world use.
- Review upstream PR [#24](https://github.com/Pickle-Pixel/ApplyPilot/pull/24) (`litellm` migration) as a separate batch with real scoring/tailoring/cover regression checks before merging.
  Main changes in that PR:
  - replace the custom LLM client with a LiteLLM-based adapter
  - centralize provider/model/api key resolution
  - add Anthropic support and broaden provider selection logic
  - update CLI, wizard, docs, and runtime checks around LLM configuration
  - add LLM resolution/client tests and optional Gemini smoke coverage
- Review upstream PR [#20](https://github.com/Pickle-Pixel/ApplyPilot/pull/20) (OpenCode backend support) as a separate batch on an isolated branch before considering merge.
