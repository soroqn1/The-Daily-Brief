"""Interactive OAuth helper to authorize Gmail and save GMAIL_REFRESH_TOKEN to .env."""

import logging
import os
import sys
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import httpx
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
SCOPES = "https://www.googleapis.com/auth/gmail.readonly"
TOKEN_URL = "https://oauth2.googleapis.com/token"


def save_refresh_token_to_env(client_id: str, client_secret: str, refresh_token: str) -> None:
    """Save credentials and refresh token to .env file."""
    load_dotenv(ENV_FILE)
    existing_lines: list[str] = []
    if ENV_FILE.is_file():
        existing_lines = ENV_FILE.read_text(encoding="utf-8").splitlines()

    updated = False
    new_lines: list[str] = []
    for line in existing_lines:
        if line.startswith("GMAIL_REFRESH_TOKEN="):
            new_lines.append(f"GMAIL_REFRESH_TOKEN={refresh_token}")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f"GMAIL_REFRESH_TOKEN={refresh_token}")

    ENV_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    logger.info("Successfully updated %s with GMAIL_REFRESH_TOKEN!", ENV_FILE)


def run_auth(port: int = 8080) -> None:
    """Run local server to capture OAuth redirect code."""
    load_dotenv(ENV_FILE)
    client_id = os.getenv("GMAIL_CLIENT_ID")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET")

    if not client_id or not client_secret:
        logger.error("GMAIL_CLIENT_ID or GMAIL_CLIENT_SECRET missing in .env")
        sys.exit(1)

    redirect_uri = f"http://localhost:{port}"

    auth_params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(auth_params)}"

    auth_code: str | None = None

    class OAuthHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            nonlocal auth_code
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            if "code" in params:
                auth_code = params["code"][0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    b"<html><body><h2>Authorization successful!</h2>"
                    b"<p>You can close this tab and return to the terminal.</p></body></html>"
                )
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Failed to obtain authorization code.")

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = HTTPServer(("localhost", port), OAuthHandler)
    logger.info("Opening browser for Gmail authorization...")
    logger.info("If the browser does not open automatically, open this URL:\n%s\n", auth_url)
    webbrowser.open(auth_url)

    while auth_code is None:
        server.handle_request()

    server.server_close()

    logger.info("Exchanging authorization code for refresh token...")
    token_payload = {
        "code": auth_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    with httpx.Client(timeout=15.0) as client:
        resp = client.post(TOKEN_URL, data=token_payload)
        if resp.status_code != 200:
            logger.error("Token exchange failed: %s", resp.text)
            sys.exit(1)

        tokens = resp.json()
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            logger.error("Google did not return a refresh_token: %s", tokens)
            sys.exit(1)

    save_refresh_token_to_env(client_id, client_secret, refresh_token)
    logger.info("Gmail authorization complete! You can now run `task brief-now`.")


if __name__ == "__main__":
    run_auth()
