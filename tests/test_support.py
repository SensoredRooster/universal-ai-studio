from __future__ import annotations

import io
import json
import zipfile

import telemetry
from support import support_bp
from flask import Flask


def test_redaction_masks_secrets_and_bearer_tokens():
    data = {
        "client_secret": "abc",
        "nested": {"password": "xyz", "safe": "hello"},
    }
    result = telemetry.redact_mapping(data)
    assert result["client_secret"] == "[REDACTED]"
    assert result["nested"]["password"] == "[REDACTED]"
    assert result["nested"]["safe"] == "hello"
    assert "[REDACTED]" in telemetry.redact_text(
        "Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456"
    )


def test_support_routes_render_and_route_to_repo(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    app = Flask(__name__)
    app.register_blueprint(support_bp)
    client = app.test_client()

    page = client.get("/support")
    assert page.status_code == 200
    assert b"Support & diagnostics" in page.data
    assert b"Nothing is uploaded automatically" in page.data

    repo = client.get("/support/repository", follow_redirects=False)
    assert repo.status_code == 302
    assert repo.headers["Location"] == telemetry.REPO_URL


def test_support_bundle_contains_manifest_and_readme(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    telemetry.configure_telemetry(tmp_path / "logs")
    telemetry.log_event("test_event", "hello")
    bundle = telemetry.create_support_bundle({"ollama_ready": True})
    assert bundle.is_file()

    with zipfile.ZipFile(bundle) as zf:
        names = set(zf.namelist())
        assert "diagnostics/manifest.json" in names
        assert "README.txt" in names
        manifest = json.loads(zf.read("diagnostics/manifest.json"))
        assert manifest["session_id"]
        assert manifest["health"]["ollama_ready"] is True
