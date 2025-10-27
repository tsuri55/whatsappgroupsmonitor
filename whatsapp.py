"""WhatsApp API client wrapper."""
import logging
from typing import Any, Optional

import httpx
from pydantic import BaseModel
from tenacity import (
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_random_exponential,
)

from config import settings

logger = logging.getLogger(__name__)


class SendMessageRequest(BaseModel):
    """Request model for sending messages."""

    phone: str
    message: str


class WhatsAppMessage(BaseModel):
    """WhatsApp message data model."""

    message_id: str
    group_jid: str
    group_name: Optional[str] = None
    sender_jid: str
    sender_name: Optional[str] = None
    content: str
    message_type: str = "text"
    timestamp: int  # Unix timestamp


class WhatsAppClient:
    """Client for interacting with go-whatsapp-web-multidevice API."""

    def __init__(self, api_url: str = None, api_key: str = None):
        """Initialize WhatsApp client."""
        self.api_url = api_url or settings.whatsapp_api_url
        self.api_key = api_key or settings.whatsapp_api_key
        self.client = httpx.AsyncClient(
            base_url=self.api_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30.0,
        )
        self._my_jid: Optional[str] = None

    @retry(
        wait=wait_random_exponential(min=settings.retry_min_wait, max=settings.retry_max_wait),
        stop=stop_after_attempt(settings.max_retry_attempts),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def send_message(self, request: SendMessageRequest) -> dict[str, Any]:
        """Send a message via WhatsApp."""
        try:
            response = await self.client.post(
                "/send/message",
                json={"phone": request.phone, "message": request.message},
            )
            response.raise_for_status()
            logger.info(f"Message sent to {request.phone}")
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to send message to {request.phone}: {e}")
            raise

    @retry(
        wait=wait_random_exponential(min=settings.retry_min_wait, max=settings.retry_max_wait),
        stop=stop_after_attempt(settings.max_retry_attempts),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def get_groups(self) -> list[dict[str, Any]]:
        """Get all groups the account is part of."""
        try:
            response = await self.client.get("/groups")
            response.raise_for_status()
            groups = response.json()
            logger.info(f"Retrieved {len(groups)} groups")
            return groups
        except httpx.HTTPError as e:
            logger.error(f"Failed to get groups: {e}")
            raise

    @retry(
        wait=wait_random_exponential(min=settings.retry_min_wait, max=settings.retry_max_wait),
        stop=stop_after_attempt(settings.max_retry_attempts),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def get_my_jid(self) -> str:
        """Get the current account's JID."""
        if self._my_jid:
            return self._my_jid

        try:
            # Try the app info endpoint instead
            response = await self.client.get("/app/devices")
            response.raise_for_status()
            data = response.json()

            # Extract JID from devices list
            if isinstance(data, list) and len(data) > 0:
                device = data[0]
                self._my_jid = device.get("device", "")
                logger.info(f"My JID: {self._my_jid}")
                return self._my_jid

            # Fallback: if no JID found, use a placeholder
            # The app will still work for sending messages
            logger.warning("Could not retrieve JID from API, using placeholder")
            self._my_jid = "bot@s.whatsapp.net"
            return self._my_jid

        except httpx.HTTPError as e:
            logger.error(f"Failed to get user info: {e}")
            raise

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
        logger.info("WhatsApp client closed")


def normalize_jid(jid: str) -> str:
    """Normalize WhatsApp JID format."""
    # Remove any @s.whatsapp.net or @g.us suffixes and re-add appropriately
    jid = jid.split("@")[0]
    # Group JIDs typically contain '-' and end with @g.us
    if "-" in jid:
        return f"{jid}@g.us"
    # User JIDs end with @s.whatsapp.net
    return f"{jid}@s.whatsapp.net"
