"""Web UI Blueprint for IPAM."""

from flask import Blueprint

# Create blueprint without url_prefix to maintain backward compatibility
# Routes will have 'web.' prefix in endpoint names but root URL paths
web_bp = Blueprint("web", __name__)

# Import routes after blueprint is created to avoid circular imports
from ipam.web import routes
