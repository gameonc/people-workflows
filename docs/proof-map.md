# Interview proof map

Verified September 27, 2026 on Python 3.14: 31 tests passed. This evidence applies to the local synthetic demo. CI configuration also exercises Python 3.10 and 3.13; inspect the current run before claiming it passed.

| Demonstrate | Evidence | Boundary |
| --- | --- | --- |
| Complete onboarding | test_complete_journey_replay_and_persistence, then browser walkthrough | Fictional actors and simulated deliveries |
| Human approval | test_wrong_manager, test_agent_cannot_approve | Actor selector is not real authentication |
| Duplicate and stale actions | test_concurrent_replay, test_stale_and_denied | Local SQLite behavior, not distributed exactly-once delivery |
| Recoverable delivery failure | test_complete_retry_and_receipt | Deliberate connector simulation |
| Durable state and audit | test_persistence, test_audit_mutation_rejected | Database owner can alter files; not tamper-proof compliance storage |
| Grounded policy answers | Knowledge tests | Keyword excerpts; optional model path mocked |
| HTTP request controls | HTTP and HTTPJourney tests | Loopback demo only; not a production security certification |

Run `python3 -m unittest discover -s tests -v`, then follow [the interview walkthrough](interview-walkthrough.md). Use a fresh --db path for each presentation; never delete operational data to reset a demo. No customer records or live API credentials belong here.
