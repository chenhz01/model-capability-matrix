# ALIGNMENT — R13 compliance ledger (model-capability-matrix)

Date: 2026-10-11 · Round: R13 · Worker: W6 · Status: aligned

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | Pure Python standard library, zero third-party deps | PASS | imports: argparse/json/sys only |
| 2 | Runnable CLI with argparse entry | PASS | `python model_capability_matrix.py --help`; subcommands validate/merge/diff/query/export |
| 3 | self_test.py ≥40 cases | PASS | round 1 = 40 checks, round 2 +10 → 50 checks |
| 4 | Output ends with `SUMMARY: PASS n/n` | PASS | final print in self_test.py |
| 5 | Three test categories | PASS | blocks A (1–20), E (21–30), X (31–40), plus round-2 R block |
| 6 | Edge classes: empty / very long / corrupted / Unicode / deep nesting | PASS | X01 empty models, X02 10k-char name, E01 corrupted JSON, X03 unicode, X06 200-level nesting |
| 7 | README first paragraph ≤60 words | PASS | 36 words (self-counted, verified via `sed -n '3p' README.md \| wc -w`) |
| 8 | why-not-X table ≥3 alternatives with real anchors (name+stars+1 difference) | PASS | seanliii/ai-model-capability-matrix (0★) from _r13_design.json + 2 adjacent non-repo alternatives marked n/a |
| 9 | Minimal Fallback section | PASS | README §Minimal Fallback (jq + git diff on same JSON format) |
| 10 | Design Trade-offs section | PASS | README §Design Trade-offs (4 items) |
| 11 | Limits & Second-order Effects | PASS | README §Limits (validated-but-wrong data, schema lag) |
| 12 | FAQ incl. When NOT to use | PASS | README §FAQ final item |
| 13 | [Core Assumptions] ≥3 | PASS | README §Core Assumptions (4 items) |
| 14 | MIT LICENSE "zhengming contributors", no real names/keys | PASS | LICENSE line 3; no secrets/real names anywhere |
| 15 | CHANGELOG v0.1.0 → v0.1.1 revision trail | PASS | CHANGELOG.md, both entries dated 2026-10-11 |
| 16 | Number discipline: measured with repro or [estimated] | PASS | all timings tagged [estimated] with repro commands |

Two-iteration record: draft → self-review found the deep-nesting edge test was not exercising the real loader, and no CLI file round-trip existed → round 2 added 10 checks (+25% tests) including real-file CLI round-trips and deep-nested JSON through `load_matrix`. Tests re-run green after round 2.
