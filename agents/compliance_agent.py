"""
ComplianceOfficer — Senatus AI Investment Committee
Role: Regulatory guardian. Clears or holds the investment for compliance reasons.
Model: claude-haiku-4-5-20251001 via AI/ML API
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from anthropic import AsyncAnthropic
from band import Agent
from band.config.loader import load_agent_config
from utils.workflow_gate import GatedAdapter


def should_respond(full_text: str, msg_text: str) -> bool:
    bears = full_text.count("MOTION: AVOID")
    done = full_text.count("COMPLIANCE CLEARED") + full_text.count("HOLD PENDING REVIEW")
    return done < bears


SYSTEM_PROMPT = """You are ComplianceOfficer on an investment committee. Screen for regulatory risks after the bear case.

When you see "MOTION: AVOID" in the room, respond ONCE:

---
## ⚖️ COMPLIANCE REVIEW: [TICKER]
**Regulatory Status:** [Clean / Flagged]

**Flags:** [any regulatory concerns from headlines, or "None identified"]

**Risk Level:** Low / Medium / High

If risk is HIGH: 🔶 **HOLD PENDING REVIEW** — [reason]
Otherwise: ✅ **COMPLIANCE CLEARED** — no material barriers identified.
---
@SynthesisChair Compliance review complete. Please deliver the final verdict.

Only flag risks that appear in the room data."""


async def main():
    load_dotenv()
    agent_id, api_key = load_agent_config("compliance")

    while True:
        try:
            adapter = GatedAdapter(
                model="claude-haiku-4-5-20251001",
                prompt=SYSTEM_PROMPT,
                provider_key=os.environ["AIML_API_KEY"],
                should_respond=should_respond,
            )
            adapter.client = AsyncAnthropic(
                api_key=os.environ["AIML_API_KEY"],
                base_url="https://api.aimlapi.com",
            )
            print("[ComplianceOfficer] Using AI/ML API (claude-haiku-4-5)")
            agent = Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key)
            print("[ComplianceOfficer] Connected to Band. Listening...")
            await agent.run()
        except Exception as e:
            print(f"[ComplianceOfficer] Disconnected: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
