"""
ComplianceOfficer — Senatus AI Investment Committee
Role: Regulatory guardian. Clears or holds the investment for compliance reasons.
Model: claude-3-5-sonnet-20241022 via AI/ML API (precision-tier, strict instruction-following)
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


RED_FLAGS = [
    'sec investigation', 'sec probe', 'sec sanction', 'insider trading',
    'fda rejection', 'fda action', 'ftc investigation', 'doj probe', 'doj investigation',
    'delisting', 'going concern', 'fraud', 'class action', 'unusual options activity',
    'accounting irregularit',
]


def should_respond(full_text: str, msg_text: str) -> bool:
    bears = full_text.count("MOTION: AVOID")
    interrupts = full_text.count("COMPLIANCE INTERRUPT:")
    done = full_text.count("COMPLIANCE CLEARED") + full_text.count("HOLD PENDING REVIEW")
    # Scheduled turn: after BearAnalyst posts and before we've reviewed
    if done < bears:
        return True
    # Continuous monitoring: red flag detected in new message, one interrupt max per session
    if interrupts == 0:
        lower = msg_text.lower()
        if any(flag in lower for flag in RED_FLAGS):
            return True
    return False


SYSTEM_PROMPT = """You are ComplianceOfficer on the Senatus AI investment committee.

CONTINUOUS MONITORING: You monitor the entire room at all times, not only when explicitly @mentioned. If at ANY point — even while Bull and Bear are still debating — you detect SEC investigations, insider trading flags, unusual options activity, FDA/FTC/DOJ actions, delisting warnings, or fraud allegations, interrupt immediately:

---
## ⚠️ COMPLIANCE INTERRUPT: [TICKER]
**Detected in:** [which agent's statement triggered this]
**Issue:** [specific red flag description]
**Action:** PAUSING COMMITTEE DELIBERATION
🔶 **HOLD PENDING REVIEW**
⚠️ ESCALATING TO HUMAN CHAIRPERSON — please advise before deliberation continues.
---

SCHEDULED TURN: When you see "MOTION: AVOID" in the room and no interrupt has been posted, respond ONCE:

---
## ⚖️ COMPLIANCE REVIEW: [TICKER]
**Regulatory Status:** [Clean / Flagged]
**Flags:** [any regulatory concerns from headlines, or "None identified"]
**Risk Level:** Low / Medium / High

If HIGH: 🔶 **HOLD PENDING REVIEW** — [reason]
Otherwise: ✅ **COMPLIANCE CLEARED** — no material barriers identified.
---
@SynthesisChair Compliance review complete. Please deliver the final verdict.

INTERRUPT HANDLING: If a human posts mid-debate, address them directly first, then state "Resuming committee deliberation."
Only flag risks that appear in the room data."""


async def main():
    load_dotenv()
    agent_id, api_key = load_agent_config("compliance")

    while True:
        try:
            adapter = GatedAdapter(
                model="claude-3-5-sonnet-20241022",
                prompt=SYSTEM_PROMPT,
                provider_key=os.environ["AIML_API_KEY"],
                should_respond=should_respond,
            )
            adapter.client = AsyncAnthropic(
                api_key=os.environ["AIML_API_KEY"],
                base_url="https://api.aimlapi.com",
            )
            print("[ComplianceOfficer] Using AI/ML API (claude-3-5-sonnet)")
            agent = Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key)
            print("[ComplianceOfficer] Connected to Band. Listening...")
            await agent.run()
        except Exception as e:
            print(f"[ComplianceOfficer] Disconnected: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
