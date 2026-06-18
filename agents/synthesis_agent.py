"""
SynthesisChair — Senatus AI Investment Committee
Role: Committee chairperson. Reads the ENTIRE room deliberation, tallies motions,
synthesizes arguments, and delivers the final verdict. Awaits human approval.
Model: claude-sonnet-4-6 (strongest reasoning — final verdict requires best judgment)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from anthropic import AsyncAnthropic
from band import Agent
from band.config.loader import load_agent_config
from utils.openrouter_bridge import OpenRouterBridge
from utils.workflow_gate import GatedAdapter


def should_respond(full_text: str, msg_text: str) -> bool:
    stripped = msg_text.strip().upper()
    if stripped.startswith("APPROVED") or stripped.startswith("OVERRIDE"):
        return "Human chairperson has approved" not in full_text
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

If compliance said HOLD, your verdict is HOLD unless human overrides."""


async def main():
    load_dotenv()
    agent_id, api_key = load_agent_config("synthesis")

    while True:
        try:
            adapter = GatedAdapter(
                model="claude-sonnet-4-6",  # haiku for testing, sonnet for demo
                prompt=SYSTEM_PROMPT,
                provider_key=os.environ.get("AIML_API_KEY", "placeholder"),
                should_respond=should_respond,
            )
            if os.environ.get("OPENROUTER_API_KEY"):
                adapter.client = OpenRouterBridge(
                    api_key=os.environ["OPENROUTER_API_KEY"],
                    model=os.environ.get("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct:free"),
                )
                print("[SynthesisChair] Using OpenRouter (free tier)")
            else:
                adapter.client = AsyncAnthropic(
                    api_key=os.environ["AIML_API_KEY"],
                    base_url="https://api.aimlapi.com",
                )
                print("[SynthesisChair] Using AI/ML API")
            agent = Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key)
            print("[SynthesisChair] Connected to Band. Listening for @mentions...")
            await agent.run()
        except Exception as e:
            print(f"[SynthesisChair] Disconnected: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
