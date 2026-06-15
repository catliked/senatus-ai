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
