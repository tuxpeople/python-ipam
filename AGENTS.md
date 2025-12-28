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

## Release Guardrails

- Do not tag or create a release unless the latest CI build is successful.

## Testing Expectations

- Add or update tests for new features and behavior changes.

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
pyenv install 3.13
pyenv local 3.13
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

### Container Images

**Production Images** (Chainguard distroless):
- **Registry**: ghcr.io/tuxpeople/python-ipam
- **Base**: cgr.dev/chainguard/python:latest (distroless)
- **Security**: 0 CRITICAL/HIGH vulnerabilities (Trivy scanned)
- **Size**: ~50-100MB (multi-stage build)
- **User**: nonroot (UID 65532)
- **Python**: 3.13

**Tags**:
- `latest` - Always points to latest stable release
- `1.0.0` - Specific patch version
- `1.0` - Minor version (updates with new patches)
- `1` - Major version (updates with new minors/patches)
- `main-<sha>` - Git commit SHA for main branch builds

**Multi-stage Build**:
```dockerfile
# Stage 1: Build dependencies in -dev image
FROM cgr.dev/chainguard/python:latest-dev AS build
RUN python -m venv /tmp/venv && \
    /tmp/venv/bin/pip install --upgrade 'pip<25.2' setuptools wheel

# Stage 2: Install Python packages
FROM build AS build-venv
COPY requirements.txt /tmp/requirements.txt
RUN /tmp/venv/bin/pip install -r /tmp/requirements.txt

# Stage 3: Minimal runtime image (distroless)
FROM cgr.dev/chainguard/python:latest
COPY --from=build-venv /tmp/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN mkdir -p /tmp && chmod 1777 /tmp
```

**Kubernetes** (if used):
```yaml
# Follow Kubernetes best practices
metadata:
  labels:
    app.kubernetes.io/name: python-ipam
    app.kubernetes.io/version: "1.0.0"
    app.kubernetes.io/component: backend
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 65532
    fsGroup: 65532
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

## Release Process

### Semantic Versioning

This project follows [Semantic Versioning 2.0.0](https://semver.org/):

**Version Format**: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes (API changes, database schema changes)
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)

**Examples**:
- `v1.0.0` - First production release
- `v1.1.0` - New features (e.g., subnet calculator)
- `v1.1.1` - Bug fixes
- `v2.0.0` - Breaking changes (e.g., database schema migration)

### Creating a Release

**IMPORTANT**: Every version MUST have:
1. Git tag (annotated)
2. GitHub Release with changelog
3. Docker image published to GHCR

**Release Checklist**:

1. **Update Version** (if not already done):
   ```bash
   # Update version in relevant files if needed
   # (Currently no __version__ file, but could be added)
   ```

2. **Run Full Test Suite**:
   ```bash
   pytest -v
   black . --check --line-length 80
   hadolint Dockerfile
   ```

3. **Update Documentation**:
   - Check README.md, API.md, FEATURES.md for accuracy
   - Update CLAUDE.md changelog (see below)
   - Ensure all recent changes are documented

4. **Create Git Tag**:
   ```bash
   # Create annotated tag with version (must start with 'v' for CI/CD)
   git tag -a v1.0.0 -m "v1.0.0"

   # Push tag to GitHub (triggers Docker build)
   git push origin v1.0.0
   ```

5. **Create GitHub Release**:
   ```bash
   # Create release with changelog (title should be version only)
   gh release create v1.0.0 \
     --title "v1.0.0" \
     --notes-file /tmp/release-notes.md
   ```

   **Release Notes Template** (`/tmp/release-notes.md`):
   ```markdown
   # Python IPAM v1.0.0

   Brief description of the release.

   ## 🚀 Features
   - New feature 1
   - New feature 2

   ## 🐛 Bug Fixes
   - Fix for issue #123

   ## 🔒 Security
   - Security improvements

   ## 📦 Container Image
   \`\`\`bash
   docker pull ghcr.io/tuxpeople/python-ipam:1.0.0
   docker pull ghcr.io/tuxpeople/python-ipam:1.0
   docker pull ghcr.io/tuxpeople/python-ipam:1
   docker pull ghcr.io/tuxpeople/python-ipam:latest
   \`\`\`

   ## 🔄 Migration Notes
   - Breaking changes (if any)
   - Upgrade instructions

   ## 📝 Full Changelog
   https://github.com/tuxpeople/python-ipam/compare/v0.9.0...v1.0.0
   ```

6. **Verify Docker Image**:
   ```bash
   # CI/CD automatically builds and pushes to GHCR on tag push
   # Verify all tags are available (wait ~5 minutes for build)
   docker pull ghcr.io/tuxpeople/python-ipam:1.0.0
   docker pull ghcr.io/tuxpeople/python-ipam:1.0
   docker pull ghcr.io/tuxpeople/python-ipam:1
   docker pull ghcr.io/tuxpeople/python-ipam:latest
   ```

7. **Update CLAUDE.md Changelog** (after release):
   ```markdown
   ### 2025-10-03 - v1.0.0
   - ✅ First production release
   - ✅ Chainguard distroless migration (0 vulnerabilities)
   - ✅ Complete CI/CD pipeline
   ```

### Hotfix Release Process

For urgent bug fixes:

1. Create branch from tag:
   ```bash
   git checkout -b hotfix/v1.0.1 v1.0.0
   ```

2. Apply fix and test:
   ```bash
   # Make changes
   pytest -v
   git commit -m "fix: critical bug in network calculation"
   ```

3. Tag and release:
   ```bash
   git tag -a v1.0.1 -m "v1.0.1"
   git push origin v1.0.1
   gh release create v1.0.1 --title "v1.0.1" --notes "Critical bug fix"
   ```

4. Merge back to main:
   ```bash
   git checkout main
   git merge hotfix/v1.0.1
   git push origin main
   ```

### CI/CD Integration

The GitHub Actions workflow automatically:
- Builds Docker image on tag push (tags starting with `v`)
- Generates SBOM with Anchore
- Scans with Trivy (fails on CRITICAL/HIGH)
- Pushes to GHCR with multiple version tags
- Creates tags: `1.0.0`, `1.0`, `1`, `latest` (from Git tag `v1.0.0`)

---

**Last Update**: 2025-10-03
**Maintainer**: Python IPAM Team

## Changelog

### 2025-10-03 - v1.0.0 Production Release
- ✅ **Security Hardening**: Migrated to Chainguard distroless Python images
- ✅ **Security Achievement**: Reduced vulnerabilities from 275+ to **0** (100% reduction)
- ✅ **Container Optimization**: Multi-stage build, image size reduced to ~50-100MB
- ✅ **CI/CD Pipeline**: Automated testing, security scanning (Trivy), SBOM generation
- ✅ **GitHub Infrastructure**: Issue templates, project roadmap, automated workflows
- ✅ **Extensible Export/Import**: Plugin-based architecture (IPAM-004)
- ✅ **Documentation**: Complete English documentation, GitHub Pages deployment
- ✅ **Test Suite**: 96 tests passing, all SQLAlchemy 2.0 deprecations fixed
- ✅ **Release Process**: Established semantic versioning with Git tags and GitHub releases
- ✅ **REST API**: Flask-RESTX with Swagger UI at /api/v1/docs
- ✅ **Application Factory Pattern**: Modular Blueprint structure
- ✅ **Python 3.13**: Upgraded to latest Python version
