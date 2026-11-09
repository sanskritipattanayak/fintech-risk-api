# Demo diagrams (Mermaid)

GitHub renders these inline. For slides, open this file on GitHub and screenshot each diagram, or paste the source into any Mermaid renderer.

## Harness overview

```mermaid
flowchart LR
  subgraph Triggers
    A[PRD in docs/prd/]:::t
    B[Log alert]:::t
  end
  subgraph Claude["Claude Code harness"]
    S[Skills<br/>prd-to-spec, spec-to-code,<br/>log-triage, bugfix-pr, secure-ship]
    SA[Subagent<br/>security-reviewer<br/>read-only tools]
    H{{Hooks<br/>prompt DLP, path policy,<br/>command policy, commit gate,<br/>post-edit lint, stop gate}}
  end
  subgraph Evidence
    AU[(audit.jsonl<br/>hashes only)]
    EV[compliance-evidence pack]
  end
  A --> S
  B --> S
  S <--> H
  S --> SA
  H --> AU
  S --> EV
  S --> PR[Pull request]
  PR --> HUM[Human review<br/>CODEOWNERS]
  HUM --> CI[CI: tests, DLP re-scan]
  CI --> PROD[Production environment<br/>human approval]
  classDef t fill:#eef,stroke:#446;
```

## Flow 1: PRD to prod

```mermaid
flowchart TD
  P[PRD] --> SP[prd-to-spec]
  SP --> G1{{G1: human approves spec}}
  G1 --> PL[Plan mode]
  PL --> G2{{G2: human approves plan}}
  G2 --> SC[spec-to-code: tests first]
  SC --> SS[secure-ship<br/>tests, data check, secret scan,<br/>security-reviewer subagent]
  SS --> G3{{G3: human says ship}}
  G3 --> PR[PR opened]
  PR --> G5{{G5: CODEOWNERS review}}
  G5 --> CI[CI]
  CI --> G6{{G6: production approval}}
  G6 --> D[Deploy by CI, not Claude]
```

## Flow 2: log alert to fix PR

```mermaid
flowchart TD
  L[logs/app.log<br/>declines spike after 00:00 UTC] --> T[log-triage<br/>haiku, read-only, redacts first]
  T --> R[incidents/INC-DEMO-001.md]
  R --> G4{{G4: eligible?}}
  G4 -- no --> OC[Page on-call, stop]
  G4 -- yes --> BF[bugfix-pr<br/>failing test, minimal fix<br/>sonnet, edits only app/ and tests/]
  BF --> SS[secure-ship]
  SS --> SR[security-reviewer subagent]
  SR --> G3{{G3: human says ship}}
  G3 --> PR[PR with evidence]
  PR --> G5{{G5: human review}}
  G5 --> EV[compliance-evidence pack]
```

## Sequence: one headless run with hooks live

```mermaid
sequenceDiagram
  participant Op as Operator / CI
  participant CC as claude -p (no --bare)
  participant H as Hooks
  participant FS as Repo
  Op->>CC: prompt + allowedTools + max-budget-usd
  CC->>H: UserPromptSubmit (DLP)
  H-->>CC: ok
  CC->>H: PreToolUse (path and command policy)
  H-->>CC: allow / block
  CC->>FS: edit app/ and tests/ (allowed paths only)
  CC->>H: PostToolUse (DLP, ruff, float-for-money)
  CC->>H: Stop (tests must be green)
  H-->>Op: decisions logged to audit.jsonl (hashes)
  CC-->>Op: JSON result, cost, branch ready for human ship
```

## Defence in depth (guardrail layers)

```mermaid
flowchart LR
  O[Org policy] --> PR[Permission rules] --> HK[Hooks] --> CG[Commit/push/PR gate]
  CG --> GH[Git hooks] --> CI[CI re-scan] --> RV[CODEOWNERS + branch protection] --> AP[Prod approval]
```

## What the bug looks like

```mermaid
flowchart LR
  E[Event at 01:00 UTC] --> C{UTC date vs UTC-5 ledger date differ?}
  C -- no --> N[Record once: correct count]
  C -- yes --> M[Record three times: count inflated]
  M --> F[False DECLINED_VELOCITY, 00:00-05:00 UTC]
```
