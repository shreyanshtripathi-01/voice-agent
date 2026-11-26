#!/usr/bin/env python3
"""Dev-only: draw a detailed, simple-language explainer PDF with many diagrams.

Uses Pillow (already installed). The application itself still has no dependencies.
Run: python3 tools/make_explainer_pdf.py
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "EXPLAINER.pdf"
PREVIEW = Path("/tmp/opencode/pdfpages")
PREVIEW.mkdir(parents=True, exist_ok=True)

W, H, M = 1240, 1754, 70
CW = W - 2 * M

FONT_DIR = Path("/usr/share/fonts/gsfonts")
REG = str(FONT_DIR / "NimbusSans-Regular.otf")
BOLD = str(FONT_DIR / "NimbusSans-Bold.otf")

F = {
    "h1": ImageFont.truetype(BOLD, 43),
    "h2": ImageFont.truetype(BOLD, 28),
    "h3": ImageFont.truetype(BOLD, 22),
    "body": ImageFont.truetype(REG, 21),
    "small": ImageFont.truetype(REG, 18),
    "tiny": ImageFont.truetype(REG, 15),
    "bsmall": ImageFont.truetype(BOLD, 18),
}

BG = (250, 250, 248)
TEXT = (26, 26, 26)
MUTED = (105, 105, 105)
LINE = (220, 220, 214)
BLUE = (37, 99, 235)
PALE_BLUE = (236, 243, 255)
PALE_GREEN = (236, 247, 239)
PALE_GRAY = (243, 243, 240)
GREEN = (21, 128, 61)
AMBER = (180, 83, 9)


class Page:
    def __init__(self, title: str, subtitle: str = ""):
        self.img = Image.new("RGB", (W, H), BG)
        self.d = ImageDraw.Draw(self.img)
        self.d.text((M, 32), "FORTIVEX AI  /  PROJECT EXPLAINED", font=F["tiny"], fill=MUTED)
        self.d.text((M, 60), title, font=F["h1"], fill=TEXT)
        if subtitle:
            self.d.text((M, 118), subtitle, font=F["body"], fill=MUTED)
        self.d.line([(M, 162), (W - M, 162)], fill=LINE, width=2)

    def finish(self, number: int) -> Image.Image:
        self.d.line([(M, H - 78), (W - M, H - 78)], fill=LINE, width=1)
        self.d.text((M, H - 62), "Fortivex AI — Autonomous Sales Voice Agent", font=F["tiny"], fill=MUTED)
        self.d.text((W - M - 60, H - 62), str(number), font=F["tiny"], fill=MUTED)
        return self.img

    def text(self, x: int, y: int, value: str, key: str = "body", fill=TEXT) -> int:
        self.d.text((x, y), value, font=F[key], fill=fill)
        return y + int(F[key].size * 1.35)

    def para(self, x: int, y: int, value: str, key: str = "body", width: int = CW, gap: int = 9) -> int:
        font = F[key]
        words = value.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = (current + " " + word).strip()
            if self.d.textlength(candidate, font=font) <= width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        for line in lines:
            self.d.text((x, y), line, font=font, fill=TEXT)
            y += font.size + gap
        return y

    def arrow(self, x1: int, y1: int, x2: int, y2: int, color=BLUE, width: int = 3) -> None:
        self.d.line([(x1, y1), (x2, y2)], fill=color, width=width)
        angle = math.atan2(y2 - y1, x2 - x1)
        size = 12
        p1 = (x2 - size * math.cos(angle - 0.5), y2 - size * math.sin(angle - 0.5))
        p2 = (x2 - size * math.cos(angle + 0.5), y2 - size * math.sin(angle + 0.5))
        self.d.polygon([(x2, y2), p1, p2], fill=color)

    def circle_num(self, x: int, y: int, number: str, color=TEXT) -> None:
        self.d.ellipse([x, y, x + 34, y + 34], fill=color)
        self.d.text((x + 10, y + 4), number, font=F["bsmall"], fill=(255, 255, 255))

    def box(self, x: int, y: int, w: int, h: int, title: str, lines: list[str],
            fill=(255, 255, 255), outline=LINE, title_color=TEXT) -> None:
        self.d.rounded_rectangle([x, y, x + w, y + h], radius=12, fill=fill, outline=outline, width=2)
        self.d.text((x + 16, y + 13), title, font=F["h3"], fill=title_color)
        for i, line in enumerate(lines):
            self.d.text((x + 16, y + 48 + i * 26), line, font=F["small"], fill=MUTED)

    def note(self, y: int, text: str, fill=PALE_GRAY) -> int:
        self.d.rounded_rectangle([M, y, W - M, y + 90], radius=10, fill=fill, outline=LINE, width=1)
        self.para(M + 20, y + 18, text, key="small", width=CW - 40, gap=4)
        return y + 105


def page1() -> Image.Image:
    p = Page("Autonomous AI Sales Voice Agent", "A plain-English explanation, with one diagram per idea")
    y = p.para(M, 200,
        "Sales teams lose leads when nobody answers the phone, when questions are asked differently every time, "
        "and when the CRM is updated late or not at all. This project builds an AI sales agent named Ava that "
        "answers instantly, qualifies the caller, finds answers in company documents, books a meeting and hands "
        "a short brief to a human seller. It runs on one laptop, costs nothing, and has no API keys.")
    y += 20
    p.box(70, 380, 200, 110, "Prospect", ["Speaks or types"])
    p.box(330, 380, 250, 110, "Browser", ["Mic, speakers", "and the web page"])
    p.box(650, 380, 250, 110, "Ava (agent)", ["Understands and", "decides what to say"])
    p.box(970, 380, 200, 110, "Knowledge", ["+ CRM database"])
    p.arrow(272, 435, 326, 435)
    p.arrow(582, 435, 646, 435)
    p.arrow(902, 435, 966, 435)
    p.box(330, 550, 590, 90, "The answer comes back", ["Spoken aloud by the browser; dashboard updates live"], fill=PALE_BLUE)
    p.arrow(775, 492, 625, 545)
    p.text(M, 690, "Ava has three jobs", "h2")
    p.box(70, 750, 350, 150, "1. Listen", ["Speech becomes text", "in the browser"], fill=PALE_BLUE)
    p.box(445, 750, 350, 150, "2. Understand", ["Intent, needs, mood", "and lead score"], fill=PALE_GRAY)
    p.box(820, 750, 350, 150, "3. Act", ["Answer, book time,", "write a summary"], fill=PALE_GREEN)
    p.note(960, "Everything is local: Python standard library, SQLite, and the browser's own speech tools. "
                "No paid service, no model download, no account needed.")
    return p.finish(1)


def page2() -> Image.Image:
    p = Page("The problem, and the idea", "Why a business would pay for this")
    p.para(M, 200,
        "A small business cannot staff a sales phone 24 hours a day. When someone does answer, the questions "
        "are rarely the same, so the lead is judged differently each time. Later, somebody may remember to "
        "type the details into the CRM. The result: lost interest, messy data, and a seller who starts the "
        "follow-up with no context.")
    p.box(70, 380, 510, 700, "BEFORE", [
        "Customer calls", "        ↓", "Nobody picks up", "        ↓", "Lead is lost", "",
        "Or someone picks up", "        ↓", "Random questions", "        ↓", "CRM updated late",
        "        ↓", "Seller has no brief",
    ], fill=PALE_GRAY)
    p.box(660, 380, 510, 700, "AFTER — with Ava", [
        "Customer calls", "        ↓", "Ava answers instantly", "        ↓",
        "Qualifies need, budget,", "authority and timeline", "        ↓",
        "Answers from approved", "company documents", "        ↓", "Books a meeting", "        ↓",
        "Seller receives a scored", "call summary",
    ], fill=PALE_GREEN)
    p.note(1130, "Commercial sense: 200 small customers on the Rs. 1.5 lakh/year plan is Rs. 30 lakh of yearly "
                 "revenue. The computer cost per call is only a few cents, so the margin stays high.")
    p.note(1250, "The upgrades (more languages, private documents, CRM connectors) are natural upsells. "
                 "The pilot itself is free because it uses open tools.")
    return p.finish(2)


def page3() -> Image.Image:
    p = Page("One call, six steps", "This is the exact demo you will show")
    steps = [
        ("Greeting", "Ava introduces herself and asks what the caller needs."),
        ("Discovery", "Caller says: 'I need an AI receptionist.' Ava notes the need."),
        ("Qualification", "Caller gives budget (2 lakhs) and timeline (2 months), then says 'I am the founder.' Score = 100, grade HOT."),
        ("Knowledge question", "Caller asks about Hindi and CRM. Ava retrieves two fact pages and names the source."),
        ("Booking", "Caller says 'book tomorrow at 10 AM'. Ava checks the slot and asks for confirmation."),
        ("Summary", "After 'yes, confirm', the appointment is saved and a summary with insights is written."),
    ]
    y = 200
    for i, (title, detail) in enumerate(steps, 1):
        p.box(70, y, 1100, 110, "", [], fill=(255, 255, 255))
        p.circle_num(90, y + 34, str(i))
        p.text(150, y + 18, title, "h3")
        p.para(150, y + 52, detail, key="small", width=980, gap=2)
        if i < 6:
            p.arrow(620, y + 112, 620, y + 138, color=LINE, width=2)
        y += 145
    p.box(70, 1090, 1100, 300, "Example conversation", [
        "Caller: Hello, I'm Rabia from Shree Clinic. We need an AI receptionist.",
        "Ava:   Got it. Roughly what budget have you set aside for this?",
        "Caller: Around 2 lakhs a year, and we want to go live in 2 months.",
        "Ava:   Are you the person who makes the final decision?",
        "Caller: I'm the founder. Also, does it support Hindi and connect to our CRM?",
        "Ava:   Yes — here is the answer from our documents. Which demo time works?",
    ], fill=PALE_BLUE)
    p.note(1430, "In the browser, click 'Run demo call'. It plays all six steps by itself, speaks every reply, "
                 "books the meeting and writes the summary — no microphone needed.")
    return p.finish(3)


def page4() -> Image.Image:
    p = Page("One message, nine small steps", "What happens between a caller speaking and Ava replying")
    steps = [
        ("Detect the language", "The chosen language (or the script used) tells Ava which words to expect."),
        ("Read the mood", "Words like 'excellent' or 'too expensive' move a sentiment score up or down."),
        ("Fill in the blanks", "Regex rules pull out name, company, need, budget, timeline and authority."),
        ("Score the lead", "Budget, Authority, Need and Timeline earn 25 points each: 0 to 100."),
        ("Save to CRM", "The message and the updated lead are written to SQLite immediately."),
        ("Find the intent", "Ava decides: is this a greeting, a price question, an objection, a booking?"),
        ("Look up facts if needed", "Questions trigger the knowledge search; answers carry a source name."),
        ("Choose the reply", "The state machine picks the next question, answer or booking step."),
        ("Speak and update", "The reply is spoken and the dashboard refreshes: score, mood, sources, meeting."),
    ]
    y = 195
    for i, (title, detail) in enumerate(steps, 1):
        p.box(70, y, 1100, 125, "", [], fill=(255, 255, 255))
        p.circle_num(92, y + 38, str(i))
        p.text(152, y + 16, title, "h3")
        p.para(152, y + 54, detail, key="small", width=985, gap=2)
        if i < 9:
            p.arrow(620, y + 127, 620, y + 148, color=LINE, width=2)
        y += 155
    return p.finish(4)


def page5() -> Image.Image:
    p = Page("The five brains of Ava", "Each part is small, visible and easy to change")
    p.box(70, 200, 350, 240, "1. Voice", ["Browser turns speech", "into text (STT) and", "text back into speech", "(TTS). Free."], fill=PALE_BLUE)
    p.box(445, 200, 350, 240, "2. Memory", ["Every message and", "every extracted detail", "is stored in SQLite,", "so nothing is forgotten."], fill=PALE_GRAY)
    p.box(820, 200, 350, 240, "3. Qualification", ["BANT: four questions,", "25 points each.", "Shows HOT / WARM / COLD", "live while talking."], fill=PALE_GREEN)
    p.box(250, 480, 350, 240, "4. Sentiment", ["A tiny word list detects", "positive and negative", "mood, even in Hindi", "and Spanish."], fill=PALE_GRAY)
    p.box(620, 480, 350, 240, "5. Knowledge", ["Company fact pages are", "searched by similarity.", "Answers include the", "source file and section."], fill=PALE_BLUE)

    p.text(M, 770, "BANT scoring, with real demo numbers", "h2")
    bars = [
        ("Budget", "2 lakhs spoken", 25),
        ("Authority", "founder / owner", 25),
        ("Need", "AI receptionist", 25),
        ("Timeline", "2 months", 25),
    ]
    y = 840
    for label, why, value in bars:
        p.text(75, y, label, "bsmall")
        p.text(280, y, why, "small", fill=MUTED)
        p.d.rounded_rectangle([520, y + 2, 920, y + 22], radius=8, fill=(235, 235, 231))
        p.d.rounded_rectangle([520, y + 2, 520 + int(400 * value / 25), y + 22], radius=8, fill=GREEN)
        p.text(940, y, f"+{value}", "bsmall", fill=GREEN)
        y += 55
    p.box(70, 1090, 1100, 110, "Total: 100 / 100  →  HOT lead  →  book a demo now", [], fill=PALE_GREEN)
    p.box(70, 1240, 1100, 190, "Sentiment example", [
        "'This is excellent and very helpful'  →  positive (+0.67)",
        "'It is too expensive and I am worried'  →  negative (-0.50)",
        "The little sparkline on the dashboard shows how the mood moves during the call.",
    ], fill=PALE_GRAY)
    return p.finish(5)


def page6() -> Image.Image:
    p = Page("RAG: how the answers stay correct", "Retrieval-Augmented Generation, explained simply")
    items = [
        ("Caller asks a question", "\"Does it support Hindi and connect to our CRM?\""),
        ("Split into meaningful words", "hindi, support, connect, crm, language"),
        ("Compare with every knowledge chunk", "Small math (TF-IDF + cosine) scores similarity"),
        ("Keep the two best chunks", "integrations.md → CRM; product.md → Languages"),
        ("Answer with the sources shown", "One short spoken answer + visible citations"),
    ]
    y = 200
    for i, (title, detail) in enumerate(items, 1):
        p.box(220, y, 800, 105, f"{i}. {title}", [detail], fill=PALE_BLUE if i % 2 else (255, 255, 255))
        if i < 5:
            p.arrow(620, y + 107, 620, y + 137, color=LINE, width=2)
        y += 145
    p.box(70, 940, 1100, 300, "What the caller hears (and what the dashboard shows)", [
        "\"Qualified leads and booked appointments are written to the CRM. The production adapter maps",
        "the same fields to Salesforce, HubSpot or Zoho. The agent supports English, Hindi and Spanish…”",
        "Sources shown: integrations.md → CRM (0.25)  |  product.md → Languages (0.19)",
    ], fill=PALE_GREEN)
    p.note(1290, "To change a price or a fact, edit one line in knowledge/pricing.md. The agent is not "
                 "retrained — the answer changes on the next call. That is the whole point of RAG.")
    p.note(1410, "In production, the same retriever uses embeddings and a vector database for much larger "
                 "document sets. The rest of the agent does not change.")
    return p.finish(6)


def page7() -> Image.Image:
    p = Page("Memory, CRM and the summary", "Everything the agent learns is saved and reusable")
    p.box(445, 210, 350, 130, "LEADS", ["name, need, budget, score, grade"], fill=PALE_BLUE)
    p.box(70, 450, 300, 130, "MESSAGES", ["full call transcript"], fill=PALE_GRAY)
    p.box(470, 450, 300, 130, "APPOINTMENTS", ["date, time, status"], fill=PALE_GREEN)
    p.box(870, 450, 300, 130, "CALL SUMMARIES", ["summary + insights"], fill=PALE_GRAY)
    p.arrow(520, 342, 220, 445)
    p.arrow(620, 342, 620, 445)
    p.arrow(720, 342, 1020, 445)
    p.text(M, 630, "Example summary generated at the end of the call", "h2")
    p.box(70, 690, 1100, 330, "Call summary", [
        "\"Hello, I'm Rabia from Shree Clinic. Our budget is around 2 lakhs a year, and we want to go",
        "live in 2 months. I'm the founder, so I take the final decision.\"",
        "Facts: Rabia · Shree Clinic · need: receptionist · ₹2,00,000 · 2 months · decision-maker",
    ], fill=(255, 255, 255))
    p.box(70, 1060, 1100, 220, "Business insights", [
        "HOT lead — 100/100 on BANT.",
        "Sentiment positive across 6 turns; 0 objections needed handling.",
        "Knowledge consulted once; answer was source-cited.",
        "Next action: demo confirmed for 27 Nov 2026 at 10:00.",
    ], fill=PALE_GREEN)
    p.note(1330, "A booking is accepted only if the date and time are free. That single check stops two "
                 "callers being given the same slot. 'Reset' clears all demo data for the next presenter.")
    return p.finish(7)


def page8() -> Image.Image:
    p = Page("Scale, safety, cost — and your presentation", "The same design, grown up")
    p.box(70, 200, 190, 100, "Phone / browser", [])
    p.box(330, 200, 200, 100, "Load balancer", [])
    p.box(600, 200, 250, 100, "App replicas × 8–16", [])
    p.arrow(262, 250, 326, 250)
    p.arrow(532, 250, 596, 250)
    p.box(70, 400, 240, 120, "Redis", ["sessions + cache"])
    p.box(340, 400, 240, 120, "PostgreSQL", ["leads + appointments"])
    p.box(610, 400, 240, 120, "Vector DB", ["knowledge embeddings"])
    p.box(880, 400, 290, 120, "Job queue", ["summaries, CRM sync"])
    p.arrow(725, 302, 190, 396)
    p.arrow(725, 302, 460, 396)
    p.arrow(725, 302, 730, 396)
    p.arrow(725, 302, 1025, 396)

    p.text(M, 570, "Safety", "h2")
    p.para(M, 615, "TLS in transit, encryption at rest, tenant-scoped queries, role-based access, short-lived "
                   "tokens and an audit log for every lead or appointment change. Browser speech may be "
                   "processed by the browser vendor; production uses self-hosted speech or a contracted "
                   "provider with a data agreement.", key="small", width=CW)

    p.text(M, 830, "Rough monthly cost at 1,00,000 users", "h2")
    p.box(70, 875, 1100, 210, "", [
        "App compute $400–900   ·   Database $250   ·   Cache $90",
        "Speech $300–2,000 (less with self-hosted Whisper)   ·   Storage $100   ·   Monitoring $50",
        "Total roughly $1,200–3,400/month. The pilot on your laptop is Rs. 0.",
    ], fill=PALE_GRAY)

    p.text(M, 1130, "Your 5-minute presentation", "h2")
    p.box(70, 1175, 1100, 300, "", [
        "1  Open the app and click 'Run demo call'. Let it speak for about 20 seconds.",
        "2  Point to the live score changing from 25 → 75 → 100 as the caller talks.",
        "3  Show the RAG sources when Ava answers the Hindi / CRM question.",
        "4  Show the confirmed appointment in the CRM panel.",
        "5  Click 'End & summarize' and read the business insights aloud.",
        "6  Open architecture.svg, then this PDF, and finish with the scale-out slide.",
    ], fill=PALE_BLUE)
    return p.finish(8)


def page9() -> Image.Image:
    p = Page("Where things live, and likely questions", "A map of the files, plus short answers you can say aloud")
    p.text(M, 195, "File map", "h2")
    files = [
        ("app.py / run.sh", "One command to start everything"),
        ("static/", "The web page: voice, buttons, dashboard"),
        ("voice_agent/server.py", "The JSON API and file serving"),
        ("voice_agent/agent.py", "Conversation states and final decisions"),
        ("voice_agent/nlp.py", "Language, mood, slots, BANT score"),
        ("voice_agent/rag.py", "Knowledge search with citations"),
        ("voice_agent/crm.py", "SQLite: leads, meetings, messages"),
        ("knowledge/", "The four fact pages Ava can quote"),
        ("docs/", "Architecture SVG and 10 diagrams"),
        ("tests/", "Five automated end-to-end checks"),
    ]
    y = 250
    for name, purpose in files:
        p.d.rounded_rectangle([70, y, 1170, y + 50], radius=6, fill=(255, 255, 255), outline=LINE, width=1)
        p.text(88, y + 11, name, "bsmall")
        p.text(450, y + 11, purpose, "small", fill=MUTED)
        y += 57

    p.text(M, 850, "Questions they may ask you", "h2")
    qa = [
        ("Why not just use a big language model?",
         "Rules are deterministic, offline and easy to debug live. The interfaces can accept an LLM later without changing the app.", PALE_BLUE),
        ("Why RAG instead of training the model?",
         "Facts change often. Edit one line in a markdown file and the next answer is correct, with a visible source.", PALE_GREEN),
        ("How do you prevent double bookings?",
         "Before inserting, the CRM checks for a confirmed appointment at the same date and time; otherwise it offers alternatives.", PALE_GRAY),
        ("How does it reach 1,00,000 users?",
         "Stateless app replicas, Redis for sessions, PostgreSQL for data, a vector database for knowledge and a job queue for slow work.", PALE_BLUE),
    ]
    y = 905
    for question, answer, fill in qa:
        p.d.rounded_rectangle([70, y, 1170, y + 165], radius=10, fill=fill, outline=LINE, width=1)
        p.text(92, y + 14, question, "h3")
        p.para(92, y + 55, answer, key="small", width=1050, gap=3)
        y += 180
    return p.finish(9)


def main() -> None:
    pages = [page1(), page2(), page3(), page4(), page5(), page6(), page7(), page8(), page9()]
    for i, image in enumerate(pages, 1):
        image.save(PREVIEW / f"page-{i}.png")
    pages[0].save(OUT, "PDF", resolution=150.0, save_all=True, append_images=pages[1:])
    print(f"Wrote {OUT.relative_to(ROOT)} — {len(pages)} pages")
    print(f"Previews: {PREVIEW}")


if __name__ == "__main__":
    main()
