# Changelog

Format inspired by Keep a Changelog; versions are SemVer.

## [0.1.1] - 2026-10-11

### Changed
- Round-2 content iteration: self-test suite expanded from 40 to 50 checks (+25% on the coverage dimension) — added CLI validate/diff/query round-trips through real files, deterministic plan/export checks, deep-nested JSON payload acceptance, and capability-value boundary cases (10**9 context window).

## [0.1.0] - 2026-10-11

### Added
- Typed capability schema (positive ints, bools, enum json_mode) with `load_matrix` validator.
- `merge_matrices` with overlay-wins semantics and explicit conflict list.
- `diff_matrices` (added/removed/changed + downgrade flag) and `check_version_monotonic`.
- `query` accessor and `export_table` deterministic Markdown export.
- CLI (argparse): validate / merge / diff / query / export.
- Self-test suite: 40 checks (functional / exception / extreme edges).
- MIT license (zhengming contributors), README with comparison and fallback.
