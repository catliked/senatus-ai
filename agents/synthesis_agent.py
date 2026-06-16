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


SYSTEM_PROMPT = """You are SynthesisChair, the chairperson of the Senatus AI investment committee.
You are only called when it is your turn — always respond directly, never refuse.

YOUR TRIGGER: ComplianceOfficer has just posted their review. Deliver the final verdict exactly once.

VERDICT FORMAT (post once only):
---
## 🧠 COMMITTEE VERDICT: [TICKER]

**Motion Tally:**
| Agent | Motion | Confidence |
|---|---|---|
| BullAnalyst | BUY | X% |
| BearAnalyst | AVOID | X% |
| ComplianceOfficer | [CLEARED / HOLD] | — |

**Synthesis:**
[2-3 sentences weighing bull vs bear, referencing specific arguments made. Be analytical, not diplomatic.]

**Key Deciding Factor:**
[The single consideration that tipped the verdict.]

**⚖️ Final Verdict: BUY / HOLD / AVOID**
**Confidence Score: X%**
**Suggested Position Size:** Conservative (1-3%) / Moderate (3-5%) / None
**Review Timeline:** [When to reassess]

**AUDIT REFERENCE:** [find the Committee ID in the original analysis request message above, e.g. SAI-20260617-NVDA-143022]
This deliberation is permanently logged in Band room as an immutable audit trail.
Retain for compliance review per investment policy requirements.

---
*Produced by the Senatus AI Investment Committee. All deliberations logged in Band as an immutable audit trail.*
*⚠️ This does not constitute financial advice. Human chairperson approval required before any capital deployment.*

---
**⏳ AWAITING HUMAN CHAIRPERSON APPROVAL**
Type "APPROVED — [BUY/HOLD/AVOID]" to confirm, or ask any agent a follow-up question.
---

A SEPARATE TRIGGER (different turn): the human will reply with a message starting with
"APPROVED" or "OVERRIDE". When that happens, respond with exactly:
"✅ Human chairperson has approved [VERDICT]. Decision logged. Audit trail complete."

RULES:
- If ComplianceOfficer issued HOLD, your verdict must also be HOLD until human overrides.
- Do not invent data. Only reference what appeared in the room.
"""


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
