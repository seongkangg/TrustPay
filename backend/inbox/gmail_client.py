"""Thin read-only wrapper over the Gmail API (v1).

Only two operations: list recent messages that carry a PDF attachment, and fetch one message's
`invoice.pdf` bytes. The mailbox is never modified. Tests inject a fake `service` object.
"""

import base64
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.inbox import InboxError, InboxMessage, is_invoice_attachment

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
PAGE_SIZE = 50


class GmailClient:
    def __init__(self, service: Any):
        self._service = service

    # ------------------------------------------------------------ construction

    @staticmethod
    def token_exists(token_file: str) -> bool:
        return Path(token_file).is_file()

    @classmethod
    def from_files(cls, credentials_file: str, token_file: str) -> "GmailClient":
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
        except ImportError as exc:  # pragma: no cover
            raise InboxError(
                "google-api-python-client / google-auth-oauthlib are not installed"
            ) from exc

        if not cls.token_exists(token_file):
            raise InboxError(
                f"no Gmail token at {token_file}; run `python -m backend.inbox.authorize` once "
                f"(needs the OAuth client file at {credentials_file})"
            )
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                Path(token_file).write_text(creds.to_json(), encoding="utf-8")
            service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        except Exception as exc:  # noqa: BLE001 — any auth/build failure is "not authorized"
            raise InboxError(f"Gmail authorization failed: {exc}") from exc
        return cls(service)

    # ------------------------------------------------------------------- read

    def list_candidates(self, lookback_days: int) -> list[str]:
        """IDs of messages with a PDF attachment, newest first."""
        query = f"has:attachment filename:pdf newer_than:{int(lookback_days)}d"
        ids: list[str] = []
        page_token = None
        try:
            while True:
                resp = (
                    self._service.users()
                    .messages()
                    .list(userId="me", q=query, maxResults=PAGE_SIZE, pageToken=page_token)
                    .execute()
                )
                ids.extend(m["id"] for m in resp.get("messages", []))
                page_token = resp.get("nextPageToken")
                if not page_token:
                    break
        except Exception as exc:  # noqa: BLE001
            raise InboxError(f"Gmail list failed: {exc}") from exc
        return ids

    def fetch(self, message_id: str) -> InboxMessage | None:
        """The message's invoice.pdf, or None when it has no attachment by that name."""
        try:
            msg = (
                self._service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
        except Exception as exc:  # noqa: BLE001
            raise InboxError(f"Gmail get {message_id} failed: {exc}") from exc

        payload = msg.get("payload", {})
        part = _find_invoice_part(payload)
        if part is None:
            return None

        body = part.get("body", {})
        data = body.get("data")
        if not data and body.get("attachmentId"):
            try:
                att = (
                    self._service.users()
                    .messages()
                    .attachments()
                    .get(userId="me", messageId=message_id, id=body["attachmentId"])
                    .execute()
                )
            except Exception as exc:  # noqa: BLE001
                raise InboxError(f"Gmail attachment for {message_id} failed: {exc}") from exc
            data = att.get("data")
        if not data:
            return None

        headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
        internal = msg.get("internalDate")
        received = datetime.fromtimestamp(int(internal) / 1000, tz=UTC) if internal else None
        return InboxMessage(
            message_id=message_id,
            thread_id=msg.get("threadId"),
            sender=headers.get("from"),
            subject=headers.get("subject"),
            received_at=received,
            attachment_name=part.get("filename", ""),
            pdf_bytes=base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)),
        )


def _find_invoice_part(part: dict[str, Any]) -> dict[str, Any] | None:
    if is_invoice_attachment(part.get("filename")):
        return part
    for child in part.get("parts", []) or []:
        found = _find_invoice_part(child)
        if found is not None:
            return found
    return None
