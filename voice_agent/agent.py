"""The sales agent: conversation state machine, qualification, RAG, booking and summary."""

from __future__ import annotations

import re
import uuid
from datetime import date
from typing import Dict, List, Optional, Tuple

from . import crm
from .config import STAGES
from .nlp import (analyze_sentiment, bant_score, detect_intents, detect_language,
                  extract_slots, normalize)
from .rag import KnowledgeBase

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "to", "of", "in", "on", "for", "with", "is", "are",
    "was", "we", "i", "you", "it", "this", "that", "our", "my", "your", "have", "has", "need",
    "want", "would", "could", "should", "do", "does", "did", "please", "just", "about", "like",
    "from", "at", "by", "so", "if", "not", "yes", "hi", "hello", "thanks",
}

_QUESTIONS = (
    "how much", "what is", "whats", "what's", "do you", "does it", "can it", "can you",
    "does your", "tell me", "is it", "are you", "kya", "kitna", "kaise", "cuanto", "puede",
)


def _money(value: Optional[int]) -> str:
    if not value:
        return "not specified"
    digits = str(int(value))
    if len(digits) <= 3:
        return "₹" + digits
    head, tail = digits[:-3], digits[-3:]
    parts = []
    while head:
        parts.append(head[-2:])
        head = head[:-2]
    return "₹" + ",".join(reversed(parts)) + "," + tail


class SalesAgent:
    """One instance serves many concurrent calls; each call is an isolated session."""

    def __init__(self) -> None:
        crm.init_db()
        self.kb = KnowledgeBase()
        self.sessions: Dict[str, Dict] = {}

    # ------------------------------------------------------------------ session
    def start_session(self, lang: str = "en-IN") -> Dict:
        sid = uuid.uuid4().hex[:10]
        greeting = {
            "hi-IN": "नमस्ते! मैं Fortivex AI की Ava हूँ। बताइए, आप किस समस्या का हल ढूंढ रहे हैं?",
            "es-ES": "¡Hola! Soy Ava, de Fortivex AI. ¿Qué problema está intentando resolver?",
        }.get(lang, "Hi! I'm Ava from Fortivex AI. Thanks for taking the call. What are you trying to solve today?")

        self.sessions[sid] = {
            "id": sid,
            "language": lang,
            "stage": "GREETING",
            "slots": {},
            "qualification": bant_score({}),
            "sentiment_history": [],
            "sources": [],
            "turns": [],
            "lead_id": None,
            "appointment": None,
            "selected_slot": None,
            "offered_slots": crm.list_available_slots(),
            "lookups": 0,
        }
        crm.save_message(sid, "agent", greeting, lang)
        return {"ok": True, "session_id": sid, "message": greeting,
                "stage": "GREETING", "language": lang}

    def get_session(self, sid: str) -> Optional[Dict]:
        return self.sessions.get(sid)

    # ------------------------------------------------------------------ message
    def handle_message(self, sid: str, text: str, lang_hint: str = "") -> Dict:
        s = self.sessions.get(sid)
        if not s:
            return {"ok": False, "error": "Unknown session. Start a new call first."}
        text = (text or "").strip()
        if not text:
            return {"ok": False, "error": "Please say or type something."}

        lang = detect_language(text, lang_hint or s["language"])
        s["language"] = lang
        sentiment = analyze_sentiment(text)
        s["sentiment_history"].append(sentiment["score"])
        s["slots"] = extract_slots(text, s["slots"])
        s["qualification"] = bant_score(s["slots"])
        s["lead_id"] = crm.upsert_lead(sid, s["slots"], s["qualification"], sentiment["label"], lang)

        intents = detect_intents(text)
        reply, stage = self._compose(s, text, intents)
        s["stage"] = stage
        s["turns"].append({"role": "user", "text": text, "intents": sorted(intents)})
        s["turns"].append({"role": "agent", "text": reply})
        crm.save_message(sid, "user", text, lang)
        crm.save_message(sid, "agent", reply, lang)

        return {
            "ok": True,
            "message": reply,
            "stage": stage,
            "language": lang,
            "intent": " / ".join(sorted(intents)) or "other",
            "slots": s["slots"],
            "qualification": s["qualification"],
            "sentiment": sentiment,
            "sentiment_history": s["sentiment_history"],
            "sources": s["sources"][-3:],
            "appointment": s["appointment"],
            "suggested_slots": crm.list_available_slots()[:4] if stage == "SCHEDULING" else [],
            "turn_count": len(s["turns"]) // 2,
        }

    # ------------------------------------------------------------------ booking
    def book(self, sid: str, appt_date: str = "", appt_time: str = "") -> Dict:
        s = self.sessions.get(sid)
        if not s:
            return {"ok": False, "error": "Unknown session."}
        slot = s.get("selected_slot") or {"date": appt_date, "time": appt_time}
        if not slot.get("date") or not slot.get("time"):
            slot = s["offered_slots"][0] if s["offered_slots"] else {"date": "", "time": ""}
        result = crm.book_appointment(s["lead_id"], slot["date"], slot["time"])
        if result["ok"]:
            s["appointment"] = result
            s["stage"] = "CLOSED"
            s["selected_slot"] = slot
            reply = self._closing_message(s)
            crm.save_message(sid, "agent", reply, s["language"])
            return {"ok": True, "message": reply, "appointment": result, "stage": "CLOSED"}
        return {"ok": False, "error": result["reason"], "suggested_slots": crm.list_available_slots()[:4]}

    # ------------------------------------------------------------------ summary
    def end_call(self, sid: str) -> Dict:
        s = self.sessions.get(sid)
        if not s:
            return {"ok": False, "error": "Unknown session."}
        messages = crm.get_messages(sid)
        prospect = [m["text"] for m in messages if m["role"] == "user"]
        summary = self._extractive_summary(prospect)
        slots, q = s["slots"], s["qualification"]
        facts = {
            "prospect": slots.get("name") or "Not captured",
            "company": slots.get("company") or "Not captured",
            "role": slots.get("role") or "Not captured",
            "need": slots.get("need") or "Not captured",
            "budget": _money(slots.get("budget_value")) if slots.get("budget_value") else (slots.get("budget_text") or "Not captured"),
            "timeline": slots.get("timeline_text") or "Not captured",
            "authority": slots.get("authority") or "Not captured",
        }
        sentiment_label = self._overall_sentiment(s["sentiment_history"])
        negatives = [t["text"] for t in s["turns"] if t["role"] == "user" and "objection" in t.get("intents", [])]
        appointment = s["appointment"]
        next_step = (f"Confirmed demo on {appointment['date']} at {appointment['time']}"
                     if appointment else "Send follow-up email and book a 15-minute demo")
        insights = [
            f"{q['grade']} lead — {q['total']}/100 on BANT (Budget {q['parts']['budget']}, "
            f"Authority {q['parts']['authority']}, Need {q['parts']['need']}, Timeline {q['parts']['timeline']}).",
            f"Prospect sentiment: {sentiment_label} across {len(s['sentiment_history'])} turns. "
            f"{len(negatives)} objection(s) handled.",
            f"Fit: {facts['need']} use case, budget {facts['budget']}, timeline {facts['timeline']}.",
            f"Knowledge base consulted {s['lookups']} time(s); answers were source-cited.",
            f"Recommended next action: {next_step}.",
        ]
        crm.save_summary(sid, summary, "\n".join(insights))
        s["stage"] = "CLOSED"
        return {"ok": True, "summary": summary, "insights": insights, "facts": facts,
                "qualification": q, "appointment": appointment, "language": s["language"]}

    # ------------------------------------------------------------------ internal
    def _compose(self, s: Dict, text: str, intents: set) -> Tuple[str, str]:
        low = normalize(text)
        lang = s["language"]
        is_question = "?" in text or low.startswith(_QUESTIONS)
        score = s["sentiment_history"][-1] if s["sentiment_history"] else 0.0

        # A caller naming a time slot gets it reserved in-memory, then confirmation books it.
        requested = self._parse_requested_slot(text, s["offered_slots"])
        if requested:
            s["selected_slot"] = requested
            return (self._ack(lang, score) + f" {requested['date']} at {requested['time']} works. "
                    "Should I put that on the calendar?", "SCHEDULING")

        if "confirm" in intents:
            if s.get("selected_slot"):
                result = crm.book_appointment(s["lead_id"], s["selected_slot"]["date"], s["selected_slot"]["time"])
                if result["ok"]:
                    s["appointment"] = result
                    return self._closing_message(s), "CLOSED"
                s["selected_slot"] = None
                return self._ack(lang, score) + " That slot just got taken. " + self._offer(s), "SCHEDULING"
            if "schedule" in intents and s["offered_slots"]:
                s["selected_slot"] = s["offered_slots"][0]
                return (self._ack(lang, score) + " I've held " + self._slot_label(s["selected_slot"])
                        + ". Shall I confirm it?", "SCHEDULING")

        if "goodbye" in intents:
            return self._closing_message(s), "CLOSED"

        if "reject" in intents:
            return (self._ack(lang, score) + " No problem at all. If it helps, I can send a two-line summary "
                    "to your email instead of a meeting. Would that be useful?"), "PRESENTING"

        if is_question and ("price" in intents or "feature" in intents):
            answer = self.kb.best_answer(text)
            s["sources"] = self.kb.retrieve(text, top_k=2)
            s["lookups"] += 1
            if answer:
                return (self._ack(lang, score) + " " + answer + " " + self._soft_close(s)), "PRESENTING"
            return (self._ack(lang, score) + " I don't have that exact detail in my knowledge base, "
                    "but I can have a specialist cover it in a short demo. " + self._soft_close(s)), "PRESENTING"

        if "objection" in intents:
            return (self._ack(lang, score) + " I understand. Most teams feel that way before they see the "
                    "time saved per call. A 15-minute demo usually answers that in minutes. "
                    + self._offer(s)), "SCHEDULING"

        if "schedule" in intents:
            s["stage"] = "SCHEDULING"
            return self._ack(lang, score) + " Happy to set that up. " + self._offer(s), "SCHEDULING"

        missing = self._next_missing(s["slots"])
        if missing:
            return self._ack(lang, score) + " " + missing, "QUALIFYING"

        if s["stage"] != "SCHEDULING":
            return (self._ack(lang, score) + " That gives me a clear picture. We can support that with "
                    "real-time voice, multilingual answers and CRM write-back. " + self._offer(s)), "SCHEDULING"

        return self._ack(lang, score) + " " + self._offer(s), "SCHEDULING"

    def _ack(self, lang: str, score: float = 0.0) -> str:
        if lang == "hi-IN":
            return "बहुत अच्छा।" if score > 0.15 else "समझ गया।"
        if lang == "es-ES":
            return "¡Me alegra!" if score > 0.15 else "Entendido."
        if score > 0.15:
            return "Great to hear that."
        if score < -0.15:
            return "I understand."
        return "Got it."

    def _next_missing(self, slots: Dict) -> Optional[str]:
        if not slots.get("need"):
            return "What would you most like the agent to handle — sales calls, reception, or customer support?"
        if not slots.get("role"):
            return "And what's your role, so I know who I'm speaking with?"
        if not slots.get("budget_value"):
            return "Roughly what budget have you set aside for this?"
        if not slots.get("timeline_days"):
            return "When would you like to go live — this month, next quarter, or sooner?"
        if not slots.get("authority"):
            return "Are you the person who makes the final decision on this?"
        if not slots.get("name"):
            return "May I know your name for the follow-up?"
        if not slots.get("company"):
            return "And your company name?"
        return None

    def _offer(self, s: Dict) -> str:
        slots = s["offered_slots"][:3]
        if not slots:
            return "Would you like a 15-minute demo this week?"
        options = ", ".join(f"{d['date']} at {d['time']}" for d in slots)
        return f"I have {options}. Which works for you?"

    def _soft_close(self, s: Dict) -> str:
        return self._offer(s) if s["qualification"]["total"] >= 40 else \
            "Happy to send a short overview if that's easier."

    def _slot_label(self, slot: Dict) -> str:
        return f"{slot['date']} at {slot['time']}"

    def _closing_message(self, s: Dict) -> str:
        appt = s.get("appointment") or s.get("selected_slot")
        if appt:
            return (self._ack(s["language"]) + " Your demo is confirmed for "
                    + self._slot_label(appt) + ". I'll log the call and send the summary. Thank you!")
        return (self._ack(s["language"]) + " Thanks for the conversation. I've logged the key points "
                "and our team will follow up shortly.")

    def _parse_requested_slot(self, text: str, offered: List[Dict]) -> Optional[Dict]:
        if "schedule" not in detect_intents(text) and "confirm" not in detect_intents(text):
            return None
        low = normalize(text)
        hour_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", low)
        day_match = re.search(r"tomorrow|today|monday|tuesday|wednesday|thursday|friday|next week", low)
        if not hour_match and not day_match:
            return None
        candidates = list(offered)
        if day_match:
            word = day_match.group(0)
            if word in {"tomorrow", "today"}:
                target = date.today().toordinal() + (0 if word == "today" else 1)
                candidates = [c for c in candidates if date.fromisoformat(c["date"]).toordinal() == target]
            elif word != "next week":
                weekday = ["monday", "tuesday", "wednesday", "thursday", "friday"].index(word)
                candidates = [c for c in candidates if date.fromisoformat(c["date"]).weekday() == weekday]
        if hour_match:
            hour = int(hour_match.group(1))
            minute = int(hour_match.group(2) or 0)
            if "pm" in low and hour < 12:
                hour += 12
            label = f"{hour:02d}:{minute:02d}"
            candidates = [c for c in candidates if c["time"] == label]
        return candidates[0] if candidates else None

    def _extractive_summary(self, sentences: List[str]) -> str:
        if not sentences:
            return "No prospect statements were recorded in this call."
        pieces = [p.strip() for s in sentences for p in re.split(r"(?<=[.!?])\s+", s) if p.strip()]
        words = [w for p in pieces for w in re.findall(r"[\w']+", p.lower()) if w not in _STOPWORDS and len(w) > 2]
        freq: Dict[str, int] = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1
        scored = []
        for piece in pieces:
            tokens = [w for w in re.findall(r"[\w']+", piece.lower()) if w in freq]
            score = sum(freq[w] for w in tokens) / (len(tokens) + 3) ** 0.5
            scored.append((score, piece))
        top = sorted(scored, key=lambda x: x[0], reverse=True)[:3]
        chosen = {p for _, p in top}
        return " ".join(p for p in pieces if p in chosen)

    @staticmethod
    def _overall_sentiment(history: List[float]) -> str:
        if not history:
            return "neutral"
        avg = sum(history) / len(history)
        return "positive" if avg > 0.15 else "negative" if avg < -0.15 else "neutral"
