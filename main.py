"""
Senatus AI — FastAPI Backend
Receives ticker + thesis from the frontend, fetches market data,
and fires the first message into the Band room to trigger the agent debate.
"""
import os
import yaml
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from utils.market_data import get_stock_data, format_stock_summary
from utils.band_client import send_message_to_room, send_human_message, get_room_messages

load_dotenv()

app = FastAPI(title="Senatus AI")

# Serve frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")


def _load_trigger_config() -> tuple[str, str, str]:
    """
    Returns (sender_api_key, research_agent_id, research_agent_handle).
    Sender is SynthesisChair — avoids ResearchAgent self-triggering.
    Falls back to env vars for cloud deployment (no agent_config.yaml).
    """
    env_sender = os.getenv("SYNTHESIS_AGENT_API_KEY", "")
    env_mention_id = os.getenv("RESEARCH_AGENT_ID", "")
    if env_sender and env_mention_id:
        return env_sender, env_mention_id, "ResearchAgent"
    try:
        with open("agent_config.yaml", "r") as f:
            config = yaml.safe_load(f)
        sender_key = config["synthesis"]["api_key"]
        mention_id = config["research"]["agent_id"]
        return sender_key, mention_id, "ResearchAgent"
    except FileNotFoundError:
        raise RuntimeError("Set SYNTHESIS_AGENT_API_KEY + RESEARCH_AGENT_ID env vars or provide agent_config.yaml")


def _load_synthesis_agent_id() -> str:
    """UUID of SynthesisChair, used to @mention it when the human posts an approval."""
    env_id = os.getenv("SYNTHESIS_AGENT_ID", "")
    if env_id:
        return env_id
    with open("agent_config.yaml", "r") as f:
        config = yaml.safe_load(f)
    return config["synthesis"]["agent_id"]


class AnalysisRequest(BaseModel):
    ticker: str
    thesis: str


class AnalysisResponse(BaseModel):
    status: str
    ticker: str
    room_id: str
    band_room_url: str
    message: str
    committee_id: str


class ApprovalRequest(BaseModel):
    decision: str  # "APPROVED" or "OVERRIDE"
    verdict: str   # BUY / HOLD / AVOID


@app.get("/")
async def root():
    return FileResponse("frontend/index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Senatus AI"}


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(req: AnalysisRequest):
    ticker = req.ticker.upper().strip()
    thesis = req.thesis.strip()

    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")
    if not thesis:
        raise HTTPException(status_code=400, detail="Investment thesis is required")

    room_id = os.getenv("BAND_ROOM_ID", "")
    if not room_id or "PASTE" in room_id:
        raise HTTPException(
            status_code=503,
            detail="BAND_ROOM_ID not configured in .env. Create a Band room and add the ID.",
        )

    # Fetch live market data (falls back to mock on failure)
    stock_data = get_stock_data(ticker)
    data_summary = format_stock_summary(stock_data)

    committee_id = f"SAI-{datetime.now().strftime('%Y%m%d')}-{ticker}-{datetime.now().strftime('%H%M%S')}"

    # Compose the trigger message for ResearchAgent
    trigger_message = (
        f"New analysis request from the investment committee.\n\n"
        f"**Committee ID:** {committee_id}\n"
        f"**Ticker:** {ticker}\n"
        f"**Thesis:** {thesis}\n\n"
        f"{data_summary}\n\n"
        f"Please format this into the official Research Report and begin the committee deliberation."
    )

    # SynthesisChair sends the trigger and @mentions ResearchAgent
    try:
        sender_key, research_id, _ = _load_trigger_config()
        send_message_to_room(
            room_id=room_id,
            text=trigger_message,
            sender_api_key=sender_key,
            mention_agent_id=research_id,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=502,
            detail=f"Failed to send message to Band room: {e}",
        )

    return AnalysisResponse(
        status="started",
        ticker=ticker,
        room_id=room_id,
        band_room_url=f"https://app.band.ai/chat/{room_id}",
        message=f"Committee deliberation initiated for {ticker}. Open your Band room to watch the debate.",
        committee_id=committee_id,
    )


@app.get("/room-status")
async def room_status():
    """Returns the real Band room message history so the dashboard can reflect
    actual deliberation state instead of a scripted animation."""
    room_id = os.getenv("BAND_ROOM_ID", "")
    if not room_id:
        raise HTTPException(status_code=503, detail="BAND_ROOM_ID not configured")
    try:
        sender_key, _, _ = _load_trigger_config()
        messages = get_room_messages(room_id, sender_key)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch room messages: {e}")
    return {"messages": messages}


@app.post("/approve")
async def approve(req: ApprovalRequest):
    """Posts the human chairperson's decision into the real Band room, @mentioning
    SynthesisChair so it posts the acknowledgement and closes the deliberation."""
    room_id = os.getenv("BAND_ROOM_ID", "")
    human_key = os.getenv("BAND_API_KEY", "")
    if not room_id or not human_key:
        raise HTTPException(status_code=503, detail="BAND_ROOM_ID or BAND_API_KEY not configured")
    try:
        synthesis_id = _load_synthesis_agent_id()
        text = f"@SynthesisChair {req.decision} — {req.verdict}"
        send_human_message(
            room_id=room_id,
            text=text,
            human_api_key=human_key,
            mention_agent_id=synthesis_id,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to post approval: {e}")
    return {"status": "sent"}
