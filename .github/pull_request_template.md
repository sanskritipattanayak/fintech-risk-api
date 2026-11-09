## Summary
<!-- What changed and why. Link the spec (Flow 1) or incident (Flow 2). -->

## Evidence
- [ ] Tests pass (`pytest -q`); regression test included for bug fixes
- [ ] `fintech-data-check`: PASS (synthetic only, Decimal money, tz-aware UTC)
- [ ] Secret scan clean, no new dependencies (or approved in spec)
- [ ] Independent security review run; findings and dispositions below
- [ ] Evidence pack linked (`evidence/<id>.md`), no `MISSING` items

## Security review findings
<!-- None, or list with disposition -->

## Risk
- [ ] Touches limits, thresholds or model scoring -> label `risk:high`

## Rollback
<!-- Flag, revert commit, or config change -->

## Gates
G1 spec / G4 triage: <link or n/a> | G3 ship: <approver> | G5 review: <reviewer>
