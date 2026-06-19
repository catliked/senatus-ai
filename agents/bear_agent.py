"""
BearAnalyst — Senatus AI Investment Committee
Role: Adversarially challenges the bull thesis.
Model: deepseek-r1 via AI/ML API (reasoning-tier, adversarial challenge)
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
    if "COMPLIANCE INTERRUPT:" in full_text:
        if not any(p in full_text for p in ["Resuming committee deliberation", "APPROVED", "OVERRIDE"]):
            return False
    bulls = full_text.count("MOTION: BUY")
    bears = full_text.count("MOTION: AVOID")
    return bears < bulls


SYSTEM_PROMPT = """You are BearAnalyst on an investment committee. Challenge the bull thesis after BullAnalyst posts.

When you see "MOTION: BUY" in the room, respond ONCE:

---
## 📉 BEAR CASE: [TICKER]
**Counter:** [Challenge one of BullAnalyst's specific claims]

**Key Risks:**
- [risk 1 from data]
- [risk 2 from data]

**Valuation Concern:** [why price may be stretched]
**Bear Case:** [one sharp sentence]

🔴 **MOTION: AVOID** | Confidence: [50-85]%
---
@ComplianceOfficer Please conduct your compliance review.

INTERRUPT HANDLING: If a human posts mid-debate, address them directly first, then state "Resuming committee deliberation." and continue your task if incomplete.
Only use data from the Research Report. Never invent numbers."""


async def main():
    load_dotenv()
    agent_id, api_key = load_agent_config("bear")

    while True:
        try:
            adapter = GatedAdapter(
                model="deepseek-r1",
                prompt=SYSTEM_PROMPT,
                provider_key=os.environ["AIML_API_KEY"],
                should_respond=should_respond,
            )
            adapter.client = OpenAIShimClient(
                api_key=os.environ["AIML_API_KEY"],
                base_url="https://api.aimlapi.com/v1",
            )
            print("[BearAnalyst] Using AI/ML API (deepseek-r1)")
            agent = Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key)
            print("[BearAnalyst] Connected to Band. Listening...")
            await agent.run()
        except Exception as e:
            print(f"[BearAnalyst] Disconnected: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
