"""
ComplianceOfficer — Senatus AI Investment Committee
Role: Regulatory guardian. Scans the full room discussion for red flags.
Can escalate to human (pausing the workflow) or clear the committee to proceed.
Model: claude-haiku-4-5-20251001 (precise instruction-following)
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
    bears = full_text.count("MOTION: AVOID")
    done = full_text.count("COMPLIANCE CLEARED") + full_text.count("HOLD PENDING REVIEW")
    return done < bears


SYSTEM_PROMPT = """You are ComplianceOfficer, the regulatory guardian on the Senatus AI investment committee.
You are only called when it is your turn — always respond directly, never refuse.

YOUR TRIGGER: BearAnalyst has just posted their bear case. Post your compliance review exactly once.

RESPONSE FORMAT:
---
## ⚖️ COMPLIANCE REVIEW: [TICKER]

**Regulatory Status:** [Clean / Flagged / Under Investigation]

**Flags Identified:**
- [Specific regulatory concern, or "None identified in available data"]
- [Second flag if applicable]

**Areas Checked:**
✓ SEC sanctions or investigations (from news/filings)
✓ Insider trading or unusual activity mentions
✓ Sector regulatory risk (FDA, FTC, DOJ, financial regulators)
✓ Listing status and any exchange warnings
✓ Analyst conflict-of-interest disclosures

**Risk Level:** Low / Medium / High

**Compliance Recommendation:**
[1-2 sentences]

[IF Risk Level is HIGH:]
🔶 **MOTION: HOLD PENDING REVIEW**
⚠️ **ESCALATING TO HUMAN CHAIRPERSON**

[IF Risk Level is LOW or MEDIUM:]
✅ **COMPLIANCE CLEARED** — no material regulatory barriers identified. Proceeding to synthesis.
---

@SynthesisChair Compliance review complete. Please deliver the committee's final verdict.

RULES:
- Base flags only on information already in the room. Do not invent risks.
"""


async def main():
    load_dotenv()
    agent_id, api_key = load_agent_config("compliance")

    while True:
        try:
            adapter = GatedAdapter(
                model="claude-haiku-4-5-20251001",
                prompt=SYSTEM_PROMPT,
                provider_key=os.environ.get("AIML_API_KEY", "placeholder"),
                should_respond=should_respond,
            )
            if os.environ.get("OPENROUTER_API_KEY"):
                adapter.client = OpenRouterBridge(
                    api_key=os.environ["OPENROUTER_API_KEY"],
                    model=os.environ.get("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct:free"),
                )
                print("[ComplianceOfficer] Using OpenRouter (free tier)")
            else:
                adapter.client = AsyncAnthropic(
                    api_key=os.environ["AIML_API_KEY"],
                    base_url="https://api.aimlapi.com",
                )
                print("[ComplianceOfficer] Using AI/ML API")
            agent = Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key)
            print("[ComplianceOfficer] Connected to Band. Listening for @mentions...")
            await agent.run()
        except Exception as e:
            print(f"[ComplianceOfficer] Disconnected: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
