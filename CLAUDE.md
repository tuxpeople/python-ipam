# CLAUDE.md - Python IPAM Project

Claude Code-specific configuration and standards for the Python IPAM project.

## Documentation Standards

**IMPORTANT LANGUAGE REQUIREMENT**:
- **ALL documentation MUST be written in English**
- This includes: README.md, API.md, FEATURES.md, REFACTORING.md, CLAUDE.md, code comments, commit messages
- German or other languages are NOT permitted in documentation

**DOCUMENTATION UPDATE POLICY**:
- **Every code change MUST be evaluated for documentation impact**
- Before committing ANY change, ask: "Does this require documentation updates?"
- Documentation files to check:
  - `README.md` - User-facing documentation, setup instructions
  - `API.md` - REST API endpoint documentation
  - `FEATURES.md` - Feature tracking and roadmap
  - `REFACTORING.md` - Architecture and refactoring notes
  - `CLAUDE.md` - This file, project standards
- Documentation updates should be committed together with code changes
- Never commit code without updating related documentation

## Project Overview

**Python IPAM** is a modern IP Address Management (IPAM) system based on:
- Flask 3.0 (Python Web Framework)
- SQLite/SQLAlchemy (Database)
- Bootstrap 5 + DataTables (Frontend)
- pytest (Testing Framework)
- Docker (Containerization)

## Code Style Rules

### Python (Google Style Guide)

**Formatter**: Black with 80 character line length
```bash
black . --line-length 80
```

**Linting**: Pylint with Google configuration
```bash
pylint --rcfile=https://google.github.io/styleguide/pylintrc app.py tests/
```

**Naming Conventions**:
- Modules/Packages: `lowercase_with_underscores`
- Classes: `CapWords` (e.g., `NetworkForm`, `HostModel`)
- Functions/Variables: `lowercase_with_underscores`
- Constants: `CAPS_WITH_UNDERSCORES`
- Private: `_leading_underscore`

**Import Order** (separated by blank lines):
```python
from __future__ import annotations

import os
import ipaddress

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

from ipam import db, Network, Host
```

### Dockerfile (Hadolint Standard)

Follow security best practices:
```dockerfile
FROM python:3.11-slim

# Security: Non-root user
RUN useradd -r -s /bin/false ipam
USER ipam

# Layer optimization
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# JSON notation for CMD
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

### Git Commits (Angular Convention)

**Format**:
```
<type>(<scope>): <short summary>

<body>

<footer>
```

**Types for this project**:
- `feat`: New IPAM features (Host/Network management)
- `fix`: Bug fixes in web UI or API
- `test`: Unit tests for models/routes/forms
- `docker`: Container configuration
- `docs`: README or API documentation

**Examples**:
```bash
feat(networks): add VLAN ID support
fix(hosts): resolve auto-detection for overlapping subnets
test(models): add network cascade delete tests
docker: optimize layer caching in Dockerfile
docs: update pyenv setup instructions
```

**IMPORTANT**: Do not use AI signatures in commits!

### Shell/Bash

For test scripts and setup automation:
```bash
#!/bin/bash

# Functions
function setup_venv() {
  local python_version="$1"
  echo "Setting up Python ${python_version}..."
}

# Prefer [[ ]]
if [[ -d "venv" ]]; then
  source venv/bin/activate
fi

# Quote variables
echo "PATH: ${PATH}"
```

## Project-Specific Standards

### Testing

**Test Structure**:
```
tests/
├── conftest.py              # Pytest fixtures (Application Factory)
├── test_models.py           # SQLAlchemy Model Tests
├── test_routes.py           # Flask Route Tests
├── test_forms.py            # WTForms Validation Tests
├── test_database.py         # Database initialization tests
├── test_export_import.py    # Export/Import plugin tests
└── test_crud_operations.py  # CRUD operation tests
```

**Test Commands**:
```bash
# All tests
pytest -v

# With coverage
pytest --cov=ipam --cov-report=html

# Specific tests
pytest tests/test_models.py::TestNetworkModel::test_network_properties

# Database tests
pytest tests/test_database.py -v
```

### Database Models

SQLAlchemy models in `ipam/models.py`:
```python
from ipam.extensions import db

class Network(db.Model):
    __tablename__ = 'networks'  # Explicit table names

    # Primary Keys as first column
    id = db.Column(db.Integer, primary_key=True)

    # Relationships with cascade definitions
    hosts = db.relationship('Host', backref='network_ref',
                           cascade='all, delete-orphan')

    # Properties for calculated values
    @property
    def total_hosts(self):
        return len(list(ipaddress.IPv4Network(
            f"{self.network}/{self.cidr}", strict=False
        ).hosts()))
```

### Flask Application Structure

**Application Factory Pattern** in `ipam/__init__.py`:
```python
from ipam.extensions import db
from ipam.config import config

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)

    from ipam.web import web_bp
    from ipam.api import api_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp)

    return app
```

### Flask Routes

**Web Routes** in `ipam/web/routes.py`:
```python
from ipam.web import web_bp
from ipam.extensions import db
from ipam.models import Network, Host

@web_bp.route('/')
def index():
    """Dashboard."""
    networks = Network.query.all()
    return render_template('index.html', networks=networks)
```

**API Routes** in `ipam/api/networks.py`:
```python
from flask_restx import Namespace, Resource
from ipam.extensions import db
from ipam.models import Network

api = Namespace('networks', description='Network operations')

@api.route('/')
class NetworkList(Resource):
    def get(self):
        """List all networks."""
        networks = Network.query.all()
        return {'data': [network.to_dict() for network in networks]}
```

### Templates

HTML/Jinja2 template standards:
- Bootstrap 5 CSS classes
- Responsive design
- DataTables for tables
- Bootstrap Icons (`bi-*`)

## Environment & Tools

### Local Development

**pyenv Setup**:
```bash
pyenv install 3.11.6
pyenv local 3.11.6
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Database Initialization**:
```bash
# Create database (on first start)
python3 -c "from ipam import create_app; from ipam.extensions import db; app = create_app(); app.app_context().push(); db.create_all()"
```

**Development Server**:
```bash
python app.py  # Flask dev server on :5000

# Available URLs:
# - Web Interface: http://localhost:5000
# - REST API: http://localhost:5000/api/v1
# - Swagger UI: http://localhost:5000/api/v1/docs
```

### Docker Development

**Development Container**:
```bash
docker-compose --profile dev up
```

**Production Container**:
```bash
docker-compose up -d
```

### Quality Assurance

**Linting/Formatting (local)**:
```bash
# Python Code
black . --line-length 80
pylint app.py tests/

# Dockerfile
hadolint Dockerfile

# Shell Scripts
shellcheck run_tests.sh
```

**Testing**:
```bash
./run_tests.sh  # Complete test suite with coverage
make test       # Makefile target
```

## API Documentation

**REST API Base URL**: `/api/v1`
**Swagger UI**: http://localhost:5000/api/v1/docs

**Main Endpoints**:

**Networks**:
- `GET /api/v1/networks` - List all networks (with filtering/pagination)
- `POST /api/v1/networks` - Create network
- `GET /api/v1/networks/{id}` - Get network
- `PUT /api/v1/networks/{id}` - Update network
- `DELETE /api/v1/networks/{id}` - Delete network

**Hosts**:
- `GET /api/v1/hosts` - List all hosts (with filtering/pagination)
- `POST /api/v1/hosts` - Create host
- `GET /api/v1/hosts/{id}` - Get host
- `PUT /api/v1/hosts/{id}` - Update host
- `DELETE /api/v1/hosts/{id}` - Delete host

**IP Management**:
- `GET /api/v1/ip/networks/{id}/next-ip` - Get next free IP
- `GET /api/v1/ip/networks/{id}/available-ips` - List all free IPs
- `GET /api/v1/ip/{ip_address}` - Query IP status

**Response Format**:
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total_items": 100,
    "total_pages": 2
  }
}
```

Complete documentation: **API.md**

## Deployment

**Container Registries**:
- Use specific tags, not `latest`
- Multi-stage builds for production

**Kubernetes** (if used):
```yaml
# Follow Kubernetes best practices
metadata:
  labels:
    app.kubernetes.io/name: python-ipam
    app.kubernetes.io/component: backend
```

## Troubleshooting

**Common Issues**:

1. **SQLite Lock Issues**:
   ```python
   # Use context manager
   with app.app_context():
       db.session.commit()
   ```

2. **pyenv Python not found**:
   ```bash
   pyenv rehash
   which python  # Should show pyenv version
   ```

3. **Docker Build Failures**:
   ```bash
   docker system prune  # Cleanup
   docker build --no-cache .
   ```

## Maintenance

**Dependencies Update**:
```bash
pip list --outdated
pip install -U package_name
pip freeze > requirements.txt
```

**Database Migrations** (on schema changes):
```python
# In Python Console
from ipam import create_app
from ipam.extensions import db

app = create_app()
with app.app_context():
    db.drop_all()  # Caution in production!
    db.create_all()
```

**Database Initialization** (Command line):
```bash
python3 -c "from ipam import create_app; from ipam.extensions import db; app = create_app(); app.app_context().push(); db.create_all()"
```

---

**Last Update**: 2025-10-03
**Maintainer**: Python IPAM Team

## Changelog

### 2025-10-03
- ✅ Implemented Application Factory Pattern
- ✅ REST API with Flask-RESTX and Swagger UI
- ✅ Modular Blueprint structure (ipam/web/ and ipam/api/)
- ✅ Fixed circular import issues
- ✅ Absolute database paths in ipam/config.py
- ✅ Extended test suite (test_database.py, test_crud_operations.py)
- ✅ Converted all documentation to English
- ✅ Added documentation update policy
