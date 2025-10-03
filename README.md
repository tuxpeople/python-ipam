# Python IPAM - IP Address Management System

A modern, web-based IP Address Management (IPAM) system built with Flask, SQLite, Bootstrap, and DataTables.

## Features

- 🌐 **Network Management**: Manage IP networks with CIDR notation
- 🖥️ **Host Management**: Track IP addresses, hostnames, and MAC addresses
- 🔌 **REST API**: Complete RESTful API with Swagger UI documentation
- 📊 **Dashboard**: Clear overview of network utilization
- 🔍 **Advanced Search**: DataTables integration for efficient data filtering
- 📱 **Responsive Design**: Bootstrap 5 for modern, mobile-friendly UI
- 🐳 **Container-ready**: Docker support for easy deployment
- ✅ **Fully Tested**: Comprehensive unit tests with pytest

## Local Development with pyenv

### Prerequisites

1. **Install pyenv** (if not already installed):

   **macOS with Homebrew:**
   ```bash
   brew install pyenv
   ```

   **Linux/macOS with curl:**
   ```bash
   curl https://pyenv.run | bash
   ```

2. **Shell Configuration** (for bash/zsh):
   ```bash
   echo 'export PATH="$HOME/.pyenv/bin:$PATH"' >> ~/.bashrc
   echo 'eval "$(pyenv init -)"' >> ~/.bashrc
   echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc
   source ~/.bashrc
   ```

### Setup

1. **Clone repository:**
   ```bash
   git clone <repository-url>
   cd ipam
   ```

2. **Install and activate Python version:**
   ```bash
   pyenv install 3.13
   pyenv local 3.13
   ```

3. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or
   venv\\Scripts\\activate  # Windows
   ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env as needed
   ```

6. **Initialize database:**
   ```bash
   python3 -c "from ipam import create_app; from ipam.extensions import db; app = create_app(); app.app_context().push(); db.create_all()"
   ```

7. **Start application:**
   ```bash
   python app.py
   ```

   The application will be available at:
   - **Web Interface**: http://localhost:5000
   - **REST API**: http://localhost:5000/api/v1
   - **API Documentation (Swagger UI)**: http://localhost:5000/api/v1/docs

### Running Tests

```bash
# Run all tests
pytest

# Tests with coverage report
pytest --cov=app --cov-report=html

# Run specific tests
pytest tests/test_models.py

# Tests in watch mode (with pytest-watch)
pip install pytest-watch
ptw
```

## Docker Deployment

### Production Container (Chainguard Distroless)

The production Docker image is built on **Chainguard distroless Python images** for maximum security:

**Security Features:**
- ✅ **0 CRITICAL/HIGH vulnerabilities** (Trivy scanned)
- ✅ Multi-stage build with minimal attack surface
- ✅ Distroless runtime (no shell, package manager)
- ✅ Runs as nonroot user (UID 65532)
- ✅ Includes SBOM (Software Bill of Materials)
- ✅ Python 3.13

**Image Details:**
- **Size**: ~50-100MB (vs 200-300MB for standard Python images)
- **Base**: cgr.dev/chainguard/python:latest (distroless)
- **Registry**: ghcr.io/tuxpeople/python-ipam

```bash
# Pull and run production image
docker pull ghcr.io/tuxpeople/python-ipam:latest
docker run -d -p 5000:5000 \
  -v $(pwd)/ipam.db:/app/ipam.db \
  ghcr.io/tuxpeople/python-ipam:latest

# Or use Docker Compose
docker-compose up -d

# With custom .env file
cp .env.example .env
# Edit .env for production settings
docker-compose up -d
```

### Development

```bash
# Development environment with hot-reload
docker-compose --profile dev up

# Or build locally
docker build -t python-ipam:dev .
docker run -p 5000:5000 python-ipam:dev
```

## REST API

The complete REST API is available at `/api/v1`. Interactive API documentation (Swagger UI) can be found at http://localhost:5000/api/v1/docs

### Main Endpoints:

**Networks:**
- `GET /api/v1/networks` - List all networks with filtering and pagination
- `GET /api/v1/networks/{id}` - Get specific network
- `POST /api/v1/networks` - Create new network
- `PUT /api/v1/networks/{id}` - Update network
- `DELETE /api/v1/networks/{id}` - Delete network

**Hosts:**
- `GET /api/v1/hosts` - List all hosts with filtering and pagination
- `GET /api/v1/hosts/{id}` - Get specific host
- `POST /api/v1/hosts` - Create new host
- `PUT /api/v1/hosts/{id}` - Update host
- `DELETE /api/v1/hosts/{id}` - Delete host

**IP Management:**
- `GET /api/v1/ip/networks/{id}/next-ip` - Get next available IP
- `GET /api/v1/ip/networks/{id}/available-ips` - List all available IPs
- `GET /api/v1/ip/{ip_address}` - Query IP address status

See [API.md](API.md) for complete documentation

## Project Structure

```
ipam/
├── app.py                 # Flask application entry point
├── requirements.txt       # Python dependencies
├── pytest.ini            # Pytest configuration
├── Dockerfile            # Docker container definition
├── docker-compose.yml    # Docker Compose configuration
├── .env.example          # Example environment variables
├── ipam/                 # Main application package
│   ├── __init__.py       # Application Factory
│   ├── extensions.py     # Flask extensions (SQLAlchemy)
│   ├── models.py         # Database models
│   ├── forms.py          # WTForms
│   ├── config.py         # Configuration
│   ├── api/              # REST API Blueprint
│   │   ├── __init__.py   # API Blueprint and Swagger
│   │   ├── models.py     # API serialization models
│   │   ├── networks.py   # Network endpoints
│   │   ├── hosts.py      # Host endpoints
│   │   └── ip_management.py  # IP management endpoints
│   └── web/              # Web Interface Blueprint
│       ├── __init__.py   # Web Blueprint
│       └── routes.py     # Web routes
├── templates/            # HTML Templates (Jinja2)
│   ├── base.html         # Base template
│   ├── index.html        # Dashboard
│   ├── networks.html     # Network overview
│   ├── hosts.html        # Host overview
│   ├── add_network.html  # Add network
│   ├── add_host.html     # Add host
│   ├── edit_network.html # Edit network
│   └── edit_host.html    # Edit host
├── exporters/            # Export plugins
│   ├── base_exporter.py  # Base exporter class
│   ├── csv_exporter.py   # CSV export
│   ├── json_exporter.py  # JSON export
│   └── dnsmasq_exporter.py  # DNSmasq config export
├── importers/            # Import plugins
│   ├── base_importer.py  # Base importer class
│   ├── csv_importer.py   # CSV import
│   └── json_importer.py  # JSON import
└── tests/                # Test suite
    ├── conftest.py       # Pytest fixtures
    ├── test_models.py    # Model tests
    ├── test_routes.py    # Route tests
    ├── test_forms.py     # Form tests
    ├── test_database.py  # Database tests
    ├── test_export_import.py  # Export/Import tests
    └── test_crud_operations.py  # CRUD tests
```

## Database Schema

### Networks Table
- `id` - Primary Key
- `network` - Network address (e.g., "192.168.1.0")
- `cidr` - CIDR suffix (e.g., 24)
- `broadcast_address` - Broadcast address
- `name` - Network name (optional)
- `domain` - DNS domain (optional)
- `vlan_id` - VLAN ID (optional)
- `description` - Description (optional)
- `location` - Location (optional)

### Hosts Table
- `id` - Primary Key
- `ip_address` - IP address (unique)
- `hostname` - Hostname (optional)
- `cname` - DNS alias/CNAME (optional)
- `mac_address` - MAC address (optional)
- `description` - Description (optional)
- `status` - Status (active/inactive/reserved)
- `network_id` - Foreign Key to Networks

## Development Guidelines

1. **Code Style**: Follow PEP 8
2. **Tests**: Write tests for new features
3. **Commits**: Use meaningful commit messages
4. **Branches**: Use feature branches for new development

## Technology Stack

- **Backend**: Flask 3.1, SQLAlchemy 2.0, Flask-RESTX
- **Frontend**: Bootstrap 5, jQuery, DataTables
- **Database**: SQLite (production-ready for small to medium deployments)
- **Testing**: pytest, pytest-flask (96 tests)
- **Containerization**: Docker (Chainguard distroless), Docker Compose
- **Security**: Trivy scanning, SBOM generation, multi-stage builds
- **CI/CD**: GitHub Actions (tests, security scans, docs deployment)

## License

[Specify license here]

## Contributing

Contributions are welcome! Please create issues for bug reports or feature requests.