# Security knowledge

## Data handling
Call transcripts and lead records stay on your machine in the prototype: SQLite locally, knowledge files locally, and browser speech APIs for audio. No call data is sent to this application's server. Browser speech recognition may be processed by the browser vendor; production deployments replace it with self-hosted Whisper or a contracted speech provider with a data-processing agreement.

## Access control
The production design uses per-tenant IDs, role-based access, short-lived tokens, and audit logs on every lead and appointment change. Transcripts are encrypted at rest and TLS is used in transit.

## Retention
Lead data is retained according to the customer's policy. Deleting a lead removes its messages, summary and appointments. The prototype includes a reset endpoint for a clean demo.
