# Security scope

Local synthetic demonstration only. The HTTP server is restricted to 127.0.0.1 and checks Host, Origin, JSON content, body size, and a per-process command token. These controls reduce cross-site requests; they are not login or tenant isolation. Any local user can switch demo identities.

Fictional actors have deterministic role and case checks. Model output cannot select commands. Text is escaped before rendering. Source citations are validated against retrieved policies. SQL uses parameter binding. Duplicate writes and version conflicts are handled transactionally. SQLite triggers prevent ordinary event updates/deletes but cannot stop someone with filesystem access.

The package excludes saved databases, live signup links, private account links and operational records. Use fictional input only. Do not run behind a public tunnel or use for real employee data. Optional local-model requests send fictional questions and policy excerpts only to localhost; the model's own deployment has not been audited here.

Tests are bounded evidence, not proof of zero vulnerabilities. Production use is BLOCK_RELEASE until real identity, authorization, protected connectors and operational controls are implemented and verified.
