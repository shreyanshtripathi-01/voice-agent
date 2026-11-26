"""Lightweight, dependency-free NLP helpers.

These are intentionally simple, deterministic and explainable. They are the
"working prototype" version of components that would be replaced with trained
models / LLMs at scale (see REPORT.md and docs/architecture.mmd).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, Iterable, List, Set, Tuple

# ---------------------------------------------------------------------------
# Text normalisation and language detection
# ---------------------------------------------------------------------------

_DEVANAGARI = re.compile(r"[\u0900-\u097F]")
_SPANISH_MARKERS = {"hola", "gracias", "necesito", "precio", "cita", "reunión", "sí", "bueno", "caro"}


def normalize(text: str) -> str:
    """Lowercase and strip accents so 'café' and 'cafe' match."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().strip()


def detect_language(text: str, hint: str = "en-IN") -> str:
    """Use the UI selection as the primary signal, with a script-based fallback."""
    if hint in {"en-IN", "en-US", "hi-IN", "es-ES"}:
        return hint
    if _DEVANAGARI.search(text or ""):
        return "hi-IN"
    if normalize(text) in _SPANISH_MARKERS or any(t in _SPANISH_MARKERS for t in normalize(text).split()):
        return "es-ES"
    return "en-IN"


# ---------------------------------------------------------------------------
# Sentiment: small multilingual lexicon (no model, fully offline)
# ---------------------------------------------------------------------------

_POSITIVE = {
    "good", "great", "excellent", "perfect", "interested", "interesting", "helpful",
    "useful", "amazing", "love", "impressed", "clear", "easy", "fast", "affordable",
    "excited", "works", "sure", "yes", "happy", "aachha", "accha", "badhiya",
    "shandaar", "pasand", "upayogi", "aasan", "sasta", "tej", "hain", "haan",
    "bueno", "excelente", "interesante", "util", "facil", "rapido", "barato", "claro", "si",
}
_NEGATIVE = {
    "bad", "worst", "expensive", "costly", "difficult", "hard", "confused", "slow",
    "issue", "problem", "worry", "worried", "concerned", "doubt", "useless", "later",
    "busy", "no", "not", "mahnga", "mahenga", "samasya", "chinta", "dhima", "kathin",
    "bhi", "vyast", "caro", "problema", "dificil", "lento", "preocupado", "despues", "ocupado",
}
_NEGATORS = {"not", "isnt", "dont", "doesnt", "never", "nahin", "nahi", "no", "nunca"}


def analyze_sentiment(text: str) -> Dict[str, object]:
    """Return polarity in [-1, 1] plus the words that drove the decision."""
    tokens = [t for t in re.findall(r"[\w\u0900-\u097F]+", normalize(text)) if t]
    pos = neg = 0
    drivers: List[str] = []
    for i, token in enumerate(tokens):
        negated = i > 0 and tokens[i - 1] in _NEGATORS
        if token in _POSITIVE:
            if negated:
                neg += 1
                drivers.append("not " + token)
            else:
                pos += 1
                drivers.append(token)
        elif token in _NEGATIVE and token not in _NEGATORS:
            if negated:
                pos += 1
                drivers.append("not " + token)
            else:
                neg += 1
                drivers.append(token)
    total = pos + neg
    score = round((pos - neg) / total, 2) if total else 0.0
    label = "positive" if score > 0.15 else "negative" if score < -0.15 else "neutral"
    return {"score": score, "label": label, "intensity": total, "drivers": drivers[:6]}


# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------

_INTENT_TERMS: Dict[str, Set[str]] = {
    "greeting": {"hello", "hi", "hey", "good", "morning", "afternoon", "namaste", "namaskar", "hola", "hy"},
    "price": {"price", "pricing", "cost", "costs", "how", "much", "rate", "rates", "fee", "budget", "afford", "keemat", "kitna", "precio", "costo"},
    "feature": {"feature", "features", "support", "support", "can", "does", "do", "integrate", "integration", "language", "hindi", "spanish", "multilingual", "knowledge", "rag", "crm", "appointment", "recording", "summary", "summarise", "summarize", "kya", "suvidha", "caracteristica", "funcion", "idioma"},
    "objection": {"expensive", "costly", "later", "busy", "doubt", "worried", "concerned", "already", "competitor", "mahnga", "mahenga", "bhi", "vyast", "chinta", "caro", "despues", "ocupado", "preocupado"},
    "schedule": {"book", "schedule", "meeting", "appointment", "demo", "tomorrow", "tuesday", "monday", "wednesday", "thursday", "friday", "slot", "available", "time", "apointment", "milna", "cita", "reunion"},
    "confirm": {"yes", "yeah", "sure", "ok", "okay", "perfect", "confirm", "please", "correct", "haan", "hain", "theek", "si", "claro", "bueno"},
    "reject": {"no", "nope", "cancel", "stop", "nahin", "nahi", "radd", "no", "nunca"},
    "goodbye": {"bye", "goodbye", "thanks", "thank", "see", "later", "dhanyavaad", "alvida", "gracias", "adios"},
    "authority": {"decide", "decision", "owner", "founder", "ceo", "boss", "approve", "approves", "manager", "head", "nirnay", "decido", "jefe"},
    "need": {"need", "looking", "want", "require", "problem", "challenge", "chahiye", "zarurat", "necesito", "necesitamos"},
}

# Order matters: stronger intents win when several match.
_INTENT_PRIORITY = (
    "reject", "confirm", "goodbye", "objection", "price", "schedule",
    "authority", "feature", "need", "greeting",
)


def detect_intents(text: str) -> Set[str]:
    """Return every intent whose vocabulary appears in the utterance."""
    tokens = set(re.findall(r"[\w\u0900-\u097F]+", normalize(text)))
    found = {name for name, terms in _INTENT_TERMS.items() if tokens & terms}
    return found


def primary_intent(text: str) -> str:
    intents = detect_intents(text)
    for name in _INTENT_PRIORITY:
        if name in intents:
            return name
    return "other"


# ---------------------------------------------------------------------------
# Slot filling (BANT fields) with transparent regex rules
# ---------------------------------------------------------------------------

_CURRENCY = {"₹": 1, "rs": 1, "inr": 1, "rupees": 1, "$": 83, "usd": 83, "euro": 90}
_MULTIPLIER = {"k": 1_000, "thousand": 1_000, "lakh": 100_000, "lakhs": 100_000,
               "lac": 100_000, "crore": 10_000_000, "cr": 10_000_000, "million": 1_000_000}

_NAME_RE = re.compile(r"(?:my name is|i am|i'm|this is|me llamo|soy|mera naam|main)\s+([^,.!?;]+)", re.I)
_COMPANY_RE = re.compile(r"(?:from|our company|we are from|company is|mi empresa|hamari company)\s+([^,.!?;]+)", re.I)
_AMOUNT_RE = re.compile(r"(₹|rs\.?|inr|rupees|\$|usd|euro)?\s*(\d+(?:\.\d+)?)\s*(lakhs|lakh|thousand|million|crore|lac|cr|k)?", re.I)
_PERIOD_RE = re.compile(r"(\d+)\s*(days|day|weeks|week|months|month|quarters|quarter)", re.I)
_ROLE_WORDS = ("founder", "owner", "ceo", "director", "manager", "head", "doctor", "clinic", "hospital", "startup", "sales", "hr", "teacher", "hotel", "restaurant")
_NEED_WORDS = ("receptionist", "sales", "support", "customer", "lead", "appointment", "multilingual", "bilingual", "clinic", "hospital", "ecommerce", "education", "real estate", "hotel", "restaurant", "call center")


def _clean_entity(raw: str) -> str:
    raw = re.split(r"[,.!?;]", raw)[0].strip()
    raw = re.split(r"\s+(?:from|who|looking|and)\s+", raw, maxsplit=1, flags=re.I)[0].strip()
    words = raw.split()
    stop = {"i", "we", "and", "the", "a", "an", "am", "is", "interested", "calling", "looking", "who", "from", "with", "please", "just", "my", "name", "im"}
    while words and words[-1].lower() in stop:
        words.pop()
    return " ".join(words[:4]).strip(" '\"-")


def extract_slots(text: str, current: Dict[str, object] | None = None) -> Dict[str, object]:
    """Extract BANT + identity fields. Only non-empty new values are returned."""
    slots: Dict[str, object] = dict(current or {})
    intents = detect_intents(text)

    m = _NAME_RE.search(text)
    if m and not slots.get("name"):
        name = _clean_entity(m.group(1))
        if 1 < len(name) < 40:
            slots["name"] = name

    m = _COMPANY_RE.search(text)
    if m and not slots.get("company"):
        company = _clean_entity(m.group(1))
        if 1 < len(company) < 60 and re.match(r"[A-Za-z\u0900-\u097F]{2,}", company):
            slots["company"] = company

    low = normalize(text)
    if not slots.get("role"):
        for word in _ROLE_WORDS:
            if word in low:
                slots["role"] = word
                break

    if not slots.get("need"):
        for word in _NEED_WORDS:
            if word in low:
                slots["need"] = word
                break

    # Budget: only treat a number as money if a currency marker or money word is nearby.
    money_context = bool(intents & {"price"}) or any(w in low for w in {"budget", "spend", "afford", "cost", "price", "rs", "inr", "lakh", "costly"})
    if money_context and not slots.get("budget_value"):
        m = _AMOUNT_RE.search(text)
        if m:
            symbol, number, unit = m.group(1), m.group(2), (m.group(3) or "").lower()
            multiplier = _MULTIPLIER.get(unit, 1)
            fx = _CURRENCY.get((symbol or "").lower().rstrip("."), 1)
            value = int(float(number) * multiplier * fx)
            if 0 < value < 1_000_000_000:
                slots["budget_value"] = value
                slots["budget_text"] = m.group(0).strip()

    if not slots.get("timeline_days"):
        m = _PERIOD_RE.search(text)
        if m:
            qty, unit = int(m.group(1)), m.group(2).lower()
            days = qty * {"day": 1, "week": 7, "month": 30, "quarter": 90}.get(unit.rstrip("s"), 30)
            slots["timeline_days"] = days
            slots["timeline_text"] = m.group(0)
        elif any(w in low for w in {"asap", "urgent", "immediately", "this week", "next week", "soon", "jaldi"}):
            slots["timeline_days"] = 7
            slots["timeline_text"] = "as soon as possible"

    if not slots.get("authority"):
        if "decision" in low or "i decide" in low or "i am the owner" in low or "i'm the owner" in low or "founder" in low or "ceo" in low:
            slots["authority"] = "decision-maker"
        elif "check with" in low or "my boss" in low or "approve" in low or "manager" in low:
            slots["authority"] = "influencer"

    return slots


def bant_score(slots: Dict[str, object]) -> Dict[str, object]:
    """Score the four BANT dimensions (0-25 each) and grade the lead."""
    budget = 25 if slots.get("budget_value") else 12 if slots.get("budget_text") else 0
    authority = 25 if slots.get("authority") == "decision-maker" else 12 if slots.get("authority") else 0
    need = 25 if slots.get("need") else 10 if slots.get("role") else 0
    days = slots.get("timeline_days")
    timeline = 25 if isinstance(days, int) and days <= 90 else 12 if slots.get("timeline_text") else 0
    parts = {"budget": budget, "authority": authority, "need": need, "timeline": timeline}
    total = sum(parts.values())
    grade = next(label for threshold, label in _grade_thresholds() if total >= threshold)
    return {"parts": parts, "total": total, "grade": grade}


def _grade_thresholds() -> Iterable[Tuple[int, str]]:
    from .config import GRADE_THRESHOLDS
    return GRADE_THRESHOLDS
