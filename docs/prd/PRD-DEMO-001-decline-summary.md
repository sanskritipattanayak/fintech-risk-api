# PRD-DEMO-001: Decline reason summary endpoint

**Flow:** 1 (PRD to prod)
**Status:** Draft. Input to `prd-to-spec`. The generated spec needs an `Approved-by` header from a human (G1) before any code.

## 1. Problem

Risk analysts and on-call engineers cannot see why transactions were declined on a given day without reading the raw event log by hand. That is slow and error-prone.

## 2. Goal

Add a read-only endpoint that returns declined-decision counts by reason for one UTC calendar day, computed from the service's structured event log.

## 3. Users

- **Risk analyst:** checks the decline mix for a day.
- **Engineer on call:** tells whether a spike is one reason or several.

## 4. Context (existing behaviour)

- The service writes one JSON event per scored request to the event log (`app/logging_config.py`; location from `log_path()`, overridable with `RISK_LOG_PATH`).
- Each event has `ts` (UTC ISO 8601), `event`, `decision` and `request_id`, among other allow-listed fields.
- The decision values are `APPROVED`, `DECLINED_VELOCITY` and `DECLINED_RISK`. The two `DECLINED_*` values are the **reason codes**.
- Existing routes: `GET /health`, `POST /score`, both in `app/main.py`. There is no `/v1` prefix and no database.

## 5. Requirements

**Must have**

1. `GET /decisions/summary?date=YYYY-MM-DD` returns JSON with exactly three keys: `date`, `total_declined`, `by_reason` (a map of reason code to count).
2. `date` is a UTC calendar day: from `00:00:00.000` up to, but not including, `00:00:00.000` of the next day, UTC. The endpoint never uses a local timezone.
3. Only events whose `decision` starts with `DECLINED` are counted. The reason code is the `decision` value. Each `request_id` is counted once, even if it appears more than once in the log.
4. A missing or malformed `date` returns HTTP 422 with a message that names the field `date`.
5. The response contains reason codes and counts only. It never includes a card id, amount, request id, or any other field from the log.
6. The endpoint is read-only. It never writes to the event log or any other file.
7. A day with no declines, or a log file that does not exist, returns HTTP 200 with `total_declined` 0 and an empty `by_reason`.

**Out of scope**

- Any change to decision logic, thresholds, the velocity check, or the model.
- Any change to the log schema or its field allow-list in `app/logging_config.py`.
- New dependencies, authentication changes, dashboards or UI.
- Logging the summary requests themselves.

## 6. Acceptance criteria

All dates are in March 2026 and all test data is synthetic. Each criterion is one pytest case.

| # | Given | When | Then |
|---|---|---|---|
| AC1 | A log with 5 events on 2026-03-01 UTC: `DECLINED_VELOCITY` x2, `DECLINED_RISK` x1, `APPROVED` x2 | GET `date=2026-03-01` | `total_declined=3`, `by_reason={"DECLINED_VELOCITY":2,"DECLINED_RISK":1}` |
| AC2 | Declines at `2026-03-01T23:59:59.999Z` and at `2026-03-02T00:00:00.000Z` | GET each of the two dates | The first is counted only for 2026-03-01, the second only for 2026-03-02 |
| AC3 | The same `request_id` recorded twice as `DECLINED_VELOCITY` on 2026-03-01 | GET `date=2026-03-01` | `total_declined=1` |
| AC4 | `date=2026-13-40`, or no `date` | GET | HTTP 422, message names `date` |
| AC5 | A log whose events carry `card_id`, `amount` and `request_id` | GET a valid date | Response keys are exactly `date`, `total_declined`, `by_reason`; no card id, amount or request id appears anywhere in the body |
| AC6 | Any valid request | The log file's bytes are compared before and after | Identical (no writes) |
| AC7 | No declines on the day, and separately no log file | GET a valid date | HTTP 200, `total_declined=0`, `by_reason={}` |

Tests for AC1 to AC7 are written first and must fail before the implementation.

## 7. Gates

| Gate | Human decision | Evidence the agent provides |
|---|---|---|
| G1 | Approves this PRD and the generated spec (adds `Approved-by`) | `prd-to-spec` output with AC1 to AC7 mapped to tests |
| G2 | Approves the plan: files to touch and test order | Plan mode output |
| G3 | Says "ship" after tests pass and the security reviewer reports | `secure-ship` results and reviewer findings |
| G5 | CODEOWNERS review of the PR | PR with evidence |
| G6 | Production approval in CI | CI results and compliance-evidence pack |

## 8. Build constraints for the agent

- Tests first (AC1 to AC7), then implementation.
- Edit only `app/` and `tests/`. The route is registered in `app/main.py`; a small new module under `app/` is acceptable. The spec trace file goes in `docs/specs/`.
- Do not touch `app/velocity.py`, `app/decision.py`, `app/model.py` or `app/logging_config.py`.
- Tests use a temporary log file (the test fixtures already set `RISK_LOG_PATH`). Never read or write the committed `logs/app.log` in a test.
- Diff budget: 4 files or 120 lines under `app/` and `tests/`.
- No new dependencies. Money rules (`Decimal`, never `float`) and tz-aware UTC apply across the service.

## 9. Success measures

- Spec, plan and failing tests exist before any code changes.
- AC1 to AC7 pass on the first green run, and the test count is recorded.
- The security reviewer runs and reports, and `secure-ship` passes.
- Humans approve at G1, G2, G3, G5 and G6. The agent never merges or deploys.

## 10. Risks

- **The agent edits decision or velocity code to make a test pass.** Mitigation: those paths are out of scope and checked at G2.
- **Scope creep into logging or dashboards.** Mitigation: the out-of-scope list is checked at G2.
- **Leaking log fields into the response.** Mitigation: AC5.
