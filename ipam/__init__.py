"""IPAM Application Factory."""

import os

from flask import Flask

from ipam.config import config
from ipam.cli import init_cli
from ipam.extensions import db, limiter, migrate


def create_app(config_name=None):
    """Create and configure the Flask application.

    Args:
        config_name: Configuration name ('development', 'production', or None for default)

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

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    # Register blueprints
    from ipam.api import api_bp, configure_api
    from ipam.web import web_bp

    configure_api(app)
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp)

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
