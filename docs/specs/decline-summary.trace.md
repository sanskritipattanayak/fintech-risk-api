# Trace: decline-summary

Spec: docs/specs/decline-summary.spec.md (Approved-by sanskriti.pattanayak, 12 Nov)

All tests are in `tests/test_decision_summary.py`. Route: `app/main.py` `decisions_summary`. Logic: `app/summary.py` `summarize`.

| Criterion | Test | Code |
|---|---|---|
| AC1 | `test_ac1_counts_declines_by_reason` | `summarize` (DECLINED prefix filter, `by_reason`) |
| AC2a | `test_ac2_boundary_last_millisecond_belongs_to_day_one` | `summarize` half-open window `start <= ts < end` |
| AC2b | `test_ac2_boundary_midnight_belongs_to_next_day` | same |
| AC3 | `test_ac3_duplicate_request_id_counted_once` | `summarize` `seen` set |
| AC4a | `test_ac4_malformed_date_returns_422_naming_date` | `decisions_summary` `fromisoformat` to `HTTPException(422)` |
| AC4b | `test_ac4_missing_date_returns_422_naming_date` | `decisions_summary` required `Query` |
| AC5 | `test_ac5_response_has_no_log_fields` | `summarize` fixed three-key return |
| AC6 | `test_ac6_endpoint_does_not_write_log` | read-only `path.open` |
| AC7a | `test_ac7_no_declines_returns_zero` | `summarize` |
| AC7b | `test_ac7_missing_log_file_returns_zero` | `path.exists()` guard |
| X1 | `test_x1_offset_timestamps_converted_to_utc` | `_event_time` `astimezone(UTC)` |
| X2 | `test_x2_malformed_log_lines_are_skipped` | `summarize` skip paths, `_event_time` naive check |
| X4 | `test_x4_non_iso_date_formats_rejected` (3 params) | `Query(pattern=...)` |

Not implemented: X3 (total equals sum, true by construction) and X5 (end-to-end `/score`), dropped for budget. The optional property test is also not written.

Result: `pytest -q` gives 107 passed, 1 xfailed (pre-existing `test_correct_code_has_no_midnight_spike`). 15 tests are new (10 AC tests, X1, X2, X4 x3). Before implementation all 15 failed (404 on the route).
