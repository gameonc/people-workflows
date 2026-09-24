# A three-minute interview walkthrough

## Opening — 20 seconds

“I build practical automations around the systems a team already uses. I put together this fictional onboarding workflow to show how I handle approvals, exceptions, and evidence. It runs locally, and the external connections are simulated.”

## Show the happy path and the failure — 90 seconds

Start a new fictional Engineering hire if Avery is already completed. Show the People Ops view: intake creates the checklist, but cannot approve access. Switch to Jordan, the assigned manager, and approve. Return to Casey, process delivery, show the retained failure, then retry successfully. Switch to the new employee and acknowledge the handbook.

Explain: “The request moves through explicit states. An AI assistant cannot approve access. Duplicate requests reuse the original result, and an outdated screen cannot overwrite newer decisions.”

## Show the knowledge boundary — 30 seconds

Ask who approves workspace access. Point to the handbook citation and exact source text. Ask about the vacation allowance. Explain that missing information is referred to People Ops instead of inventing policy. The current running version uses keyword retrieval and source excerpts; an optional local model can select valid citations, but no live model is connected in this demonstration.

## Show the evidence — 20 seconds

Open the activity trail and download the JSON case evidence. Refresh the page. The completed state and failed attempt remain recorded. Automated checks cover invalid approvals, duplicate and concurrent retry requests, state persistence, and unavailable-model fallback.

## Explain the next integration — 20 seconds

“Before connecting this to your HRIS and Slack, I’d map the actual record owner, approval policy, connector scopes, failure handling, and handoff expectations. Then I’d connect one bounded workflow and measure it with the People team.”

## Interview claims to keep precise

- This is a tested local prototype built with AI coding assistance under Cady’s direction, not an existing customer deployment.
- HRIS, Slack, email, and provisioning calls are simulated. No message or account was created.
- The 25 tests and browser walkthrough are demonstrated evidence; customer savings and production reliability have not been measured.
- AI selects or explains information; deterministic rules control approvals and state changes.
- CLD Technology is the presentation brand. No new company tenure or legal-entity relationship is asserted by this demo.

## Measure during a real pilot

Track start-to-ready time, minutes of manual work per case, number of handoffs, failure recovery time, duplicate deliveries, and unresolved policy questions. Compare an agreed baseline with a limited pilot. Report observed values and sample size instead of promising an arbitrary percentage reduction.

## Relevant opportunity

Deepgram’s People AI & Automation Engineer role was the design target: https://jobs.ashbyhq.com/deepgram/bf8ea79f-f380-467e-8349-ea1ea8281316 . This demo is independent work and is not affiliated with or endorsed by Deepgram. Job availability should be checked again before applying.
