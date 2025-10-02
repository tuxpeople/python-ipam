# Python IPAM - IP Address Management System

Eine moderne, webbasierte IP-Adress-Verwaltungssystem (IPAM) gebaut mit Flask, SQLite, Bootstrap und DataTables.

## Features

- 🌐 **Netzwerk-Management**: Verwalten Sie IP-Netzwerke mit CIDR-Notation
- 🖥️ **Host-Management**: Verfolgen Sie IP-Adressen, Hostnamen und MAC-Adressen
- 📊 **Dashboard**: Übersichtliche Darstellung der Netzwerkauslastung
- 🔍 **Erweiterte Suche**: DataTables-Integration für effiziente Datenfilterung
- 📱 **Responsive Design**: Bootstrap 5 für moderne, mobile-freundliche UI
- 🐳 **Container-ready**: Docker-Unterstützung für einfache Bereitstellung
- ✅ **Vollständig getestet**: Umfassende Unit-Tests mit pytest

## Lokale Entwicklung mit pyenv

### Voraussetzungen

1. **pyenv installieren** (falls noch nicht vorhanden):

   **macOS mit Homebrew:**
   ```bash
   brew install pyenv
   ```

   **Linux/macOS mit curl:**
   ```bash
   curl https://pyenv.run | bash
   ```

2. **Shell-Konfiguration** (für bash/zsh):
   ```bash
   echo 'export PATH="$HOME/.pyenv/bin:$PATH"' >> ~/.bashrc
   echo 'eval "$(pyenv init -)"' >> ~/.bashrc
   echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc
   source ~/.bashrc
   ```

### Setup

1. **Repository klonen:**
   ```bash
   git clone <repository-url>
   cd ipam
   ```

2. **Python-Version installieren und aktivieren:**
   ```bash
   pyenv install 3.11.6
   pyenv local 3.11.6
   ```

3. **Virtuelle Umgebung erstellen:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # oder
   venv\\Scripts\\activate  # Windows
   ```

4. **Dependencies installieren:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Umgebungsvariablen konfigurieren:**
   ```bash
   cp .env.example .env
   # Bearbeiten Sie .env nach Bedarf
   ```

6. **Datenbank initialisieren:**
   ```bash
   python -c "from app import app, db; app.app_context().push(); db.create_all()"
   ```

7. **Anwendung starten:**
   ```bash
   python app.py
   ```

   Die Anwendung ist dann unter http://localhost:5000 erreichbar.

### Tests ausführen

```bash
# Alle Tests ausführen
pytest

# Tests mit Coverage-Report
pytest --cov=app --cov-report=html

# Nur spezifische Tests
pytest tests/test_models.py

# Tests im Watch-Modus (mit pytest-watch)
pip install pytest-watch
ptw
```

## Docker-Bereitstellung

### Entwicklung

```bash
# Entwicklungsumgebung mit Hot-Reload
docker-compose --profile dev up

# Oder direkter Docker-Build
docker build -t python-ipam .
docker run -p 5000:5000 python-ipam
```

### Produktion

```bash
# Produktionsumgebung
docker-compose up -d

# Mit eigener .env-Datei
cp .env.example .env
# Bearbeiten Sie .env für Produktionseinstellungen
docker-compose up -d
```

## API-Endpunkte

- `GET /api/networks` - Alle Netzwerke abrufen
- `GET /api/hosts` - Alle Hosts abrufen

## Projektstruktur

```
ipam/
├── app.py                 # Haupt-Flask-Anwendung
├── requirements.txt       # Python-Dependencies
├── pytest.ini           # Pytest-Konfiguration
├── Dockerfile            # Docker-Container-Definition
├── docker-compose.yml    # Docker-Compose-Konfiguration
├── .env.example          # Beispiel-Umgebungsvariablen
├── templates/            # HTML-Templates
│   ├── base.html         # Basis-Template
│   ├── index.html        # Dashboard
│   ├── networks.html     # Netzwerk-Übersicht
│   ├── hosts.html        # Host-Übersicht
│   ├── add_network.html  # Netzwerk hinzufügen
│   └── add_host.html     # Host hinzufügen
└── tests/                # Test-Suite
    ├── conftest.py       # Pytest-Konfiguration
    ├── test_models.py    # Modell-Tests
    ├── test_routes.py    # Route-Tests
    └── test_forms.py     # Formular-Tests
```

## Datenbank-Schema

### Networks Tabelle
- `id` - Primary Key
- `network` - Netzwerk-Adresse (z.B. "192.168.1.0")
- `cidr` - CIDR-Suffix (z.B. 24)
- `broadcast_address` - Broadcast-Adresse
- `vlan_id` - VLAN-ID (optional)
- `description` - Beschreibung
- `location` - Standort

### Hosts Tabelle
- `id` - Primary Key
- `ip_address` - IP-Adresse (einzigartig)
- `hostname` - Hostname (optional)
- `mac_address` - MAC-Adresse (optional)
- `description` - Beschreibung
- `status` - Status (active/inactive/reserved)
- `network_id` - Foreign Key zu Networks

## Entwicklungsrichtlinien

1. **Code-Style**: Folgen Sie PEP 8
2. **Tests**: Schreiben Sie Tests für neue Features
3. **Commits**: Verwenden Sie aussagekräftige Commit-Messages
4. **Branches**: Nutzen Sie Feature-Branches für neue Entwicklungen

## Technologie-Stack

- **Backend**: Flask 3.0, SQLAlchemy
- **Frontend**: Bootstrap 5, jQuery, DataTables
- **Database**: SQLite (produktionsreif für kleine bis mittlere Bereitstellungen)
- **Testing**: pytest, pytest-flask
- **Containerization**: Docker, Docker Compose

## Lizenz

[Lizenz hier angeben]

## Beiträge

Beiträge sind willkommen! Bitte erstellen Sie Issues für Bug-Reports oder Feature-Requests.