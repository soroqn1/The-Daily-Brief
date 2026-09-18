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


def update_env_vars(vars_to_update: dict[str, str]) -> None:
    """Update or append environment variables in .env and os.environ atomically."""
    for k, v in vars_to_update.items():
        if "\n" in str(k) or "\r" in str(k) or "\n" in str(v) or "\r" in str(v):
            raise ValueError(f"Newline characters are not allowed in env vars: {k}")

    load_dotenv(ENV_FILE)
    existing_lines: list[str] = []
    if ENV_FILE.is_file():
        existing_lines = ENV_FILE.read_text(encoding="utf-8").splitlines()

    updated_keys = set()
    new_lines: list[str] = []
    for line in existing_lines:
        matched = False
        for k, v in vars_to_update.items():
            prefix = f"{k}="
            if line.startswith(prefix):
                new_lines.append(f"{prefix}{v}")
                updated_keys.add(k)
                matched = True
                break
        if not matched:
            new_lines.append(line)

    for k, v in vars_to_update.items():
        if k not in updated_keys:
            new_lines.append(f"{k}={v}")

    tmp_file = ENV_FILE.with_suffix(".tmp")
    tmp_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    os.replace(tmp_file, ENV_FILE)

    for k, v in vars_to_update.items():
        os.environ[k] = v
    logger.info("Updated %s with keys: %s", ENV_FILE, list(vars_to_update.keys()))


def save_refresh_token_to_env(
    client_id: str,
    client_secret: str,
    refresh_token: str,
    token_env: str = "GMAIL_REFRESH_TOKEN",
) -> None:
    """Save credentials and refresh token to .env file."""
    updates = {token_env: refresh_token}
    if client_id:
        updates["GMAIL_CLIENT_ID"] = client_id
    if client_secret:
        updates["GMAIL_CLIENT_SECRET"] = client_secret
    update_env_vars(updates)


def run_auth(port: int = 8080, space: str = "default") -> None:
    """Run local server to capture OAuth redirect code."""
    from the_daily_brief.config import get_config

    config = get_config()
    space_cfg = config.get_space(space)
    token_env = space_cfg.gmail_token_env

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
                err_msg = params.get("error", ["Failed to obtain authorization code"])[0]
                auth_code = ""
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    f"<html><body><h2>OAuth Error</h2><p>{err_msg}</p></body></html>".encode()
                )

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = HTTPServer(("localhost", port), OAuthHandler)
    logger.info("Opening browser for Gmail authorization for space '%s'...", space)
    logger.info("If the browser does not open automatically, open this URL:\n%s\n", auth_url)
    webbrowser.open(auth_url)

    while auth_code is None:
        server.handle_request()

    server.server_close()

    if not auth_code:
        logger.error("Authorization failed or was cancelled by user.")
        sys.exit(1)

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

    save_refresh_token_to_env(client_id, client_secret, refresh_token, token_env=token_env)
    logger.info("Gmail authorization complete for space '%s' (%s)!", space, token_env)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Authorize Gmail account for a space.")
    parser.add_argument(
        "--space",
        "-s",
        default="default",
        help="Space profile to authorize (e.g. default, work, study)",
    )
    parser.add_argument("--port", "-p", type=int, default=8080, help="Local redirect port")
    cli_args = parser.parse_args()

    run_auth(port=cli_args.port, space=cli_args.space)
