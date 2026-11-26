"""End-to-end checks for the demo workflow. Run: python3 -m unittest discover -s tests -v"""

import unittest

from voice_agent import crm
from voice_agent.agent import SalesAgent
from voice_agent.nlp import analyze_sentiment, bant_score, extract_slots
from voice_agent.rag import KnowledgeBase


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        crm.reset_demo_data()
        self.agent = SalesAgent()
        self.sid = self.agent.start_session()["session_id"]

    def say(self, text, lang=""):
        return self.agent.handle_message(self.sid, text, lang)

    def test_full_business_workflow(self):
        self.say("Hello, I'm Rabia from Shree Clinic. We need an AI receptionist for incoming calls.")
        r = self.say("Our budget is around 2 lakhs a year, and we want to go live in 2 months.")
        self.assertEqual(r["slots"]["budget_value"], 200000)
        self.assertEqual(r["slots"]["timeline_days"], 60)

        r = self.say("I'm the founder, so I take the final decision.")
        self.assertEqual(r["qualification"]["grade"], "HOT")
        self.assertEqual(r["qualification"]["total"], 100)

        r = self.say("How much does it cost?")
        self.assertTrue(any("pricing" in s["source"] for s in r["sources"]))
        self.assertIn("₹1,50,000", r["message"])

        r = self.say("Great. Let's book tomorrow at 10 AM.")
        self.assertEqual(r["stage"], "SCHEDULING")
        self.assertTrue(r["suggested_slots"] or r["appointment"])

        r = self.say("Yes, please confirm.")
        self.assertEqual(r["stage"], "CLOSED")
        self.assertTrue(r["appointment"]["ok"])

        summary = self.agent.end_call(self.sid)
        self.assertIn("Rabia", summary["facts"]["prospect"])
        self.assertEqual(summary["facts"]["budget"], "₹2,00,000")
        self.assertTrue(summary["insights"])

    def test_double_booking_is_rejected(self):
        self.say("I'm the founder and we need a sales agent. Budget 2 lakhs, timeline 1 month.")
        slot = self.agent.sessions[self.sid]["offered_slots"][0]
        first = crm.book_appointment(self.agent.sessions[self.sid]["lead_id"], slot["date"], slot["time"])
        second = crm.book_appointment(self.agent.sessions[self.sid]["lead_id"], slot["date"], slot["time"])
        self.assertTrue(first["ok"])
        self.assertFalse(second["ok"])

    def test_multilingual_and_sentiment(self):
        r = self.say("नमस्ते, मुझे Hindi में जानकारी चाहिए।", "hi-IN")
        self.assertEqual(r["language"], "hi-IN")
        self.assertIn("समझ", r["message"] + "बहुत अच्छा।")
        self.assertEqual(analyze_sentiment("This is excellent and very helpful")["label"], "positive")
        self.assertEqual(analyze_sentiment("This is bad and too expensive")["label"], "negative")

    def test_bant_and_slots(self):
        slots = extract_slots("We need a sales bot, budget ₹5 lakhs, go live in 3 weeks, I am the owner.")
        score = bant_score(slots)
        self.assertEqual(slots["budget_value"], 500000)
        self.assertEqual(slots["timeline_days"], 21)
        self.assertEqual(slots["authority"], "decision-maker")
        self.assertEqual(score["total"], 100)
        self.assertEqual(score["grade"], "HOT")

    def test_rag_retrieval(self):
        kb = KnowledgeBase()
        hits = kb.retrieve("Is our customer data secure and encrypted?")
        self.assertTrue(hits)
        self.assertIn("security", hits[0]["source"])


if __name__ == "__main__":
    unittest.main()
