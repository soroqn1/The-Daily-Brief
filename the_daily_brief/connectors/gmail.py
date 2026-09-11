"""Gmail connector for fetching unread and flagged emails via Gmail API."""

import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta

import httpx

from the_daily_brief.config import get_config
from the_daily_brief.connectors.base import BaseConnector, BriefItem

logger = logging.getLogger(__name__)

TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GMAIL_MESSAGES_ENDPOINT = "https://gmail.googleapis.com/gmail/v1/users/me/messages"


class GmailConnector(BaseConnector):
    """Connector for Gmail via Google OAuth2 and Gmail REST API."""

    name: str = "gmail"

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        refresh_token: str | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token

    def _resolve_credentials(self) -> tuple[str, str, str] | None:
        """Resolve OAuth credentials from explicit args or environment variables."""
        client_id = self.client_id or os.getenv("GMAIL_CLIENT_ID")
        client_secret = self.client_secret or os.getenv("GMAIL_CLIENT_SECRET")
        refresh_token = self.refresh_token or os.getenv("GMAIL_REFRESH_TOKEN")

        if not client_id or not client_secret or not refresh_token:
            logger.warning(
                "Gmail connector skipped: missing credentials in environment "
                "(GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN)"
            )
            return None

        return client_id, client_secret, refresh_token

    async def _get_access_token(
        self,
        client: httpx.AsyncClient,
        client_id: str,
        client_secret: str,
        refresh_token: str,
    ) -> str | None:
        """Exchange refresh token for a short-lived access token."""
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        response = await client.post(TOKEN_ENDPOINT, data=payload)
        if response.status_code != 200:
            logger.warning(
                "Gmail OAuth refresh failed with status %d: %s",
                response.status_code,
                response.text,
            )
            return None

        data = response.json()
        return data.get("access_token")

    async def _fetch_message_detail(
        self,
        client: httpx.AsyncClient,
        message_id: str,
        access_token: str,
    ) -> BriefItem | None:
        """Fetch details for a single message and map it to a BriefItem."""
        url = f"{GMAIL_MESSAGES_ENDPOINT}/{message_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await client.get(url, headers=headers)
        if response.status_code != 200:
            logger.warning(
                "Failed to fetch Gmail message %s (status %d)",
                message_id,
                response.status_code,
            )
            return None

        data = response.json()
        label_ids = set(data.get("labelIds", []))

        # Extract headers
        headers_list = data.get("payload", {}).get("headers", [])
        headers_map = {
            h.get("name", "").lower(): h.get("value", "")
            for h in headers_list
            if isinstance(h, dict)
        }

        subject = headers_map.get("subject", "(No Subject)")
        sender = headers_map.get("from", "")
        title = f"{sender}: {subject}" if sender else subject

        # Parse snippet or body (limit to ~300 chars)
        snippet = data.get("snippet", "")
        body = snippet[:300] if snippet else ""

        # Parse message timestamp
        timestamp: datetime | None = None
        internal_date = data.get("internalDate")
        if internal_date and str(internal_date).isdigit():
            timestamp = datetime.fromtimestamp(int(internal_date) / 1000, tz=UTC)

        # Flagged / Starred or Important messages get higher priority
        is_actionable = "STARRED" in label_ids or "IMPORTANT" in label_ids
        category = "action_required" if is_actionable else "missed"
        priority = 1 if is_actionable else 2

        mail_url = f"https://mail.google.com/mail/u/0/#inbox/{message_id}"

        return BriefItem(
            source=self.name,
            category=category,
            title=title,
            body=body,
            priority=priority,
            timestamp=timestamp,
            url=mail_url,
        )

    async def fetch(self) -> list[BriefItem]:
        """Fetch unread and flagged emails since the last brief timestamp.

        Never raises — logs exceptions and returns [].
        """
        try:
            config = get_config()
            gmail_cfg = config.connectors.get("gmail", {})
            if not gmail_cfg.get("enabled", True):
                logger.debug("Gmail connector is disabled in configuration.")
                return []

            creds = self._resolve_credentials()
            if creds is None:
                return []

            client_id, client_secret, refresh_token = creds
            max_emails = int(gmail_cfg.get("max_emails", 20))
            scan_hours = int(gmail_cfg.get("scan_hours", 12))
            since_time = datetime.now(UTC) - timedelta(hours=scan_hours)
            after_epoch = int(since_time.timestamp())

            async with httpx.AsyncClient(timeout=15.0) as client:
                access_token = await self._get_access_token(
                    client, client_id, client_secret, refresh_token
                )
                if not access_token:
                    return []

                # Fetch starred items (always) and recent unread items in parallel
                starred_req = client.get(
                    GMAIL_MESSAGES_ENDPOINT,
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"q": "is:starred", "maxResults": max_emails},
                )
                unread_req = client.get(
                    GMAIL_MESSAGES_ENDPOINT,
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={
                        "q": f"is:unread after:{after_epoch}",
                        "maxResults": max_emails,
                    },
                )

                resp_starred, resp_unread = await asyncio.gather(starred_req, unread_req)

                message_ids: list[str] = []
                seen_ids: set[str] = set()

                for resp in (resp_starred, resp_unread):
                    if resp.status_code == 200:
                        data = resp.json()
                        for m in data.get("messages", []):
                            msg_id = m.get("id")
                            if msg_id and msg_id not in seen_ids:
                                seen_ids.add(msg_id)
                                message_ids.append(msg_id)

                tasks = [
                    self._fetch_message_detail(client, msg_id, access_token)
                    for msg_id in message_ids[:max_emails]
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                items: list[BriefItem] = []
                for res in results:
                    if isinstance(res, BriefItem):
                        items.append(res)
                    elif isinstance(res, Exception):
                        logger.warning("Error fetching individual email: %s", res)

                return items

        except Exception as exc:
            logger.error("Unexpected error in Gmail connector: %s", exc, exc_info=True)
            return []
