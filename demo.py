#!/usr/bin/env python3
"""Terminal version of the full sales workflow (no browser needed).

Run: python3 demo.py
"""

from voice_agent import crm
from voice_agent.agent import SalesAgent

LINES = [
    "Hello, I'm Rabia from Shree Clinic. We need an AI receptionist for incoming calls.",
    "Our budget is around 2 lakhs a year, and we want to go live in 2 months.",
    "I'm the founder, so I take the final decision.",
    "How much does it cost? Does it support Hindi and connect to our CRM?",
    "Great. Let's book tomorrow at 10 AM.",
    "Yes, please confirm.",
]


def main() -> None:
    crm.reset_demo_data()
    agent = SalesAgent()
    session = agent.start_session()
    print(f"\n{'=' * 72}\nAVA (AI agent): {session['message']}\n{'=' * 72}")

    for line in LINES:
        result = agent.handle_message(session["session_id"], line)
        print(f"\nPROSPECT       : {line}")
        print(f"AVA            : {result['message']}")
        q = result["qualification"]
        print(f"[stage={result['stage']} | BANT={q['total']} {q['grade']} | "
              f"intent={result['intent']} | sources={len(result['sources'])}]")

    print(f"\n{'=' * 72}\nCALL SUMMARY & INSIGHTS\n{'=' * 72}")
    outcome = agent.end_call(session["session_id"])
    print(outcome["summary"])
    for fact, value in outcome["facts"].items():
        print(f"  {fact:>10}: {value}")
    print("\nInsights:")
    for insight in outcome["insights"]:
        print("  •", insight)
    print(f"\nAppointment written to CRM: {outcome['appointment']}\n")


if __name__ == "__main__":
    main()
