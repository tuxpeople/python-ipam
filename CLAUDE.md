# CLAUDE.md - Python IPAM Project

Claude Code-spezifische Konfiguration und Standards für das Python IPAM-Projekt.

## Projekt-Übersicht

**Python IPAM** ist eine moderne IP-Adress-Verwaltungssystem (IPAM) basierend auf:
- Flask 3.0 (Python Web Framework)
- SQLite/SQLAlchemy (Datenbank)
- Bootstrap 5 + DataTables (Frontend)
- pytest (Testing Framework)
- Docker (Containerisierung)

## Code-Style-Regeln

### Python (Google Style Guide)

**Formatter**: Black mit 80 Zeichen Zeilenlänge
```bash
black . --line-length 80
```

**Linting**: Pylint mit Google-Konfiguration
```bash
pylint --rcfile=https://google.github.io/styleguide/pylintrc app.py tests/
```

**Naming Conventions**:
- Module/Packages: `lowercase_with_underscores`
- Klassen: `CapWords` (z.B. `NetworkForm`, `HostModel`)
- Funktionen/Variablen: `lowercase_with_underscores`
- Konstanten: `CAPS_WITH_UNDERSCORES`
- Private: `_leading_underscore`

**Import-Reihenfolge** (mit Leerzeilen getrennt):
```python
from __future__ import annotations

import os
import ipaddress

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

from app import db, Network, Host
```

### Dockerfile (Hadolint Standard)

Beachte Security Best Practices:
```dockerfile
FROM python:3.11-slim

# Security: Non-root user
RUN useradd -r -s /bin/false ipam
USER ipam

# Layer-Optimierung
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# JSON notation für CMD
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

### Git Commits (Angular Convention)

**Format**:
```
<type>(<scope>): <short summary>

<body>

<footer>
```

**Types für dieses Projekt**:
- `feat`: Neue IPAM-Features (Host/Network-Management)
- `fix`: Bugfixes in Web-UI oder API
- `test`: Unit-Tests für Models/Routes/Forms
- `docker`: Container-Konfiguration
- `docs`: README oder API-Dokumentation

**Beispiele**:
```bash
feat(networks): add VLAN ID support
fix(hosts): resolve auto-detection for overlapping subnets
test(models): add network cascade delete tests
docker: optimize layer caching in Dockerfile
docs: update pyenv setup instructions
```

**WICHTIG**: Keine KI-Signaturen in Commits verwenden!

### Shell/Bash

Für Test-Scripts und Setup-Automation:
```bash
#!/bin/bash

# Funktionen
function setup_venv() {
  local python_version="$1"
  echo "Setting up Python ${python_version}..."
}

# [[ ]] bevorzugen
if [[ -d "venv" ]]; then
  source venv/bin/activate
fi

# Variablen quoten
echo "PATH: ${PATH}"
```

## Projektspezifische Standards

### Testing

**Test-Struktur**:
```
tests/
├── conftest.py          # Pytest fixtures
├── test_models.py       # SQLAlchemy Model Tests
├── test_routes.py       # Flask Route Tests
└── test_forms.py        # WTForms Validation Tests
```

**Test-Commands**:
```bash
# Alle Tests
pytest -v

# Mit Coverage
pytest --cov=app --cov-report=html

# Spezifische Tests
pytest tests/test_models.py::TestNetworkModel::test_network_properties
```

### Database Models

SQLAlchemy-Models folgen diesen Conventions:
```python
class Network(db.Model):
    __tablename__ = 'networks'  # Explizite Tabellennamen

    # Primary Keys als erste Spalte
    id = db.Column(db.Integer, primary_key=True)

    # Relationships mit cascade-Definitionen
    hosts = db.relationship('Host', backref='network_ref',
                           cascade='all, delete-orphan')

    # Properties für berechnete Werte
    @property
    def total_hosts(self):
        return len(list(ipaddress.IPv4Network(
            f"{self.network}/{self.cidr}", strict=False
        ).hosts()))
```

### Flask Routes

Route-Konventionen:
```python
@app.route('/api/networks')
def api_networks():
    """API-Endpunkt für Netzwerk-Daten."""
    networks = Network.query.all()
    return jsonify([{
        'id': n.id,
        'network': n.network,
        # ...weitere Felder
    } for n in networks])
```

### Templates

HTML/Jinja2-Template-Standards:
- Bootstrap 5 CSS-Klassen
- Responsive Design
- DataTables für Tabellen
- Bootstrap Icons (`bi-*`)

## Umgebung & Tools

### Lokale Entwicklung

**pyenv Setup**:
```bash
pyenv install 3.11.6
pyenv local 3.11.6
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Development Server**:
```bash
python app.py  # Flask dev server auf :5000
```

### Docker-Entwicklung

**Development Container**:
```bash
docker-compose --profile dev up
```

**Production Container**:
```bash
docker-compose up -d
```

### Quality Assurance

**Linting/Formatting (lokal)**:
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
./run_tests.sh  # Vollständige Test-Suite mit Coverage
make test       # Makefile-Target
```

## API-Dokumentation

**RESTful Endpunkte**:
- `GET /api/networks` - Alle Netzwerke
- `GET /api/hosts` - Alle Hosts

**Response Format**:
```json
{
  "data": [...],
  "status": "success",
  "message": "Optional message"
}
```

## Deployment

**Container-Registries**:
- Verwende spezifische Tags, nicht `latest`
- Multi-stage Builds für Production

**Kubernetes** (falls verwendet):
```yaml
# Folge Kubernetes Best Practices
metadata:
  labels:
    app.kubernetes.io/name: python-ipam
    app.kubernetes.io/component: backend
```

## Troubleshooting

**Häufige Probleme**:

1. **SQLite Lock Issues**:
   ```python
   # Verwende Context Manager
   with app.app_context():
       db.session.commit()
   ```

2. **pyenv Python nicht gefunden**:
   ```bash
   pyenv rehash
   which python  # Sollte pyenv-Version zeigen
   ```

3. **Docker Build Failures**:
   ```bash
   docker system prune  # Cleanup
   docker build --no-cache .
   ```

## Wartung

**Dependencies Update**:
```bash
pip list --outdated
pip install -U package_name
pip freeze > requirements.txt
```

**Database Migrations** (bei Schema-Änderungen):
```python
# In Python Console
from app import app, db
with app.app_context():
    db.drop_all()  # Vorsicht in Production!
    db.create_all()
```

---

**Letztes Update**: 2024-10-02
**Maintainer**: Python IPAM Team