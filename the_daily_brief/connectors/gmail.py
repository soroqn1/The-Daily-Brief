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
        token_env: str = "GMAIL_REFRESH_TOKEN",
        space_name: str = "default",
        scan_hours: int | None = None,
        audit_days: int | None = None,
        max_emails: int | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.token_env = token_env
        self.space_name = space_name
        self.scan_hours = scan_hours
        self.audit_days = audit_days
        self.max_emails = max_emails
        self.last_error: str | None = None

    def _resolve_credentials(self) -> tuple[str, str, str] | None:
        """Resolve OAuth credentials from explicit args or environment variables."""
        client_id = (self.client_id or os.getenv("GMAIL_CLIENT_ID") or "").strip()
        client_secret = (self.client_secret or os.getenv("GMAIL_CLIENT_SECRET") or "").strip()
        refresh_token = (
            self.refresh_token
            or os.getenv(self.token_env)
            or os.getenv("GMAIL_REFRESH_TOKEN")
            or ""
        ).strip()

        if ".apps.googleusercontent.com" in client_secret:
            msg = (
                "GMAIL_CLIENT_SECRET is set to a Client ID instead of a Client Secret! "
                "Check Google Cloud Console."
            )
            logger.warning("Gmail (%s): %s", self.space_name, msg)
            self.last_error = msg
            return None

        if not client_id or not client_secret or not refresh_token:
            missing: list[str] = []
            if not client_id:
                missing.append("GMAIL_CLIENT_ID")
            if not client_secret:
                missing.append("GMAIL_CLIENT_SECRET")
            if not refresh_token:
                missing.append(self.token_env)
            msg = f"Missing credentials: {', '.join(missing)}"
            logger.warning("Gmail (%s): %s", self.space_name, msg)
            self.last_error = msg
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
            err_desc = response.text
            try:
                err_desc = response.json().get("error_description", response.text)
            except Exception:
                pass
            msg = f"OAuth refresh failed ({response.status_code}): {err_desc}"
            logger.warning("Gmail (%s): %s", self.space_name, msg)
            self.last_error = msg
            return None

        data = response.json()
        return data.get("access_token")

    async def test_connection(self) -> tuple[bool, str]:
        """Test OAuth credentials and connectivity with Google."""
        creds = self._resolve_credentials()
        if not creds:
            return False, self.last_error or "Missing credentials"
        client_id, client_secret, refresh_token = creds

        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(TOKEN_ENDPOINT, data=payload)
                if response.status_code == 200:
                    return True, f"Gmail connected (token valid for space '{self.space_name}')"
                elif response.status_code == 401:
                    return (
                        False,
                        "Google error (401 invalid_client): Client ID or Secret is invalid",
                    )
                elif response.status_code == 400:
                    err_desc = response.json().get("error_description", "invalid_grant")
                    return False, f"Google error (400): {err_desc}. Refresh token expired/revoked."
                return False, f"Google OAuth error ({response.status_code}): {response.text}"
        except Exception as exc:
            return False, f"Network error connecting to Google: {exc}"

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
            max_emails = (
                self.max_emails
                if self.max_emails is not None
                else int(gmail_cfg.get("max_emails", 20))
            )
            scan_hours = (
                self.scan_hours
                if self.scan_hours is not None
                else int(gmail_cfg.get("scan_hours", 12))
            )
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

    async def fetch_audit(
        self, days: int | None = None, max_emails: int | None = None
    ) -> list[BriefItem]:
        """Fetch emails over recent days for deep email audit.

        Searches recent messages within `days` days. Never raises — logs exceptions and returns [].
        """
        try:
            creds = self._resolve_credentials()
            if creds is None:
                return []

            client_id, client_secret, refresh_token = creds
            effective_days = (
                days
                if days is not None
                else (self.audit_days if self.audit_days is not None else 5)
            )
            effective_max_emails = (
                max_emails
                if max_emails is not None
                else (self.max_emails if self.max_emails is not None else 35)
            )
            since_time = datetime.now(UTC) - timedelta(days=effective_days)
            after_epoch = int(since_time.timestamp())

            async with httpx.AsyncClient(timeout=15.0) as client:
                access_token = await self._get_access_token(
                    client, client_id, client_secret, refresh_token
                )
                if not access_token:
                    return []

                # Query messages within the audit window
                query = f"after:{after_epoch}"
                resp = await client.get(
                    GMAIL_MESSAGES_ENDPOINT,
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"q": query, "maxResults": effective_max_emails},
                )
                if resp.status_code != 200:
                    logger.warning("Failed to query Gmail audit messages: %s", resp.text)
                    return []

                messages = resp.json().get("messages", [])
                message_ids = [m["id"] for m in messages if "id" in m]

                tasks = [
                    self._fetch_message_detail(client, msg_id, access_token)
                    for msg_id in message_ids[:effective_max_emails]
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                items: list[BriefItem] = []
                for res in results:
                    if isinstance(res, BriefItem):
                        items.append(res)
                    elif isinstance(res, Exception):
                        logger.warning("Error fetching email detail for audit: %s", res)

                return items
        except Exception as exc:
            logger.error("Unexpected error in Gmail fetch_audit: %s", exc, exc_info=True)
            return []
