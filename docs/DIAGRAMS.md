# Project diagrams — plain English

Every diagram below is Mermaid, so GitHub displays it automatically. Read them in order; together they explain the whole project.

---

## 1. The whole system in one picture

```mermaid
flowchart LR
  P["Prospect speaks"] --> MIC["Browser microphone"]
  MIC --> STT["Speech to text<br/>Web Speech API"]
  STT --> UI["Web page<br/>static/app.js"]
  UI --> API["Python server<br/>server.py"]
  API --> AGENT["Ava, the sales agent<br/>agent.py"]
  AGENT --> NLP["Understand<br/>nlp.py"]
  AGENT --> RAG["Find facts<br/>rag.py"]
  AGENT --> CRM["Save data<br/>crm.py"]
  RAG --> KB[(Knowledge files)]
  CRM --> DB[(SQLite database)]
  AGENT --> TTS["Text to speech"]
  TTS --> SPK["Browser speakers"]
  API --> DASH["Live dashboard<br/>score, mood, sources, booking"]
```

**In one line:** the browser turns speech into text, the agent decides what to say, and the browser turns the answer back into speech.

---

## 2. The business problem — before and after

```mermaid
flowchart LR
  subgraph BEFORE["Before"]
    B1["Customer calls"] --> B2["Nobody picks up"]
    B2 --> B3["Lead is lost"]
    B4["Someone picks up"] --> B5["Random questions"]
    B5 --> B6["CRM updated late or not at all"]
  end
  subgraph AFTER["After — with Ava"]
    A1["Customer calls"] --> A2["Ava answers instantly"]
    A2 --> A3["Qualifies: need, budget, authority, timeline"]
    A3 --> A4["Answers from approved knowledge"]
    A4 --> A5["Books a meeting"]
    A5 --> A6["Seller gets a scored summary"]
  end
```

**Why it matters:** no lead is wasted, every call is consistent, and the human seller starts with a brief instead of raw notes.

---

## 3. One call, step by step

```mermaid
sequenceDiagram
  participant C as Prospect
  participant B as Browser
  participant A as Agent
  participant K as Knowledge base
  participant D as CRM (SQLite)

  B->>A: Start call
  A-->>B: "Hi, I'm Ava. What are you trying to solve?"
  C->>B: "I need an AI receptionist"
  B->>A: Message + language
  A->>D: Save message, update lead
  A-->>B: "What budget have you set aside?"
  C->>B: "Around 2 lakhs, in 2 months"
  A->>A: Calculate BANT score = 75
  C->>B: "How much does it cost?"
  A->>K: Retrieve pricing answer
  K-->>A: Pricing chunk + source name
  A-->>B: Answer with citation
  C->>B: "Book tomorrow at 10 AM"
  A->>D: Check slot, write appointment
  A-->>B: "Confirmed. Thank you!"
  A->>D: Save summary and insights
```

---

## 4. What happens to a single message

```mermaid
flowchart TD
  M["Prospect sentence arrives as text"] --> L["1. Detect language"]
  L --> S["2. Analyse sentiment"]
  S --> F["3. Fill slots: name, need, budget, timeline, authority"]
  F --> Q["4. Recompute BANT score"]
  Q --> U["5. Save lead and message to CRM"]
  U --> I["6. Detect intent: greeting / price / feature / booking / objection"]
  I --> R{"Is it a question?"}
  R -->|Yes| RR["Retrieve knowledge, prepare citation"]
  R -->|No| ST["Skip retrieval"]
  RR --> DEC["7. State machine chooses the reply"]
  ST --> DEC
  DEC --> W["8. Save reply, return JSON"]
  W --> V["9. Browser speaks + dashboard updates"]
```

**Key idea:** every step is small, visible and testable. Nothing is hidden inside a black box.

---

## 5. The conversation follows a simple state machine

```mermaid
stateDiagram-v2
  [*] --> GREETING
  GREETING --> QUALIFYING: caller states a need
  QUALIFYING --> QUALIFYING: ask for missing BANT fields
  QUALIFYING --> PRESENTING: price or feature question
  PRESENTING --> SCHEDULING: offer meeting times
  QUALIFYING --> SCHEDULING: score is high enough
  SCHEDULING --> SCHEDULING: pick a time
  SCHEDULING --> CLOSED: caller confirms
  PRESENTING --> CLOSED: caller says goodbye
  CLOSED --> [*]
```

**Why states?** The agent always knows what it should ask next, so it never loops or forgets a question.

---

## 6. Lead qualification — BANT scoring

```mermaid
flowchart LR
  N["Need found<br/>+25"] --> T
  B["Budget parsed: 2 lakhs<br/>+25"] --> T
  A["Authority: founder<br/>+25"] --> T
  T["Timeline: 2 months<br/>+25"] --> SUM["Total = 100 / 100"]
  SUM --> G["Grade = HOT"]
  G --> NX["Next action: book a demo"]
```

| Field | Full points when… | Example from the demo |
|---|---|---|
| Budget | A number with currency or unit is spoken | "2 lakhs" → ₹200,000 |
| Authority | Caller says they decide | "I'm the founder" |
| Need | A use case is named | "AI receptionist" |
| Timeline | A period is spoken | "2 months" → 60 days |

70+ = HOT, 40–69 = WARM, below 40 = COLD.

---

## 7. How RAG answers a question

```mermaid
flowchart TD
  Q["User asks: Does it support Hindi and connect to our CRM?"] --> T["Turn into tokens, remove small words"]
  T --> E["Add synonyms: Hindi → language, multilingual"]
  E --> V["Compare with every knowledge chunk<br/>TF-IDF + cosine similarity"]
  V --> TOP["Top 2 chunks: integrations.md → CRM<br/>product.md → Languages"]
  TOP --> A["Join the chunks into one short spoken answer"]
  A --> C["Show the source names in the dashboard"]
```

**Why RAG instead of hard-coded answers?** Facts live in `knowledge/*.md`. Change a price by editing one line; the agent never needs retraining, and every answer can be traced to a source.

---

## 8. Data model — what is stored

```mermaid
erDiagram
  LEADS ||--o{ APPOINTMENTS : has
  LEADS ||--o{ MESSAGES : contains
  LEADS ||--o| CALL_SUMMARIES : produces
  LEADS {
    int id PK
    string session_id
    string name
    string company
    string need
    int budget
    string authority
    int score
    string grade
  }
  APPOINTMENTS {
    int id PK
    int lead_id FK
    string appt_date
    string appt_time
    string status
  }
  MESSAGES {
    int id PK
    string session_id
    string role
    string text
  }
  CALL_SUMMARIES {
    string session_id PK
    string summary
    string insights
  }
```

**Agenda check:** "contextual memory" = the MESSAGES table. "CRM integration" = the LEADS and APPOINTMENTS tables. A unique date+time check stops double bookings.

---

## 9. Scaling the same design to 1,00,000 users

```mermaid
flowchart LR
  PHONE["Phone / browser"] --> GW["Telephony gateway<br/>Twilio or SIP"]
  GW --> LB["Load balancer + TLS"]
  LB --> W1["App replica 1"]
  LB --> W2["App replica 2"]
  LB --> W3["App replica N"]
  W1 --> R[(Redis<br/>sessions + cache)]
  W1 --> PG[(PostgreSQL<br/>leads + appointments)]
  W1 --> V[(Vector DB<br/>knowledge embeddings)]
  W1 --> Q["Job queue<br/>summaries, CRM sync"]
  W1 --> OBS["Logs, metrics, alerts"]
```

**What changes, what stays:** the agent logic, BANT rules and conversation states stay exactly the same. Only the storage and speech layers are swapped for managed services. The app layer is stateless, so adding users means adding replicas.

---

## 10. How to run and present it

```mermaid
flowchart TD
  A["cd ~/Desktop/fortivex-voice-agent"] --> B["bash run.sh"]
  B --> C["Open http://127.0.0.1:8765"]
  C --> D{"How do you want to demo?"}
  D -->|Fastest| E["Click Run demo call"]
  D -->|Interactive| F["Click Start voice and speak"]
  D -->|No mic| G["Type a prospect reply"]
  E --> H["Books meeting + writes summary"]
  F --> H
  G --> H
  H --> I["Open REPORT.pdf and docs/architecture.svg"]
```

---

### Where each diagram lives in code

| Diagram | Code |
|---|---|
| Whole system | `voice_agent/server.py`, `agent.py` |
| Call steps | `voice_agent/agent.py` → `handle_message()` |
| State machine | `voice_agent/agent.py` → `_compose()` |
| BANT | `voice_agent/nlp.py` → `bant_score()` |
| RAG | `voice_agent/rag.py` → `KnowledgeBase` |
| Data | `voice_agent/crm.py` → `SCHEMA` |
| Scale | `REPORT.md` section 5 |
