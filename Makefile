.PHONY: help install test run clean docker-build docker-run

help: ## Zeige verfügbare Befehle
	@echo "Verfügbare Befehle:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Installiere Dependencies
	pip install -r requirements.txt

test: ## Führe Tests aus
	./run_tests.sh

test-quick: ## Führe Tests ohne Coverage aus
	pytest -v

run: ## Starte die Anwendung lokal
	python app.py

clean: ## Bereinige temporäre Dateien
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

docker-build: ## Baue Docker-Image
	docker build -t python-ipam .

docker-run: ## Starte Container
	docker run -p 5000:5000 python-ipam

docker-dev: ## Starte Entwicklungsumgebung mit Docker
	docker-compose --profile dev up

docker-prod: ## Starte Produktionsumgebung mit Docker
	docker-compose up -d

setup-dev: ## Setup für lokale Entwicklung
	python -m venv venv
	@echo "Aktiviere die virtuelle Umgebung mit:"
	@echo "source venv/bin/activate"
	@echo "Dann führe 'make install' aus"