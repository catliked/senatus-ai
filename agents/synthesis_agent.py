"""
SynthesisChair — Senatus AI Investment Committee
Role: Committee chairperson. Synthesizes all arguments, delivers final verdict, awaits human approval.
Model: openai/o4-mini via AI/ML API (reasoning-tier, final synthesis & verdict)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from band import Agent
from band.config.loader import load_agent_config
from utils.workflow_gate import GatedAdapter
from utils.openai_shim import OpenAIShimClient


def should_respond(full_text: str, msg_text: str) -> bool:
    stripped = msg_text.strip().upper()
    if stripped.startswith("APPROVED") or stripped.startswith("OVERRIDE"):
        return "Human chairperson has approved" not in full_text
    # Don't synthesize from a mid-debate compliance interrupt (Bear hasn't posted yet)
    if "COMPLIANCE INTERRUPT:" in full_text and "MOTION: AVOID" not in full_text:
        return False
    done = full_text.count("COMPLIANCE CLEARED") + full_text.count("HOLD PENDING REVIEW")
    verdicts = full_text.count("Final Verdict:")
    return verdicts < done


SYSTEM_PROMPT = """You are SynthesisChair, chairperson of an investment committee. Two triggers:

TRIGGER 1 — After compliance posts: deliver final verdict ONCE.
---
## 🧠 COMMITTEE VERDICT: [TICKER]

| Agent | Motion | Confidence |
|---|---|---|
| BullAnalyst | BUY | X% |
| BearAnalyst | AVOID | X% |
| ComplianceOfficer | [CLEARED/HOLD] | — |

**Synthesis:** [2 sentences weighing bull vs bear]
**Key Deciding Factor:** [what tipped the verdict]

**⚖️ Final Verdict: BUY / HOLD / AVOID**
**Confidence Score: X%**
**Suggested Position Size:** Conservative (1-3%) / Moderate (3-5%) / None

**AUDIT REFERENCE:** [Committee ID from the original request, e.g. SAI-20260618-NVDA-143022]
⚠️ Not financial advice. AWAITING HUMAN CHAIRPERSON APPROVAL.
---

TRIGGER 2 — Human says APPROVED or OVERRIDE: reply with exactly:
"✅ Human chairperson has approved [VERDICT]. Decision logged. Audit trail complete."

If compliance said HOLD, your verdict is HOLD unless human overrides.

INTERRUPT HANDLING: If a human posts mid-debate, address them directly first, then state "Resuming committee deliberation." Human messages take priority."""


async def main():
    load_dotenv()
    agent_id, api_key = load_agent_config("synthesis")

    while True:
        try:
            adapter = GatedAdapter(
                model="openai/o4-mini",
                prompt=SYSTEM_PROMPT,
                provider_key=os.environ["AIML_API_KEY"],
                should_respond=should_respond,
            )
            adapter.client = OpenAIShimClient(
                api_key=os.environ["AIML_API_KEY"],
                base_url="https://api.aimlapi.com/v1",
            )
            print("[SynthesisChair] Using AI/ML API (openai/o4-mini)")
            agent = Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key)
            print("[SynthesisChair] Connected to Band. Listening...")
            await agent.run()
        except Exception as e:
            print(f"[SynthesisChair] Disconnected: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
