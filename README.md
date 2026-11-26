# Fortivex AI — Autonomous AI Sales Voice Agent

A working, **free** prototype of an AI sales caller: it listens and speaks, qualifies a lead in real time, answers from a knowledge base, books a meeting into a CRM, and writes a call summary. Built with the Python standard library + browser speech APIs. **No API keys, no pip installs, no model downloads.**

---

## 1. Run it (60 seconds)

```bash
cd ~/fortivex-voice-agent
python3 app.py
```

Open **http://127.0.0.1:8765** in **Chrome or Edge**. (Alternatively `bash run.sh`.)

### Three ways to run the demo
1. **Run demo call** — one click plays a full six-turn prospect conversation, speaks the agent replies, books the appointment and generates the summary. Use this in the interview; it does not need a microphone.
2. **Start voice** — grant microphone permission and speak. Choose the call language first (English / Hindi / Spanish).
3. **Type a reply** — works in any browser, no microphone needed.

> Voice input uses the browser's Web Speech API. `localhost` is a trusted origin, so Chrome/Edge allow the mic. Speech output uses the built-in browser voices.

---

## 2. What is implemented (mapped to the brief)

| Requirement in the mail | Status | Where |
|---|---|---|
| Real-time voice: STT + TTS | ✅ Working | Browser `SpeechRecognition` + `speechSynthesis` in `static/app.js` |
| Contextual memory | ✅ Working | Full transcript + slots per session, persisted in SQLite (`crm.py`) |
| Multilingual communication | ✅ Working | Language selector, Hindi/Spanish intent vocabularies and localized replies |
| Lead qualification | ✅ Working | Deterministic BANT scoring, 0–100, HOT/WARM/COLD (`nlp.py`, `agent.py`) |
| Sentiment analysis | ✅ Working | Multilingual lexicon with negation handling and live sparkline (`nlp.py`) |
| RAG knowledge retrieval | ✅ Working | TF-IDF over 4 markdown docs, source-cited answers (`rag.py`, `knowledge/`) |
| Appointment booking + CRM | ✅ Working | Conflict-checked SQLite booking; lead + appointment tables (`crm.py`) |
| Call summary + insights | ✅ Working | Extractive summary, facts, BANT insight, next action (`agent.py`) |
| End-to-end workflow | ✅ Working | Six-turn demo script + 5 automated tests |
| Architecture diagram | ✅ | `docs/architecture.svg` and `docs/architecture.mmd` |
| 1-page report | ✅ | `REPORT.md` (also served at `/report`) |
| Scale to 1,00,000 users | ✅ Design | `REPORT.md` §5, `docs/architecture.svg` lower band |
| Security, deployment, cost | ✅ Design | `REPORT.md` §6–7 |

---

## 3. Project structure

```
fortivex-voice-agent/
├── app.py                  # entry point → python3 app.py
├── README.md               # this file
├── REPORT.md               # required 1-page report
├── requirements.txt        # intentionally empty: standard library only
├── run.sh / run.bat        # launchers
├── voice_agent/
│   ├── config.py           # paths, ports, BANT weights, languages
│   ├── nlp.py              # normalize, language, sentiment, intents, slots, BANT
│   ├── rag.py              # markdown loader + TF-IDF retriever
│   ├── crm.py              # SQLite leads / appointments / messages / summaries
│   ├── agent.py            # state machine, qualification, booking, summary
│   └── server.py           # JSON API + static/docs serving
├── static/                 # index.html, style.css, app.js (the UI)
├── knowledge/              # product.md, pricing.md, integrations.md, security.md
├── docs/                   # architecture.svg, architecture.mmd
├── tests/test_workflow.py  # 5 end-to-end tests
└── data/crm.db             # created on first run (demo data)
```

---

## 4. How a turn works

```
speech → browser STT → POST /api/message
  → detect language → sentiment → extract slots → recompute BANT score
  → upsert lead in CRM → detect intents → RAG lookup (if a question)
  → state machine chooses reply → save transcript → JSON back to UI
  → browser TTS speaks the reply → dashboard updates score/sentiment/sources
```

**Stages:** `GREETING → DISCOVERY/QUALIFYING → PRESENTING → SCHEDULING → CLOSED`.

**BANT scoring:** Budget 25 (parsed ₹ amounts, e.g. "2 lakhs" → 200000), Authority 25 (decision-maker / influencer), Need 25, Timeline 25 (weeks/months → days). 70+ = HOT, 40+ = WARM, else COLD.

---

## 5. API reference

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Dashboard UI |
| POST | `/api/session` `{lang}` | Start a call, returns `session_id` + greeting |
| POST | `/api/message` `{session_id,text,lang}` | One conversation turn, returns reply + all live state |
| POST | `/api/book` `{session_id,date,time}` | Book an appointment in the CRM |
| POST | `/api/end` `{session_id}` | Generate summary + insights |
| GET | `/api/leads` | List CRM leads (integration proof) |
| GET | `/api/knowledge` | List indexed RAG chunks |
| POST | `/api/reset` | Clear demo data |
| GET | `/api/health`, `/report`, `/readme` | Health + docs |

---

## 6. Tests

```bash
python3 -m unittest discover -s tests -v
```

Covers the full workflow, double-booking prevention, multilingual/sentiment behaviour, slot+BANT extraction and RAG ranking.

---

## 7. What is deliberately simplified, and the production path

| Prototype | Production upgrade |
|---|---|
| Browser speech | Telephony (Twilio/SIP) media stream → self-hosted Whisper / contracted STT-TTS |
| Regex intent + slot rules | Fine-tuned classifier / LLM function calling with schema validation |
| TF-IDF over markdown | Embeddings + pgvector / Pinecone, hybrid search, reranking |
| SQLite on localhost | Managed PostgreSQL (tenant-partitioned), Redis for session state |
| In-process session dict | Stateless workers + Redis TTL, queue for long-running jobs |
| Lexicon sentiment | Trained multilingual sentiment model |
| Local UI | React dashboard + auth, RBAC, audit logs |

These are design decisions, not missing homework: the prototype demonstrates each workflow with transparent, debuggable code and the report explains the scale-out.

---

## 8. Troubleshooting

- **No audio / mic blocked** — use Chrome or Edge on `http://127.0.0.1:8765`, allow the mic, or type instead.
- **No voice heard** — check system volume and that the "Speak replies" checkbox is on; browser voices vary by OS.
- **Port busy** — edit `PORT` in `voice_agent/config.py`.
- **Fresh demo** — click **Reset demo** or `POST /api/reset`.

---

## 9. Putting it on GitHub

```bash
git init
git add .
git commit -m "Fortivex AI autonomous sales voice agent - MVP"
git remote add origin https://github.com/<your-username>/<repo-name>.git
git branch -M main
git push -u origin main
```

The repository already contains `REPORT.md`, `README.md`, the architecture diagram, source and tests.

---

## 10. Interview talking points

- **Why rule-based NLP?** Deterministic, offline, explainable and fast to demo. It makes every decision debuggable live; the same interfaces accept an LLM later without changing the API.
- **Why RAG instead of fine-tuning?** Product facts change often; retrieval with citations updates by editing a markdown file and avoids hallucinations.
- **How is memory handled?** Per-session slots + full transcript in SQLite; production moves sessions to Redis with TTL and transcripts to Postgres.
- **How do you stop double bookings?** A unique date/time check on `CONFIRMED` appointments before insert, with a retry offering alternatives.
- **What is the business value?** Every inbound call is answered, qualified and followed up; sellers receive a scored brief instead of raw notes.
- **What would you build next?** Telephony connector, embedding-based RAG, CRM OAuth adapters, human handoff and a conversion analytics loop.
