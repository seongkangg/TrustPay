"""One-time Gmail authorization:  python -m backend.inbox.authorize

Needs the OAuth client file (Google Cloud → APIs & Services → Credentials → OAuth client ID,
type "Desktop app") saved at GMAIL_CREDENTIALS_FILE. Opens a browser for consent and writes
GMAIL_TOKEN_FILE. Read-only scope; nothing in the mailbox is ever changed.
"""

import sys
from pathlib import Path

from backend.config import get_settings
from backend.inbox.gmail_client import SCOPES


def main() -> int:
    settings = get_settings()
    creds_path = Path(settings.gmail_credentials_file)
    token_path = Path(settings.gmail_token_file)
    if not creds_path.is_file():
        print(f"missing OAuth client file: {creds_path}", file=sys.stderr)
        print(
            "download it from Google Cloud (OAuth client ID, Desktop app) and save it there",
            file=sys.stderr,
        )
        return 1

    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
    creds = flow.run_local_server(port=0)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")

    profile = (
        build("gmail", "v1", credentials=creds, cache_discovery=False)
        .users()
        .getProfile(userId="me")
        .execute()
    )
    print(f"authorized {profile.get('emailAddress')} (read-only); token saved to {token_path}")
    print("set INBOX_ENABLED=true in .env and restart the backend")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
