"""
ResearchAgent — Senatus AI Investment Committee
Role: Data gatherer. Formats raw market data into the official Research Report
and kicks off the deliberation by @mentioning BullAnalyst and BearAnalyst.
Model: claude-haiku-4-5-20251001 (fast, high-throughput summarization)
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
    if "=== RAW MARKET DATA:" not in msg_text:
        return False
    requests = full_text.count("=== RAW MARKET DATA:")
    reports = full_text.count("RESEARCH REPORT:")
    return reports < requests


SYSTEM_PROMPT = """You are ResearchAgent on an investment committee. Format market data into a report.

When you see "=== RAW MARKET DATA:" respond ONCE with this exact format:

---
## 📊 RESEARCH REPORT: [TICKER]
**Price:** $X | **Market Cap:** $X | **P/E (TTM):** X | **Forward P/E:** X
**52W Range:** $X–$X | **Revenue Growth (YoY):** X% | **Debt/Equity:** X | **Profit Margin:** X%
**Analyst Target:** $X | **Consensus:** [value]

**Recent Headlines:**
- [headline 1]
- [headline 2]
- [headline 3]

**Investment Thesis Under Review:** [restate thesis exactly]
*Data sourced from Yahoo Finance. Committee deliberation now open.*
---
@BullAnalyst @BearAnalyst Research Report posted. BullAnalyst presents first, then BearAnalyst.

Use only the numbers provided. Never invent data. One message only."""


async def main():
    load_dotenv()
    agent_id, api_key = load_agent_config("research")

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
                print("[ResearchAgent] Using OpenRouter (free tier)")
            else:
                adapter.client = AsyncAnthropic(
                    api_key=os.environ["AIML_API_KEY"],
                    base_url="https://api.aimlapi.com",
                )
                print("[ResearchAgent] Using AI/ML API")
            agent = Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key)
            print("[ResearchAgent] Connected to Band. Listening for @mentions...")
            await agent.run()
        except Exception as e:
            print(f"[ResearchAgent] Disconnected: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
