"""API Blueprint for IPAM REST API."""

from flask import Blueprint
from flask_restx import Api

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

# Import after api is created to avoid circular imports
from ipam.api import dhcp_ranges, hosts, ip_management, networks

# Register namespaces
api.add_namespace(networks.api, path="/networks")
api.add_namespace(hosts.api, path="/hosts")
api.add_namespace(ip_management.api, path="/ip")
api.add_namespace(dhcp_ranges.api, path="/dhcp-ranges")
