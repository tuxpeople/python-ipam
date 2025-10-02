#!/bin/bash

# Test-Runner-Script für Python IPAM

set -e

echo "=== Python IPAM Test Suite ==="
echo ""

# Virtuelle Umgebung aktivieren falls vorhanden
if [ -d "venv" ]; then
    echo "Aktiviere virtuelle Umgebung..."
    source venv/bin/activate
fi

# Dependencies prüfen
echo "Prüfe Dependencies..."
pip install -r requirements.txt > /dev/null 2>&1

# Linting (optional, falls installiert)
if command -v flake8 &> /dev/null; then
    echo "Führe Code-Linting aus..."
    flake8 app.py tests/ --max-line-length=100 --ignore=E501,W503
fi

# Tests ausführen
echo "Führe Unit-Tests aus..."
pytest -v

# Coverage-Report
echo ""
echo "Erstelle Coverage-Report..."
pytest --cov=app --cov-report=term-missing --cov-report=html

echo ""
echo "=== Tests abgeschlossen ==="
echo "Coverage-Report verfügbar unter: htmlcov/index.html"