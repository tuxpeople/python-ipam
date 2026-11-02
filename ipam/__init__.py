"""IPAM Application Factory."""

import os
from urllib.parse import urlsplit

from flask import Flask, flash, redirect, request, url_for
from flask_wtf.csrf import CSRFError

from ipam.cli import init_cli
from ipam.config import INSECURE_SECRET_KEYS, config
from ipam.extensions import csrf, db, limiter, migrate


def create_app(config_name=None, config_overrides=None):
    """Create and configure the Flask application.

    Args:
        config_name: Configuration name ('development', 'production', or None for default)
        config_overrides: Optional mapping applied on top of the selected
            configuration *before* extensions are initialized. Settings
            such as ``SQLALCHEMY_DATABASE_URI`` only take effect here;
            changing ``app.config`` afterwards does not rebind the engine.

    Returns:
        Configured Flask application instance
    """
    app = Flask(
        __name__, template_folder="../templates", static_folder="../static"
    )

    # Load configuration
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "default")
    app.config.from_object(config[config_name])
    if config_overrides:
        app.config.update(config_overrides)
    if (
        config_name == "production"
        and app.config.get("SECRET_KEY") in INSECURE_SECRET_KEYS
    ):
        app.logger.warning(
            "SECRET_KEY is a published placeholder; sessions and CSRF tokens "
            "can be forged. Set SECRET_KEY to a random value, e.g. "
            "python -c 'import secrets; print(secrets.token_hex(32))'."
        )

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    csrf.init_app(app)

    @app.context_processor
    def inject_app_version():
        return {"app_version": app.config["APP_VERSION"]}

    # Import models for Flask-Migrate/Alembic
    # Register blueprints
    from ipam.api import api_bp, configure_api
    from ipam.models import Host, Network  # noqa: F401
    from ipam.web import web_bp

    configure_api(app)
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp)
    # The REST API authenticates with tokens, not browser cookies.
    csrf.exempt(api_bp)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        flash(
            "The form was rejected because its security token is missing "
            "or expired. Please try again.",
            "error",
        )
        return redirect(_same_origin_referrer() or url_for("web.index"))

    # Register export/import plugins
    with app.app_context():
        from exporters import register_exporter
        from exporters.csv_exporter import CSVExporter
        from exporters.dnsmasq_exporter import DNSmasqExporter
        from exporters.json_exporter import JSONExporter
        from importers import register_importer
        from importers.csv_importer import CSVImporter
        from importers.json_importer import JSONImporter

        register_exporter("csv", CSVExporter())
        register_exporter("json", JSONExporter())
        register_exporter("dnsmasq", DNSmasqExporter("combined"))
        register_exporter("dnsmasq-dns", DNSmasqExporter("dns"))
        register_exporter("dnsmasq-dhcp", DNSmasqExporter("dhcp"))
        register_importer("csv", CSVImporter())
        register_importer("json", JSONImporter())

    init_cli(app)

    return app


def _same_origin_referrer():
    """Return the referrer if it points back to this application."""
    referrer = request.referrer
    if not referrer:
        return None
    target = urlsplit(referrer)
    if target.netloc != urlsplit(request.host_url).netloc:
        return None
    return referrer
