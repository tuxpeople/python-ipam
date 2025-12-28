"""API Blueprint for IPAM REST API."""

from flask import Blueprint, current_app, jsonify, request
from flask_restx import Api

from ipam.extensions import limiter

# Create API blueprint
api_bp = Blueprint("api", __name__, url_prefix="/api/v1")

# Initialize Flask-RESTX API with OpenAPI documentation
api = Api(
    api_bp,
    version="1.0",
    title="IPAM REST API",
    description="Complete RESTful API for IP Address Management (IPAM)",
    doc="/docs",
)


def _get_token():
    """Extract API token from headers."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(None, 1)[1].strip()
    return request.headers.get("X-API-Key")


def _is_auth_exempt(path):
    """Return True if the path should bypass auth."""
    return path.endswith("/docs") or path.endswith("/swagger.json")


def _get_rate_limit():
    """Return the configured API rate limit."""
    return current_app.config.get("API_RATE_LIMIT", "200 per minute")


@limiter.request_filter
def _skip_rate_limits():
    return not current_app.config.get("RATELIMIT_ENABLED", True)


def configure_api(app):
    """Configure API auth and rate limiting."""
    if getattr(api_bp, "_auth_configured", False):
        return

    @api_bp.before_request
    def require_api_token():
        if request.method == "OPTIONS" or _is_auth_exempt(request.path):
            return None
        tokens = current_app.config.get("API_TOKENS", [])
        if not tokens:
            return None
        token = _get_token()
        if token in tokens:
            return None
        return jsonify({"message": "Unauthorized"}), 401

    api_bp._auth_configured = True
    limiter.limit(_get_rate_limit)(api_bp)


# Import after api is created to avoid circular imports
from ipam.api import backups, dhcp_ranges, hosts, ip_management, networks

# Register namespaces
api.add_namespace(networks.api, path="/networks")
api.add_namespace(hosts.api, path="/hosts")
api.add_namespace(ip_management.api, path="/ip")
api.add_namespace(dhcp_ranges.api, path="/dhcp-ranges")
api.add_namespace(backups.api, path="/backups")
