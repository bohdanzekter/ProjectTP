# Changelog

All notable changes to this project will be documented in this file.
The format adheres to [Semantic Versioning](https://semver.org/).

## [0.1.1] - 2026-11-19

### Changed
- Updated `README.md` with PyPI installation (`sipl-toolkit-zekorfk`) and CLI usage examples.

## [0.1.0] - 2026-11-19

### Added
- `CORE-01`: Formal SIPL grammar (`grammar/sipl.lark`), lexical rules, operator precedence, and 10+10 positive/negative examples.
- `CORE-02`: Typed AST nodes with `SourceSpan` and parser with detailed syntax diagnostics.
- `CORE-03`: SIPL interpreter with partial dereferencing checks (`UndefinedVariableError`) and infinite-loop protection (`StepLimitExceededError`), >90% test coverage.
- `CORE-04`: Execution event model and JSON-serializable trace (`BeforeStatement`, `AfterStatement`, `VariableChanged`, `ConditionEvaluated`, `ExecutionFinished`, `ExecutionError`).
- `CORE-05`: CLI (`parse`, `check`, `run`, `trace`) with stable exit codes and JSON output contract.
- `VIS-01`: Parse Tree visualization in Text, JSON, DOT, and standalone SVG formats linked to source fragments.
- `VIS-02`: AST visualization and interactive HTML comparison (`Parse Tree ↔ AST`).
- `REL-01`, `REL-02`, `REL-03`: GitHub Actions CI, SemVer release packaging, and PyPI distribution.