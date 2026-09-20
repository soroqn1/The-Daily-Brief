"""Tests for FastAPI local server endpoints."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from the_daily_brief.config import Config
from the_daily_brief.server import app


def test_index_dashboard(tmp_path: Path) -> None:
    """Test root dashboard returns HTML with spaces cards."""
    dummy_config = Config(output_dir=tmp_path, storage_dir=tmp_path / "saves")
    dummy_config.ensure_directories()

    client = TestClient(app)
    with patch("the_daily_brief.server.get_config", return_value=dummy_config):
        response = client.get("/")
        assert response.status_code == 200
        assert "The Daily Brief — Local Hub" in response.text
        assert "Space: DEFAULT" in response.text


def test_get_daily_existing(tmp_path: Path) -> None:
    """Test GET /{space}/daily serves existing HTML without regenerating."""
    dummy_config = Config(output_dir=tmp_path, storage_dir=tmp_path / "saves")
    space_dir = dummy_config.get_space_dir("work")
    html_file = space_dir / "daily.html"
    html_file.write_text("<h1>Work Daily Brief Cached</h1>", encoding="utf-8")

    client = TestClient(app)
    with patch("the_daily_brief.server.get_config", return_value=dummy_config):
        response = client.get("/work/daily")
        assert response.status_code == 200
        assert "Work Daily Brief Cached" in response.text


def test_get_daily_generates_when_missing(tmp_path: Path) -> None:
    """Test GET /{space}/daily generates fresh when file doesn't exist."""
    dummy_config = Config(output_dir=tmp_path, storage_dir=tmp_path / "saves")
    space_dir = dummy_config.get_space_dir("work")
    html_file = space_dir / "daily.html"
    md_file = space_dir / "daily.md"
    html_file.write_text("<h1>Newly Generated</h1>", encoding="utf-8")
    md_file.write_text("# Newly Generated", encoding="utf-8")

    client = TestClient(app)
    with (
        patch("the_daily_brief.server.get_config", return_value=dummy_config),
        patch(
            "the_daily_brief.server.generate_daily_brief",
            new=AsyncMock(return_value=(html_file, md_file)),
        ),
    ):
        response = client.get("/work/daily?force=true")
        assert response.status_code == 200
        assert "Newly Generated" in response.text


def test_post_daily_generates(tmp_path: Path) -> None:
    """Test POST /{space}/daily returns JSON with paths."""
    html_file = tmp_path / "daily.html"
    md_file = tmp_path / "daily.md"

    client = TestClient(app)
    with patch(
        "the_daily_brief.server.generate_daily_brief",
        new=AsyncMock(return_value=(html_file, md_file)),
    ):
        response = client.post("/study/daily")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["space"] == "study"
        assert data["type"] == "daily"
        assert data["view_url"] == "/study/daily"


def test_get_email_existing(tmp_path: Path) -> None:
    """Test GET /{space}/email serves existing HTML."""
    dummy_config = Config(output_dir=tmp_path, storage_dir=tmp_path / "saves")
    space_dir = dummy_config.get_space_dir("work")
    html_file = space_dir / "email.html"
    html_file.write_text("<h1>Work Email Audit Cached</h1>", encoding="utf-8")

    client = TestClient(app)
    with patch("the_daily_brief.server.get_config", return_value=dummy_config):
        response = client.get("/work/email")
        assert response.status_code == 200
        assert "Work Email Audit Cached" in response.text


def test_post_email_generates(tmp_path: Path) -> None:
    """Test POST /{space}/email returns JSON."""
    html_file = tmp_path / "email.html"
    md_file = tmp_path / "email.md"

    client = TestClient(app)
    with patch(
        "the_daily_brief.server.generate_email_audit",
        new=AsyncMock(return_value=(html_file, md_file)),
    ):
        response = client.post("/work/email")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["space"] == "work"
        assert data["type"] == "email"


def test_get_raw_markdown(tmp_path: Path) -> None:
    """Test GET /{space}/daily/raw and /{space}/email/raw returns plain text."""
    dummy_config = Config(output_dir=tmp_path, storage_dir=tmp_path / "saves")
    space_dir = dummy_config.get_space_dir("work")
    (space_dir / "daily.md").write_text("# Work Daily MD", encoding="utf-8")
    (space_dir / "email.md").write_text("# Work Email MD", encoding="utf-8")

    client = TestClient(app)
    with patch("the_daily_brief.server.get_config", return_value=dummy_config):
        resp_daily = client.get("/work/daily/raw")
        assert resp_daily.status_code == 200
        assert resp_daily.text == "# Work Daily MD"

        resp_email = client.get("/work/email/raw")
        assert resp_email.status_code == 200
        assert resp_email.text == "# Work Email MD"


def test_global_daily_endpoints(tmp_path: Path) -> None:
    """Test global daily feed HTML, POST, and raw Markdown endpoints."""
    dummy_config = Config(output_dir=tmp_path, storage_dir=tmp_path / "saves")
    global_dir = dummy_config.get_space_dir("global")
    html_file = global_dir / "daily.html"
    md_file = global_dir / "daily.md"
    html_file.write_text("<h1>Global Feed Unified</h1>", encoding="utf-8")
    md_file.write_text("# Global Feed MD", encoding="utf-8")

    client = TestClient(app)
    with patch("the_daily_brief.server.get_config", return_value=dummy_config):
        resp = client.get("/global/daily")
        assert resp.status_code == 200
        assert "Global Feed Unified" in resp.text

        resp_raw = client.get("/global/daily/raw")
        assert resp_raw.status_code == 200
        assert resp_raw.text == "# Global Feed MD"

    with patch(
        "the_daily_brief.server.generate_global_feed",
        new=AsyncMock(return_value=(html_file, md_file)),
    ):
        resp_post = client.post("/global/daily")
        assert resp_post.status_code == 200
        assert resp_post.json()["space"] == "global"


def test_api_connector_types() -> None:
    """Test GET /api/connector-types returns list of available connectors with guides."""
    client = TestClient(app)
    response = client.get("/api/connector-types")
    assert response.status_code == 200
    types = response.json()
    assert isinstance(types, list)
    type_ids = [t["type_id"] for t in types]
    assert "gmail" in type_ids
    assert "obsidian" in type_ids


def test_api_spaces_and_connectors_crud(tmp_path: Path) -> None:
    """Test creating, fetching, and deleting spaces and connectors via REST API."""
    dummy_config = Config(output_dir=tmp_path, storage_dir=tmp_path / "saves")
    dummy_config.ensure_directories()

    client = TestClient(app)
    with (
        patch("the_daily_brief.server.get_config", return_value=dummy_config),
        patch("the_daily_brief.server.update_env_vars"),
    ):
        # 1. List spaces
        resp = client.get("/api/spaces")
        assert resp.status_code == 200
        assert "default" in resp.json()

        # 2. Create new space
        resp = client.post("/api/spaces", json={"name": "crypto"})
        assert resp.status_code == 200
        assert resp.json()["space"]["name"] == "crypto"
        assert "crypto" in dummy_config.spaces

        # 3. Add connector to space
        resp = client.post(
            "/api/spaces/crypto/connectors",
            json={
                "type": "gmail",
                "name": "Crypto Alerts",
                "config": {
                    "client_id": "test_cid.apps.googleusercontent.com",
                    "client_secret": "GOCSPX-valid_secret",
                    "token_env": "GMAIL_CRYPTO_TOKEN",
                    "scan_hours": 24,
                },
            },
        )
        assert resp.status_code == 200
        conn_data = resp.json()["connector"]
        assert conn_data["name"] == "Crypto Alerts"
        conn_id = conn_data["id"]

        # Rejection test: client secret containing .apps.googleusercontent.com
        resp_bad = client.post(
            "/api/spaces/crypto/connectors",
            json={
                "type": "gmail",
                "config": {"client_secret": "bad-id.apps.googleusercontent.com"},
            },
        )
        assert resp_bad.status_code == 400

        # 4. Remove connector from space
        resp = client.delete(f"/api/spaces/crypto/connectors/{conn_id}")
        assert resp.status_code == 200
        assert resp.json()["removed"] == conn_id

        # 5. Delete space
        resp = client.delete("/api/spaces/crypto")
        assert resp.status_code == 200
        assert "crypto" not in dummy_config.spaces

        # 6. Delete nonexistent space returns 404
        resp = client.delete("/api/spaces/crypto")
        assert resp.status_code == 404


def test_gmail_connector_auto_env(tmp_path: Path) -> None:
    """Test adding Gmail connector automatically saves credentials and token to .env."""
    dummy_config = Config(output_dir=tmp_path, storage_dir=tmp_path / "saves")
    dummy_config.ensure_directories()

    client = TestClient(app)
    with (
        patch("the_daily_brief.server.get_config", return_value=dummy_config),
        patch("the_daily_brief.server.update_env_vars") as mock_update_env,
    ):
        resp = client.post(
            "/api/spaces/study/connectors",
            json={
                "type": "gmail",
                "name": "Study Gmail",
                "config": {
                    "client_id": "test_client_id.apps.googleusercontent.com",
                    "client_secret": "test_secret_123",
                    "refresh_token": "test_refresh_token_xyz",
                    "scan_hours": 12,
                },
            },
        )
        assert resp.status_code == 200
        conn_data = resp.json()["connector"]
        # token_env is automatically derived from connector type + space name
        assert conn_data["config"]["token_env"] == "GMAIL_REFRESH_TOKEN_STUDY"
        # Verify update_env_vars was called with all credentials
        mock_update_env.assert_called_once_with(
            {
                "GMAIL_CLIENT_ID": "test_client_id.apps.googleusercontent.com",
                "GMAIL_CLIENT_SECRET": "test_secret_123",
                "GMAIL_REFRESH_TOKEN_STUDY": "test_refresh_token_xyz",
            }
        )


def test_auth_gmail_prepare_and_start() -> None:
    """Test preparing OAuth credentials and getting authorization redirect."""
    client = TestClient(app)
    with patch("the_daily_brief.server.update_env_vars") as mock_update_env:
        resp = client.post(
            "/api/auth/gmail/prepare",
            json={
                "space": "study",
                "client_id": "my_client_id",
                "client_secret": "my_client_sec",
            },
        )
        assert resp.status_code == 200
        mock_update_env.assert_called_once_with(
            {
                "GMAIL_CLIENT_ID": "my_client_id",
                "GMAIL_CLIENT_SECRET": "my_client_sec",
            }
        )

    with patch.dict("os.environ", {"GMAIL_CLIENT_ID": "mock_id"}):
        resp_start = client.get("/api/auth/gmail/start?space=study", follow_redirects=False)
        assert resp_start.status_code == 307
        assert "accounts.google.com" in resp_start.headers["location"]
        assert "state=study" in resp_start.headers["location"]


def test_space_diagnostics(tmp_path: Path) -> None:
    """Test space diagnostics endpoint returns LLM and connectors status."""
    dummy_config = Config(output_dir=tmp_path, storage_dir=tmp_path / "saves")
    dummy_config.ensure_directories()

    client = TestClient(app)
    with (
        patch("the_daily_brief.server.get_config", return_value=dummy_config),
        patch(
            "the_daily_brief.server.test_llm_connection",
            new=AsyncMock(return_value=(True, "LLM OK", "Hello there!")),
        ),
    ):
        resp = client.get("/api/spaces/default/diagnostics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["space"] == "default"
        assert data["llm"]["ok"] is True
        assert data["llm"]["reply"] == "Hello there!"


def test_space_validation_endpoints() -> None:
    """Test that invalid space names are rejected with 400."""
    client = TestClient(app)

    # Path traversal / invalid space attempts
    assert client.get("/bad..traversal/daily").status_code == 400
    assert client.get("/api/spaces/bad..traversal/diagnostics").status_code == 400
    assert client.delete("/api/spaces/bad@traversal").status_code == 400

    # Invalid characters in space creation
    resp = client.post("/api/spaces", json={"name": "bad space!"})
    assert resp.status_code == 400
    assert "Invalid space name" in resp.json()["detail"]


def test_cors_policy() -> None:
    """Test that CORS restricts to localhost origins."""
    client = TestClient(app)

    # Allowed localhost origin
    resp = client.options(
        "/api/spaces",
        headers={
            "Origin": "http://localhost:8000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:8000"

    # Disallowed external origin
    resp_bad = client.options(
        "/api/spaces",
        headers={
            "Origin": "https://malicious-site.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in resp_bad.headers
