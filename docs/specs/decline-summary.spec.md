---
Spec: decline-summary
Source PRD: docs/prd/PRD-DEMO-001-decline-summary.md
Status: APPROVED
Approved-by: sanskriti.pattanayak
Approved-on: 12 Nov
---

# Spec: Decline reason summary endpoint

## 1. Summary and non-goals

Add a read-only `GET /decisions/summary?date=YYYY-MM-DD` that returns declined-decision counts by reason code for one UTC calendar day, computed by reading the structured event log (`log_path()`).

Non-goals (from the PRD): no change to decision logic, thresholds, velocity check or model; no change to the log schema or allow-list; no new dependencies, auth changes, dashboards or UI; summary requests are not logged.

## 2. API contract

**Route:** `GET /decisions/summary` (no `/v1` prefix, matching existing routes).

| Part | Definition |
|---|---|
| Query | `date`: required, ISO calendar date `YYYY-MM-DD` (strict; no time part, no offset) |
| 200 body | `{"date": "YYYY-MM-DD", "total_declined": int, "by_reason": {"<REASON_CODE>": int}}`, exactly these three keys |
| 422 | `date` missing or malformed (including impossible dates such as `2026-13-40`); the error detail names the field `date` |

Rules:
- `date` in the response echoes the requested day in ISO format.
- Reason codes are the log's `decision` values that start with `DECLINED` (today `DECLINED_VELOCITY`, `DECLINED_RISK`). New `DECLINED_*` values are counted automatically.
- `total_declined == sum(by_reason.values())` always.
- `by_reason` contains only reasons with count > 0. It is `{}` when there are none.
- Key order in `by_reason` is not significant.
- A day with no declines, or a missing log file, returns 200 with `total_declined: 0` and `by_reason: {}`.
- Malformed log lines (invalid JSON, non-object, missing or unparseable `ts`, missing `decision`) are skipped, never raise a 500 (see Open questions Q3).

## 3. Money and time rules

- **Money:** the endpoint reads and returns no amounts. `amount` in the log is never parsed and never used. No `float` or `Decimal` arithmetic is introduced.
- **Time:** the window is the half-open interval `[date 00:00:00.000 UTC, next day 00:00:00.000 UTC)`. Event `ts` values are parsed as timezone-aware and converted to UTC before comparison. A `ts` without timezone info is skipped (the log writer rejects naive timestamps, so this is defensive). The server's local timezone is never consulted. The window is computed with `datetime(..., tzinfo=UTC)`, not `datetime.now()` or `date.today()`.
- Sub-second precision is preserved when parsing (`23:59:59.999Z` is in day N, `00:00:00.000Z` is in day N+1).

## 4. Data classification

| Field | Where | Classification | Handling |
|---|---|---|---|
| `date` (query) | request, response | synthetic-public | Validated, echoed |
| reason code (`decision`) | log read, response | synthetic-public | Returned as map key |
| count | response | synthetic-public | Returned |
| `ts` | log read | synthetic-public | Read for windowing only; not returned |
| `request_id` | log read | pseudo-id | Read for de-duplication only; never returned or logged |
| `card_id` | log read | pseudo-id (opaque token) | Never read into the result; never returned |
| `amount`, `currency`, `merchant_category`, `risk_score`, `velocity_count` | log | sensitive (treated as real) | Not read, not returned |

The response is built from a fixed whitelist of three keys. It is never built by passing through log records. No real PAN, SSN or name is accepted or produced.

## 5. Risk and abuse cases

| Case | Handling |
|---|---|
| Boundary of window (`23:59:59.999Z` vs `00:00:00.000Z`) | Half-open UTC window; AC2 |
| Duplicate log lines for one `request_id` (retry, double write, replay) | Count each `request_id` once (AC3) |
| Decline event with no `request_id` | Cannot be de-duplicated; counted once per line (Q1) |
| Same `request_id` appears with different decline reasons | First occurrence in file order wins (Q2) |
| Buggy or malicious `date` (`2026-13-40`, empty, `../x`, very long, `2026-3-1`, `20260301`, with time part) | 422, no file access depends on `date` |
| Path traversal / injection | `date` never touches a path or query; log path comes only from `log_path()` |
| Information leak via response | Fixed three-key whitelist; AC5 |
| Log tampering or log growth | Read-only; streams the file line by line (no full load into memory) |
| Corrupt or partially written last line | Skipped (Section 2) |
| Expensive repeated queries (DoS) | Out of scope here; no auth or rate limiting change per PRD. Noted in Q5 |
| Read causing writes | Opens in read mode only; no `emit`, no mkdir; AC6 |

## 6. Audit and logging

- No new structured events. The PRD scopes out logging summary requests.
- The endpoint calls neither `emit` nor `write_event`, so the event log and its allow-list are untouched.
- No PII is added to any log. Errors (422) use FastAPI's default validation response, which echoes only the invalid `date` input. No log field is reflected.
- The compliance-evidence pack records: the spec, AC to test mapping, test counts, security-reviewer result and gate approvals.

## 7. Acceptance criteria

Each is one pytest case in `tests/test_decision_summary.py`. All dates are in March 2026 and all data is synthetic (`card_` plus 8 hex digits).

| AC | Criterion | Test name |
|---|---|---|
| AC1 | 5 events on 2026-03-01 (`DECLINED_VELOCITY` x2, `DECLINED_RISK` x1, `APPROVED` x2) gives `total_declined=3`, `by_reason={"DECLINED_VELOCITY":2,"DECLINED_RISK":1}` | `test_ac1_counts_declines_by_reason` |
| AC2a | Declines at `2026-03-01T23:59:59.999Z` and `2026-03-02T00:00:00.000Z`: querying 2026-03-01 counts only the first | `test_ac2_boundary_last_millisecond_belongs_to_day_one` |
| AC2b | Same data: querying 2026-03-02 counts only the second (midnight UTC belongs to the new day) | `test_ac2_boundary_midnight_belongs_to_next_day` |
| AC3 | Same `request_id` recorded twice as `DECLINED_VELOCITY` on 2026-03-01 gives `total_declined=1` | `test_ac3_duplicate_request_id_counted_once` |
| AC4a | `date=2026-13-40` returns 422 and the message names `date` | `test_ac4_malformed_date_returns_422_naming_date` |
| AC4b | No `date` returns 422 and the message names `date` | `test_ac4_missing_date_returns_422_naming_date` |
| AC5 | Events carry `card_id`, `amount`, `request_id`: response keys are exactly `date`, `total_declined`, `by_reason`; none of those values appear in the body text | `test_ac5_response_has_no_log_fields` |
| AC6 | Log file bytes are identical before and after a valid request (and the file's mtime is unchanged) | `test_ac6_endpoint_does_not_write_log` |
| AC7a | No declines on the day gives 200, `total_declined=0`, `by_reason={}` | `test_ac7_no_declines_returns_zero` |
| AC7b | No log file gives 200, `total_declined=0`, `by_reason={}` (and the file is not created) | `test_ac7_missing_log_file_returns_zero` |

Additional cases from this spec (derived, not in the PRD table; tests also written first):

| ID | Criterion | Test name |
|---|---|---|
| X1 | Events with timezone offsets are converted to UTC: `2026-03-01T23:30:00-05:00` (= 2026-03-02T04:30Z) counts for 03-02 | `test_x1_offset_timestamps_converted_to_utc` |
| X2 | Malformed lines, blank lines and naive `ts` are skipped, not a 500 | `test_x2_malformed_log_lines_are_skipped` |
| X3 | `total_declined` equals the sum of `by_reason` | `test_x3_total_equals_sum_of_reasons` |
| X4 | `date` formats `2026-3-1`, `20260301` and `2026-03-01T00:00:00Z` return 422 | `test_x4_non_iso_date_formats_rejected` |
| X5 | Summary request does not alter `/score` behaviour or log (a `/score` decline then summary shows it counted) | `test_x5_end_to_end_score_then_summary` |

### Traceability: PRD requirement to acceptance criteria to tests

| PRD req | Requirement | AC / case | Test(s) |
|---|---|---|---|
| R1 | Route, exactly three keys | AC1, AC5 | `test_ac1_counts_declines_by_reason`, `test_ac5_response_has_no_log_fields` |
| R2 | UTC half-open day | AC2, X1 | `test_ac2_boundary_last_millisecond_belongs_to_day_one`, `test_ac2_boundary_midnight_belongs_to_next_day`, `test_x1_offset_timestamps_converted_to_utc` |
| R3 | Only `DECLINED*`; reason = decision; dedupe `request_id` | AC1, AC3, X3 | `test_ac1_counts_declines_by_reason`, `test_ac3_duplicate_request_id_counted_once`, `test_x3_total_equals_sum_of_reasons` |
| R4 | Missing or malformed `date` gives 422 naming `date` | AC4, X4 | `test_ac4_malformed_date_returns_422_naming_date`, `test_ac4_missing_date_returns_422_naming_date`, `test_x4_non_iso_date_formats_rejected` |
| R5 | No log fields in response | AC5 | `test_ac5_response_has_no_log_fields` |
| R6 | Read-only | AC6, AC7b | `test_ac6_endpoint_does_not_write_log`, `test_ac7_missing_log_file_returns_zero` |
| R7 | Empty day or no file gives 200 with zeros | AC7 | `test_ac7_no_declines_returns_zero`, `test_ac7_missing_log_file_returns_zero` |
| Out of scope guard | Decision, velocity, model, logging untouched | G2 diff check; X5 | `test_x5_end_to_end_score_then_summary` plus the existing suite staying green |

Every PRD requirement R1 to R7 maps to at least one acceptance test.

## 8. Test plan

- **Unit/API (pytest, `TestClient`):** all tests above use the autouse `log_path` fixture (temp file via `RISK_LOG_PATH`) and write synthetic JSONL with `build_record`/`write_event` or literal dicts. The committed `logs/app.log` is never read or written.
- **Fail first:** tests are written and run red (404 on the route) before any implementation.
- **Property test (optional, no new dependency):** a seeded `random` loop generates mixed events across 03-01 and 03-02, then asserts `total == sum(by_reason)`, that per-day totals match a brute-force count and that no event is counted on two dates. Hypothesis is not in the stack, so a seeded stdlib loop is used.
- **Regression:** the full existing suite must stay green. Existing log format tests confirm the schema is untouched.
- **Hygiene checks:** `fintech-data-check` on fixtures, ruff, DLP scan on the diff.
- **Diff budget:** at most 4 files or 120 lines under `app/` and `tests/`. Expected: `app/main.py` (route), one new module (log reader), `tests/test_decision_summary.py`. If that cannot fit, flag it at G2. The optional property test and X1 to X5 are the first to trim if over budget, never AC1 to AC7.

## 9. Rollout and rollback

- Read-only, additive route with no data migration. Existing routes are unaffected.
- **Flag:** no feature flag in the PRD. Proposed: none needed because the route is additive and read-only (Q4).
- **Shadow/staged:** deploy through the normal CI plus human approval (G6). Verify on the first day's data by comparing `by_reason` with a manual `grep` count on synthetic logs.
- **Rollback:** revert the PR (a single additive route and module); no state to repair.

## 10. Open questions for the human

- **Q1.** Log events with no `request_id`: count each line (spec default) or skip them? Counting avoids under-reporting.
- **Q2.** If one `request_id` appears with two different decline reasons, is first-occurrence-wins acceptable? (A request is only scored once today, so this should only occur through corruption.)
- **Q3.** Should malformed log lines be silently skipped (spec default), or should the endpoint return 5xx? Silent skipping risks hiding corruption. Do we want a skipped-line count internally, noting that the PRD limits the response to three keys?
- **Q4.** Confirm no feature flag is required.
- **Q5.** Is access control or rate limiting for this endpoint in scope? The PRD says no auth changes. The endpoint exposes only aggregate counts, but it reads the whole log on each call. Is that acceptable at current log sizes, or should it be revisited later?
- **Q6.** Should a very old or far-future `date` be rejected, or just return zeros? The spec default is zeros (200).

## Approval (G1)

Approved by sanskriti.pattanayak on 12 Nov (see header). Open questions Q1 to Q6 were resolved by accepting the spec defaults. `spec-to-code` may proceed.
