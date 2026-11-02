"""Tests for CSRF protection of the web UI."""

import re

import pytest

from ipam.extensions import db
from ipam.models import Host, Network


@pytest.fixture
def csrf_client(app):
    """Client with CSRF protection enabled (the default fixture disables it)."""
    app.config["WTF_CSRF_ENABLED"] = True
    return app.test_client()


def _csrf_token(client, path="/"):
    response = client.get(path)
    match = re.search(
        rb'<meta name="csrf-token" content="([^"]+)"', response.data
    )
    assert match, "base template must expose the CSRF token"
    return match.group(1).decode()


def _create_host(app):
    with app.app_context():
        host = Host(ip_address="192.168.130.10", hostname="victim")
        db.session.add(host)
        db.session.commit()
        return host.id


class TestCsrfProtection:
    def test_post_without_token_is_rejected(self, app, csrf_client):
        host_id = _create_host(app)

        response = csrf_client.post(f"/delete_host/{host_id}")
        assert response.status_code == 302

        with app.app_context():
            assert db.session.get(Host, host_id) is not None

    def test_rejection_flashes_message(self, app, csrf_client):
        host_id = _create_host(app)

        response = csrf_client.post(
            f"/delete_host/{host_id}", follow_redirects=True
        )
        assert b"security token is missing or expired" in response.data

    def test_post_with_token_succeeds(self, app, csrf_client):
        host_id = _create_host(app)
        token = _csrf_token(csrf_client)

        response = csrf_client.post(
            f"/delete_host/{host_id}", data={"csrf_token": token}
        )
        assert response.status_code == 302

        with app.app_context():
            assert db.session.get(Host, host_id) is None

    def test_rejection_ignores_foreign_referrer(self, app, csrf_client):
        host_id = _create_host(app)

        response = csrf_client.post(
            f"/delete_host/{host_id}",
            headers={"Referer": "https://evil.example/attack"},
        )
        assert response.headers["Location"] == "/"

    def test_backup_restore_requires_token(self, csrf_client):
        response = csrf_client.post("/backups/anything.db/restore")
        assert response.status_code == 302
        assert response.headers["Location"] == "/"

    def test_api_is_exempt(self, app, csrf_client):
        response = csrf_client.post(
            "/api/v1/networks",
            json={"network": "10.99.0.0", "cidr": 24},
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 201


class TestFormsCarryToken:
    """Every POST form rendered by the UI must include a CSRF token."""

    @pytest.fixture
    def pages(self, app):
        with app.app_context():
            network = Network(
                network="192.168.131.0",
                cidr=24,
                broadcast_address="192.168.131.255",
            )
            db.session.add(network)
            db.session.commit()
            host = Host(ip_address="192.168.131.10", network_id=network.id)
            db.session.add(host)
            db.session.commit()
            return [
                "/",
                "/networks",
                "/hosts",
                "/backups",
                "/add_network",
                "/add_host",
                "/import",
                f"/networks/{network.id}",
                f"/hosts/{host.id}",
                f"/edit_network/{network.id}",
                f"/edit_host/{host.id}",
            ]

    def test_all_post_forms_include_token(self, csrf_client, pages):
        form_pattern = re.compile(
            rb'<form[^>]*method="POST"[^>]*>(.*?)</form>', re.S | re.I
        )
        for path in pages:
            html = csrf_client.get(path).data
            for body in form_pattern.findall(html):
                assert b'name="csrf_token"' in body, path
