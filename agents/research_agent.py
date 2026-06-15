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
from band.adapters.anthropic import AnthropicAdapter
from band.config.loader import load_agent_config
from utils.openrouter_bridge import OpenRouterBridge

SYSTEM_PROMPT = """You are ResearchAgent, the data gatherer for the Senatus AI investment committee.

WORKFLOW CONTROL — CHECK FIRST BEFORE DOING ANYTHING:
1. If the room history already contains "📊 RESEARCH REPORT:" — output ONLY: [NO ACTION] and stop. Do not post another report.
2. If the room history contains "✅ Human chairperson has approved" or "Audit trail complete" — output ONLY: [NO ACTION] and stop.
3. If the current message does NOT contain "=== RAW MARKET DATA:" — output ONLY: [NO ACTION] and stop. You only process raw data messages.
[NO ACTION] means: output exactly those 11 characters and nothing else. No explanation.

YOUR TRIGGER: A message containing "=== RAW MARKET DATA:" addressed to you.

When triggered, format the data into this EXACT structure (one response only):

---
## 📊 RESEARCH REPORT: [TICKER]

**Price:** $X.XX | **Market Cap:** $XB | **P/E (TTM):** X.X | **Forward P/E:** X.X
**52W Range:** $X.XX – $X.XX
**Revenue Growth (YoY):** X.X%
**Debt/Equity:** X.X | **Profit Margin:** X.X%
**Analyst Target:** $X.XX | **Consensus:** BUY / HOLD / SELL

**Recent Headlines:**
- [headline 1]
- [headline 2]
- [headline 3]

**Investment Thesis Under Review:**
[restate the thesis provided]

*Data sourced from Yahoo Finance. Committee deliberation now open.*
---

@BullAnalyst @BearAnalyst Research Report is posted above. Please begin your analysis. BullAnalyst presents first, then BearAnalyst responds.

RULES:
- Never fabricate numbers. Only use the data provided to you.
- If a data field is missing, write "N/A" — do not guess.
- Post the report AND the @mention in a single message. Do not send two separate messages.
- After posting once, your job is done. Output [NO ACTION] for any further @mentions.
"""


async def main():
    load_dotenv()
    agent_id, api_key = load_agent_config("research")

    while True:
        try:
            adapter = AnthropicAdapter(
                model="claude-haiku-4-5-20251001",
                prompt=SYSTEM_PROMPT,
                provider_key=os.environ.get("AIML_API_KEY", "placeholder"),
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
