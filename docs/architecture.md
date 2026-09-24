# Architecture and reuse

Browser → local HTTP API → workflow rules → SQLite cases, requests, receipts, and events.

The handbook helper is a separate read-only path. It never receives an engine command capability. Optional local model output is accepted only as a nonempty list of IDs drawn from retrieved candidate policies. Displayed content always comes directly from those policy records.

## Transition contract

| Action | Required actor and state | Result |
|---|---|---|
| Create | People Ops; validated department/name/date | Pending assigned-manager approval |
| Approve/decline | Assigned manager; pending | Delivery ready or blocked |
| Deliver | People Ops; approved and pending | Deliberate simulated failure |
| Retry | People Ops; approved and failed | One simulated receipt |
| Acknowledge | Employee on own case; not acknowledged | Handbook step complete |
| Escalate | Actor with case visibility; no open review | Review flag and audit event |
| Resolve | People Ops; review open | Review closed; other rules unchanged |

Commands include a UUID request key and expected case version. `BEGIN IMMEDIATE` serializes writes. An exact replay returns the previous outcome; a changed payload with a used key is rejected. Permissions are evaluated before replay. Case changes, receipts, audit events, and request results commit together. HTTP mutations require a local origin, expected Host, JSON, and a process token. These protections reduce cross-site requests; they do not constitute user authentication.

The simulator runs inside a single SQLite transaction because it performs no network call. For a real connector, introduce a durable outbox with task claiming, lease expiry, backoff, bounded retries, remote idempotency keys, and reconciliation for uncertain outcomes. Do not hold this transaction open across a network request or claim exactly-once external delivery from the local receipt table.

## Reuse decisions

- Reused design patterns from the existing Health OS care-workflow engine: actor checks before replay, optimistic versioning, explicit state transitions, durable failure records, and traceable events.
- Used LaneOS/CLD ownership documentation as a reference for separating the operating system that owns records from adapters that execute bounded actions.
- Implemented a small independent engine for this demonstration. No clinical data, clinical rules, private employee data, or service credentials were copied.
- Used existing local Python/SQLite and browser capabilities. No new cloud account, framework, paid subscription, model download, or infrastructure deployment was introduced.
- This is one complete reusable workflow, not a claim that all prior platform systems are integrated or live.

## Adaptation points

`config.json`: brand, synthetic actors, department manager and access bundle.
`policies.json`: versioned fictional handbook passages and matching terms.
`core.py`: transition rules and connector simulator.
`knowledge.py`: read-only retrieval and optional local model selection.
`server.py`: local server and boundary validation.
`static/`: dashboard presentation.

Before a production adaptation: real identity and session management, tenant and document-level access, protected secrets, scoped connectors, durable delivery workers, retention/deletion rules, redacted logs, monitored failures, backups, transport security, and tests against the actual target services are required. SQLite triggers prevent event mutation through ordinary commands, not tampering by someone who controls the database file. No autonomous hiring or employee eligibility decisions are implemented.
