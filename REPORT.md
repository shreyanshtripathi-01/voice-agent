# Autonomous AI Sales Voice Agent — Project Report
**Fortivex AI · Round 3 prototype · Shreyansh Tripathi · 26 Nov 2026**

**Business problem.** Sales teams miss or mishandle inbound enquiries: no one answers every call, qualification is inconsistent, and the CRM is updated late. An AI agent that answers in the caller's language, qualifies live, retrieves accurate answers, books the meeting and hands a brief to a seller removes that loss.

**What was built.** A laptop-only prototype. "Ava" listens and speaks through the browser's free Web Speech APIs, runs a six-stage sales conversation, scores the lead on **BANT** (Budget, Authority, Need, Timeline), answers from a cited knowledge base, tracks sentiment, books a conflict-checked appointment into SQLite CRM, and generates an extractive summary with insights. **Zero paid services, zero third-party packages.**

**Technical implementation.**

| Layer | Prototype |
|---|---|
| Voice | Browser `SpeechRecognition` (STT), `speechSynthesis` (TTS); English / Hindi / Spanish |
| Logic | `agent.py`: session state, intent routing, slot filling, stage machine, localized replies |
| NLP | `nlp.py`: regex slots, ₹/timeline normalisation, negation-aware sentiment, multilingual intents |
| RAG | `rag.py`: markdown → heading chunks → TF-IDF + cosine similarity → source-cited answers |
| Memory / CRM | `crm.py`: SQLite leads, appointments, messages, summaries; no double bookings |
| API / UI | `server.py`: standard-library `ThreadingHTTPServer`; live score, sparkline, sources, booking |

**Workflow demonstrated:** greeting → need/role discovery → budget + timeline → authority → RAG answer with citation → slot choice → confirmed booking → AI summary. `python3 -m unittest discover -s tests -v` proves it in 5 tests; the UI's **Run demo call** repeats it unattended.

**Commercial feasibility.** The engine replaces repetitive first-call work. The prototype's knowledge base models Starter ₹1.5 lakh/yr, Growth ₹3.5 lakh/yr, Enterprise ₹9 lakh/yr. At 200 Starter customers that is ₹30 lakh ARR at >70% gross margin; upsells are languages, private RAG, connectors and analytics. The pilot itself costs nothing.

**Scalability to 1,00,000 users.** The API is stateless: replicas behind a load balancer autoscale on concurrent calls. Sessions move to **Redis** with TTL, SQLite to tenant-partitioned **PostgreSQL**, markdown retrieval to a **vector database** with embeddings and reranking. Audio enters via Twilio/SIP → self-hosted Whisper or a speech vendor; a queue decouples transcription, summarisation and CRM sync. For ~5k daily actives / 10k calls a day: 8–16 app pods, one DB with read replicas, regional object storage. Diagram: `docs/architecture.svg`.

**Data security.** Prototype data stays local. Production adds TLS in transit, AES-256 at rest, tenant-scoped queries, RBAC, short-lived tokens, audit logs on lead/appointment writes, configurable retention and cascading deletion. Browser STT may be vendor-processed; production uses self-hosted STT or a contracted provider with a DPA. `POST /api/reset` wipes demo data.

**Infrastructure, deployment, cost.** Prototype: `python3 app.py` on localhost — **₹0**. Production: containers on Cloud Run/ECS behind HTTPS, managed Postgres + Redis, object storage, CI/CD with tests, structured logs and conversion dashboards. Illustrative monthly cost at 100k users: compute $400–900, DB $250, cache $90, speech $300–2,000 (less with self-hosted Whisper), storage/egress $100, monitoring $50 → **~$1,200–3,400/month**; marginal cost per call is a few cents.

> Source, tests, architecture diagram and 1-page report are in this repository. Run `bash run.sh`.
