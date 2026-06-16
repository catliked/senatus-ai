"""
Band REST client using the official thenvoi_rest SDK.
Correct auth: X-API-Key header (not Bearer).
Messages require a mentions list with agent UUIDs.
"""
from band.client.rest import (
    RestClient,
    ChatMessageRequest,
    ChatMessageRequestMentionsItem,
    DEFAULT_REQUEST_OPTIONS,
)


BAND_BASE_URL = "https://app.band.ai"


def send_message_to_room(
    room_id: str,
    text: str,
    sender_api_key: str,
    mention_agent_id: str,
) -> dict:
    """
    Post a message to a Band room on behalf of an agent.
    mention_agent_id: UUID of the agent being @mentioned (required by Band API).
    """
    client = RestClient(api_key=sender_api_key, base_url=BAND_BASE_URL)
    result = client.agent_api_messages.create_agent_chat_message(
        chat_id=room_id,
        message=ChatMessageRequest(
            content=text,
            mentions=[ChatMessageRequestMentionsItem(id=mention_agent_id)],
        ),
        request_options=DEFAULT_REQUEST_OPTIONS,
    )
    return result


def send_human_message(
    room_id: str,
    text: str,
    human_api_key: str,
    mention_agent_id: str,
) -> dict:
    """
    Post a message to a Band room as the human chairperson (BAND_API_KEY, band_u_ prefix).
    Used for the dashboard's Approve/Override actions so they show up as real room activity.
    """
    client = RestClient(api_key=human_api_key, base_url=BAND_BASE_URL)
    result = client.human_api_messages.send_my_chat_message(
        chat_id=room_id,
        message=ChatMessageRequest(
            content=text,
            mentions=[ChatMessageRequestMentionsItem(id=mention_agent_id)],
        ),
        request_options=DEFAULT_REQUEST_OPTIONS,
    )
    return result


def get_room_messages(room_id: str, agent_api_key: str) -> list[dict]:
    """
    Fetch the full message history of a Band room so the dashboard can reflect
    real deliberation state instead of a scripted animation.
    """
    client = RestClient(api_key=agent_api_key, base_url=BAND_BASE_URL)
    result = client.agent_api_messages.list_agent_messages(
        chat_id=room_id,
        status="all",
        page_size=100,
        request_options=DEFAULT_REQUEST_OPTIONS,
    )
    return [
        {
            "sender": m.sender_name or m.sender_id,
            "content": m.content,
            "time": m.inserted_at.isoformat() if m.inserted_at else None,
        }
        for m in result.data
    ]
