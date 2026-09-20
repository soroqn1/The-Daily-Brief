"""Local FastAPI server for The Daily Brief."""

import logging
import os
import urllib.parse
from datetime import datetime
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from pydantic import BaseModel, Field

from the_daily_brief.auth import update_env_vars
from the_daily_brief.config import ConnectorInstance, get_config, is_valid_space_name
from the_daily_brief.connectors.registry import list_connector_types
from the_daily_brief.llm import test_llm_connection
from the_daily_brief.main import (
    generate_daily_brief,
    generate_email_audit,
    generate_global_feed,
    get_connectors_for_space,
)
from the_daily_brief.renderer import render_dashboard

logger = logging.getLogger(__name__)

app = FastAPI(
    title="The Daily Brief Server",
    description="Local web service for daily briefs, email audits, and connects.",
    version="0.2.0",
)

# Restrict CORS to local origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateSpaceRequest(BaseModel):
    name: str


class CreateConnectorRequest(BaseModel):
    type: str
    id: str | None = None
    name: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class PrepareAuthRequest(BaseModel):
    space: str
    client_id: str | None = None
    client_secret: str | None = None


@app.get("/api/connector-types")
async def get_connector_types() -> JSONResponse:
    """List all available connector types with setup guides and schema fields."""
    types = list_connector_types()
    return JSONResponse([t.to_dict() for t in types])


@app.get("/api/spaces")
async def get_spaces() -> JSONResponse:
    """List all configured spaces and their connected sources."""
    config = get_config()
    spaces = config.spaces or {"default": config.get_space("default")}
    data = {name: space.to_dict() for name, space in spaces.items()}
    return JSONResponse(data)


@app.post("/api/spaces")
async def create_space(req: CreateSpaceRequest) -> JSONResponse:
    """Create a new space."""
    config = get_config()
    clean_name = req.name.strip().lower().replace(" ", "_")
    if not clean_name or not is_valid_space_name(clean_name):
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid space name. "
                "Use alphanumeric characters, dashes, or underscores (max 64 chars)."
            ),
        )
    space = config.add_space(clean_name)
    return JSONResponse({"status": "ok", "space": space.to_dict()})


@app.delete("/api/spaces/{space}")
async def delete_space(space: str) -> JSONResponse:
    """Delete a space and its configuration."""
    if not is_valid_space_name(space):
        raise HTTPException(status_code=400, detail=f"Invalid space name '{space}'")
    config = get_config()
    if not config.remove_space(space):
        raise HTTPException(status_code=404, detail=f"Space '{space}' not found")
    return JSONResponse({"status": "ok", "space": space})


@app.get("/api/spaces/{space}/diagnostics")
async def space_diagnostics(space: str) -> JSONResponse:
    """Run real-time diagnostics on LLM and space connectors."""
    if not is_valid_space_name(space):
        raise HTTPException(status_code=400, detail=f"Invalid space name '{space}'")
    config = get_config()
    llm_ok, llm_msg, llm_reply = await test_llm_connection(config.llm.provider)

    connector_results: list[dict[str, Any]] = []
    connectors = get_connectors_for_space(config, space)
    for c in connectors:
        if hasattr(c, "test_connection"):
            c_ok, c_msg = await c.test_connection()
            connector_results.append(
                {
                    "id": getattr(c, "id", c.name),
                    "type": getattr(c, "name", "connector"),
                    "ok": c_ok,
                    "message": c_msg,
                }
            )
        else:
            connector_results.append(
                {
                    "id": getattr(c, "id", c.name),
                    "type": getattr(c, "name", "connector"),
                    "ok": True,
                    "message": "Ready",
                }
            )

    all_ok = llm_ok and all(r["ok"] for r in connector_results)
    return JSONResponse(
        {
            "space": space,
            "all_ok": all_ok,
            "llm": {
                "ok": llm_ok,
                "provider": config.llm.provider,
                "message": llm_msg,
                "reply": llm_reply,
            },
            "connectors": connector_results,
        }
    )


@app.post("/api/spaces/{space}/connectors")
async def add_connector(space: str, req: CreateConnectorRequest) -> JSONResponse:
    """Add or update a connector in a space."""
    if not is_valid_space_name(space):
        raise HTTPException(status_code=400, detail=f"Invalid space name '{space}'")
    config = get_config()
    if space not in config.spaces:
        config.add_space(space)

    existing_conns = config.get_space(space).connectors or []
    existing = next((c for c in existing_conns if c.type == req.type), None)
    conn_id = req.id or (existing.id if existing else f"{space}_{req.type}")
    conn_name = req.name or f"{req.type.capitalize()} Connector"
    conn_config = dict(req.config)

    # Automatic .env management for connectors with credentials
    if req.type == "gmail":
        token_env = (
            "GMAIL_REFRESH_TOKEN"
            if space == "default"
            else f"GMAIL_REFRESH_TOKEN_{space.upper().replace('-', '_')}"
        )
        conn_config["token_env"] = token_env

        client_id = str(
            conn_config.pop("client_id", None) or os.getenv("GMAIL_CLIENT_ID") or ""
        ).strip()
        client_secret = str(
            conn_config.pop("client_secret", None) or os.getenv("GMAIL_CLIENT_SECRET") or ""
        ).strip()
        refresh_token = str(conn_config.pop("refresh_token", None) or "").strip()

        if client_secret and ".apps.googleusercontent.com" in client_secret:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Client Secret cannot be a Client ID (contains .apps.googleusercontent.com). "
                    "Copy the Client Secret (starts with 'GOCSPX-') from Google Cloud Console."
                ),
            )

        env_updates = {}
        if client_id:
            env_updates["GMAIL_CLIENT_ID"] = client_id
        if client_secret:
            env_updates["GMAIL_CLIENT_SECRET"] = client_secret
        if refresh_token:
            env_updates[token_env] = refresh_token

        if env_updates:
            update_env_vars(env_updates)

    instance = ConnectorInstance(
        id=conn_id,
        type=req.type,
        name=conn_name,
        config=conn_config,
        enabled=req.enabled,
    )
    config.add_connector(space, instance)
    return JSONResponse({"status": "ok", "connector": instance.to_dict()})


@app.delete("/api/spaces/{space}/connectors/{conn_id}")
async def remove_connector(space: str, conn_id: str) -> JSONResponse:
    """Remove a connector from a space."""
    if not is_valid_space_name(space):
        raise HTTPException(status_code=400, detail=f"Invalid space name '{space}'")
    config = get_config()
    if not config.remove_connector(space, conn_id):
        raise HTTPException(
            status_code=404,
            detail=f"Connector '{conn_id}' not found in space '{space}'",
        )
    return JSONResponse({"status": "ok", "removed": conn_id})


@app.post("/api/auth/gmail/prepare")
async def prepare_gmail_auth(req: PrepareAuthRequest) -> JSONResponse:
    """Save client credentials prior to starting Google OAuth redirect."""
    if not is_valid_space_name(req.space):
        raise HTTPException(status_code=400, detail=f"Invalid space name '{req.space}'")
    updates: dict[str, str] = {}
    if req.client_id:
        updates["GMAIL_CLIENT_ID"] = req.client_id.strip()
    if req.client_secret:
        updates["GMAIL_CLIENT_SECRET"] = req.client_secret.strip()
    if updates:
        update_env_vars(updates)
    return JSONResponse({"status": "ok"})


@app.get("/api/auth/gmail/start")
async def auth_gmail_start(space: str = "default") -> Response:
    """Redirect to Google OAuth consent screen for a specific space."""
    if not is_valid_space_name(space):
        raise HTTPException(status_code=400, detail=f"Invalid space name '{space}'")
    client_id = (os.getenv("GMAIL_CLIENT_ID") or "").strip()
    if not client_id:
        raise HTTPException(
            status_code=400,
            detail="GMAIL_CLIENT_ID missing in environment. Enter Client ID first.",
        )
    # Loopback root URI is required by Google for Desktop OAuth clients
    redirect_uri = "http://localhost:8000"
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/gmail.readonly",
        "access_type": "offline",
        "prompt": "consent",
        "state": space,
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)


async def handle_gmail_oauth_code(
    code: str,
    space: str = "default",
    redirect_uri: str = "http://localhost:8000",
) -> Response:
    """Exchange authorization code with Google for refresh token and save to .env."""
    if not is_valid_space_name(space):
        return HTMLResponse(
            "<h2>Authorization Error</h2><p style='color:red;'>Invalid space name</p>",
            status_code=400,
        )
    client_id = (os.getenv("GMAIL_CLIENT_ID") or "").strip()
    client_secret = (os.getenv("GMAIL_CLIENT_SECRET") or "").strip()
    if not client_id or not client_secret:
        return HTMLResponse(
            "<h2>Authorization Error</h2>"
            "<p style='color:red;'>Missing GMAIL_CLIENT_ID or GMAIL_CLIENT_SECRET in .env</p>",
            status_code=400,
        )

    token_payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post("https://oauth2.googleapis.com/token", data=token_payload)
        if resp.status_code != 200:
            err_msg = resp.text
            try:
                err_msg = resp.json().get("error_description", resp.text)
            except Exception:
                pass
            return HTMLResponse(
                f"<h2>Google Authorization Error ({resp.status_code})</h2>"
                f"<p style='color:red;'>{err_msg}</p>"
                "<p>Please verify Client ID & Secret in Google Cloud Console.</p>"
                "<p><a href='/'>Return to Hub</a></p>",
                status_code=400,
            )
        tokens = resp.json()

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        return HTMLResponse(
            "<h2>Warning</h2><p>Google did not return a refresh token. "
            "Please revoke previous access in Google Account permissions and re-authorize.</p>",
            status_code=400,
        )

    token_env = (
        "GMAIL_REFRESH_TOKEN"
        if space == "default"
        else f"GMAIL_REFRESH_TOKEN_{space.upper().replace('-', '_')}"
    )
    update_env_vars({token_env: refresh_token})

    config = get_config()
    if space not in config.spaces:
        config.add_space(space)

    conn_id = f"{space}_gmail"
    config.add_connector(
        space,
        ConnectorInstance(
            id=conn_id,
            type="gmail",
            name=f"{space.capitalize()} Gmail",
            config={"token_env": token_env},
        ),
    )

    return HTMLResponse(
        f"""<!DOCTYPE html>
<html>
<head><title>Authorization Successful</title></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
             text-align: center; padding: 60px 20px; background: #fafafa;">
  <h2 style="font-family: Georgia, serif; font-size: 26px; margin-bottom: 12px;">
    ✅ Authorization Successful!
  </h2>
  <p style="color: #444; font-size: 15px; margin-bottom: 20px;">
    Saved refresh token to <code>.env</code> as <strong>{token_env}</strong>
    for space <strong>{space.upper()}</strong>.
  </p>
  <button onclick="if(window.opener){{window.opener.location.reload();}}window.close();"
          style="padding: 10px 20px; background: #111; color: #fff; border: none;
                 border-radius: 4px; font-size: 14px; cursor: pointer;">
    Close Window & Return
  </button>
  <script>
    if (window.opener) {{
      window.opener.location.reload();
      setTimeout(() => window.close(), 1200);
    }}
  </script>
</body>
</html>"""
    )


@app.get("/api/auth/gmail/callback", response_class=HTMLResponse)
async def auth_gmail_callback(code: str = Query(...), state: str = Query("default")) -> Response:
    """Handle callback when configured with explicit /api/auth/gmail/callback URI."""
    if not is_valid_space_name(state):
        return HTMLResponse(
            "<h2>Authorization Error</h2><p style='color:red;'>Invalid space name</p>",
            status_code=400,
        )
    return await handle_gmail_oauth_code(
        code=code,
        space=state,
        redirect_uri="http://localhost:8000/api/auth/gmail/callback",
    )


@app.get("/global/daily", response_class=HTMLResponse)
async def get_global_daily_feed(force: bool = Query(False)) -> Response:
    """Get or generate the unified Reddit-style global feed across all spaces."""
    config = get_config()
    target_dir = config.get_space_dir("global")
    html_path = target_dir / "daily.html"

    if not force and html_path.is_file():
        content = html_path.read_text(encoding="utf-8")
        return HTMLResponse(content=content)

    res = await generate_global_feed(force=force)
    if not res:
        raise HTTPException(status_code=500, detail="Failed to generate global feed")

    generated_html_path, _ = res
    content = generated_html_path.read_text(encoding="utf-8")
    return HTMLResponse(content=content)


@app.post("/global/daily")
async def generate_global_daily_feed_post() -> JSONResponse:
    """Force generate global feed via POST request."""
    res = await generate_global_feed(force=True)
    if not res:
        raise HTTPException(status_code=500, detail="Failed to generate global feed")

    html_path, md_path = res
    return JSONResponse(
        {
            "status": "ok",
            "space": "global",
            "type": "daily",
            "html_path": str(html_path),
            "md_path": str(md_path),
            "view_url": "/global/daily",
        }
    )


@app.get("/global/daily/raw", response_class=PlainTextResponse)
async def get_global_daily_raw_markdown() -> Response:
    """Get raw Markdown content of global feed for AI consumption."""
    config = get_config()
    target_dir = config.get_space_dir("global")
    md_path = target_dir / "daily.md"

    if not md_path.is_file():
        res = await generate_global_feed(force=False)
        if not res:
            raise HTTPException(
                status_code=404,
                detail="Global feed not found and generation failed.",
            )
        _, md_path = res

    content = md_path.read_text(encoding="utf-8")
    return PlainTextResponse(content=content)


@app.get("/{space}/daily", response_class=HTMLResponse)
async def get_daily_brief(space: str, force: bool = Query(False)) -> Response:
    """Get or generate the daily brief for a space."""
    if not is_valid_space_name(space):
        raise HTTPException(status_code=400, detail=f"Invalid space name '{space}'")
    config = get_config()
    target_dir = config.get_space_dir(space)
    html_path = target_dir / "daily.html"

    if not force and html_path.is_file():
        content = html_path.read_text(encoding="utf-8")
        return HTMLResponse(content=content)

    res = await generate_daily_brief(space_name=space, force=force)
    if not res:
        raise HTTPException(status_code=500, detail=f"Failed to generate daily brief for '{space}'")

    generated_html_path, _ = res
    content = generated_html_path.read_text(encoding="utf-8")
    return HTMLResponse(content=content)


@app.post("/{space}/daily")
async def generate_daily_brief_post(space: str) -> JSONResponse:
    """Force generate daily brief via POST request (e.g. from browser button)."""
    if not is_valid_space_name(space):
        raise HTTPException(status_code=400, detail=f"Invalid space name '{space}'")
    res = await generate_daily_brief(space_name=space, force=True)
    if not res:
        raise HTTPException(status_code=500, detail=f"Failed to generate daily brief for '{space}'")

    html_path, md_path = res
    return JSONResponse(
        {
            "status": "ok",
            "space": space,
            "type": "daily",
            "html_path": str(html_path),
            "md_path": str(md_path),
            "view_url": f"/{space}/daily",
        }
    )


@app.get("/{space}/daily/raw", response_class=PlainTextResponse)
async def get_daily_raw_markdown(space: str) -> Response:
    """Get raw Markdown content of daily brief for AI consumption."""
    if not is_valid_space_name(space):
        raise HTTPException(status_code=400, detail=f"Invalid space name '{space}'")
    config = get_config()
    target_dir = config.get_space_dir(space)
    md_path = target_dir / "daily.md"

    if not md_path.is_file():
        res = await generate_daily_brief(space_name=space, force=False)
        if not res:
            raise HTTPException(
                status_code=404,
                detail="Daily brief not found and generation failed.",
            )
        _, md_path = res

    content = md_path.read_text(encoding="utf-8")
    return PlainTextResponse(content=content)


@app.get("/{space}/email", response_class=HTMLResponse)
async def get_email_audit(space: str, force: bool = Query(False)) -> Response:
    """Get or generate deep email audit for a space."""
    if not is_valid_space_name(space):
        raise HTTPException(status_code=400, detail=f"Invalid space name '{space}'")
    config = get_config()
    target_dir = config.get_space_dir(space)
    html_path = target_dir / "email.html"

    if not force and html_path.is_file():
        content = html_path.read_text(encoding="utf-8")
        return HTMLResponse(content=content)

    res = await generate_email_audit(space_name=space, force=force)
    if not res:
        raise HTTPException(status_code=500, detail=f"Failed to generate email audit for '{space}'")

    generated_html_path, _ = res
    content = generated_html_path.read_text(encoding="utf-8")
    return HTMLResponse(content=content)


@app.post("/{space}/email")
async def generate_email_audit_post(space: str) -> JSONResponse:
    """Force generate email audit via POST request (e.g. from browser button)."""
    if not is_valid_space_name(space):
        raise HTTPException(status_code=400, detail=f"Invalid space name '{space}'")
    res = await generate_email_audit(space_name=space, force=True)
    if not res:
        raise HTTPException(status_code=500, detail=f"Failed to generate email audit for '{space}'")

    html_path, md_path = res
    return JSONResponse(
        {
            "status": "ok",
            "space": space,
            "type": "email",
            "html_path": str(html_path),
            "md_path": str(md_path),
            "view_url": f"/{space}/email",
        }
    )


@app.get("/{space}/email/raw", response_class=PlainTextResponse)
async def get_email_raw_markdown(space: str) -> Response:
    """Get raw Markdown content of email audit for AI consumption."""
    if not is_valid_space_name(space):
        raise HTTPException(status_code=400, detail=f"Invalid space name '{space}'")
    config = get_config()
    target_dir = config.get_space_dir(space)
    md_path = target_dir / "email.md"

    if not md_path.is_file():
        res = await generate_email_audit(space_name=space, force=False)
        if not res:
            raise HTTPException(
                status_code=404,
                detail="Email audit not found and generation failed.",
            )
        _, md_path = res

    content = md_path.read_text(encoding="utf-8")
    return PlainTextResponse(content=content)


@app.get("/settings", response_class=HTMLResponse)
@app.get("/", response_class=HTMLResponse)
async def index(
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
) -> Response:
    """Dashboard listing spaces, connects, guides, diagnostics, and report triggers."""
    if error:
        return HTMLResponse(
            f"<h2>Google Authorization Error</h2><p style='color:red;'>{error}</p>"
            "<p><a href='/'>Return to Hub</a></p>",
            status_code=400,
        )
    if code:
        return await handle_gmail_oauth_code(
            code=code,
            space=state or "default",
            redirect_uri="http://localhost:8000",
        )

    config = get_config()
    spaces = config.spaces or {"default": config.get_space("default")}
    connector_types = [t.to_dict() for t in list_connector_types()]

    today_formatted = datetime.now().strftime("%A, %B %d, %Y").upper()
    accent_palette = ["carmine", "indigo", "amber", "forest"]

    cards: list[dict[str, Any]] = []
    for idx, (space_name, space_cfg) in enumerate(spaces.items()):
        space_dir = config.get_space_dir(space_name)
        daily_html = space_dir / "daily.html"
        daily_md = space_dir / "daily.md"
        email_html = space_dir / "email.html"

        daily_time = (
            datetime.fromtimestamp(daily_html.stat().st_mtime).strftime("%H:%M")
            if daily_html.is_file()
            else None
        )
        email_time = (
            datetime.fromtimestamp(email_html.stat().st_mtime).strftime("%H:%M")
            if email_html.is_file()
            else None
        )

        source_count = len(space_cfg.connectors) if space_cfg.connectors else 0
        source_count_str = f"{source_count} {'SOURCE' if source_count == 1 else 'SOURCES'}"

        conn_list = []
        if space_cfg.connectors:
            for c in space_cfg.connectors:
                c_details = [
                    f"{k}: {v}"
                    for k, v in c.config.items()
                    if k not in ("refresh_token", "space_name")
                ]
                conn_list.append(
                    {
                        "id": c.id,
                        "type": c.type,
                        "name": c.name,
                        "details_str": ", ".join(c_details),
                    }
                )

        cards.append(
            {
                "name": space_name,
                "dir": str(space_dir),
                "accent_color": accent_palette[idx % len(accent_palette)],
                "desk_num": f"{idx + 1:02d}",
                "source_count_str": source_count_str,
                "connectors": conn_list,
                "daily_time": daily_time,
                "daily_has_file": daily_html.is_file(),
                "daily_md_path": str(daily_md),
                "email_time": email_time,
                "email_has_file": email_html.is_file(),
            }
        )

    html = render_dashboard(
        config=config,
        cards=cards,
        connector_types=connector_types,
        spaces_list=list(spaces.keys()),
        today_formatted=today_formatted,
    )
    return HTMLResponse(content=html)
