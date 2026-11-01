# Helpdesk escalation and service priorities

SYNTHETIC TRAINING DOCUMENT. Version 2026-11-01. These fictional response targets support an assignment demonstration. They are not official UCP commitments and do not guarantee resolution.

## When and how to escalate
Escalate a service problem when two appropriate basic checks fail, the issue affects several users, or the next step would require an authorized administrator. Stop repeating device resets when current status indicates a shared outage. Describe the evidence, remaining uncertainty and recommended next action. An outage can justify a revised plan even if earlier device checks were reasonable at the time.

Collect a short symptom description, affected service, operating system when relevant, non-sensitive error text, the checks already attempted, and the current simulated service observation. User preference records describe earlier context; they do not prove that the same incident is still active. A past successful workaround is not automatically appropriate for a new outage.

## Fictional priority targets
Priority P1 is a widespread loss of an essential shared service affecting many users: the fictional first-response target is one hour. Priority P2 is a single user unable to perform a core task with no permitted workaround: the target is four working hours. Priority P3 is a non-blocking request with a permitted workaround: the target is two working days. These are response targets, not promised repair times. The simple ticket service stores a category and an open status; it does not implement automatic priority assignment or an SLA timer.

If the assistant explains these priority rules, it must retrieve and cite this policy. It must not claim that an actual technician has accepted the request. Service recovery times remain unknown unless explicitly present in the current simulated tool response.

## Confirmation, ticket state and memory
Preparing a draft does not create a ticket. Show the draft summary and category, then wait for the user to click Confirm or enter the exact confirmation command for that draft. The application, not the LLM, authorizes this step. Repeating confirmation for the same draft returns the same saved ticket rather than opening duplicates. A different user or session cannot confirm that draft.

After creation, report only the identifier and state returned by the real MCP tool. Ticket lookup is scoped to the selected user. The user selector in this local educational prototype is not production authentication; do not deploy it as a multi-user public service. Save incident history and preferences only with permission. The knowledge collection contains procedures; user memory contains user-specific facts. They must remain distinct in both implementation and demonstration.
