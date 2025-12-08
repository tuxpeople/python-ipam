# Multi-stage build using Chainguard Python images for minimal attack surface
# Stage 1: Build virtualenv with all dependencies
# hadolint ignore=DL3007
FROM cgr.dev/chainguard/python:latest-dev AS build

# Create virtualenv and upgrade build tools
# Pin pip to avoid CVE-2025-8869 in pip 25.2 (when fix is available)
RUN python -m venv /home/nonroot/venv && \
    /home/nonroot/venv/bin/pip install --upgrade 'pip<25.2' setuptools wheel

# Stage 2: Install Python dependencies
FROM build AS build-venv
COPY --chown=nonroot:nonroot requirements.txt /tmp/requirements.txt
RUN /home/nonroot/venv/bin/pip install \
    --disable-pip-version-check \
    --no-cache-dir \
    -r /tmp/requirements.txt

# Stage 3: Final minimal runtime image
# hadolint ignore=DL3007
FROM cgr.dev/chainguard/python:latest

LABEL maintainer="Python IPAM"
LABEL description="IP Address Management System built with Flask"
LABEL org.opencontainers.image.source="https://github.com/tuxpeople/python-ipam"
LABEL org.opencontainers.image.description="Secure IPAM built on Chainguard distroless Python"

# Copy virtualenv from build stage
COPY --from=build-venv /home/nonroot/venv /home/nonroot/venv

# Set PATH to use virtualenv
ENV PATH="/home/nonroot/venv/bin:$PATH"

# Activate virtualenv by setting VIRTUAL_ENV
ENV VIRTUAL_ENV="/home/nonroot/venv"

# Set Flask environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Copy application code
WORKDIR /app
COPY --chown=nonroot:nonroot . /app

# Chainguard images already run as nonroot user
# No need for USER directive

EXPOSE 5000

# Healthcheck using Python instead of curl (not available in distroless)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/').read()" || exit 1

# Use virtualenv Python so installed packages (e.g., gunicorn) are available
ENTRYPOINT ["/home/nonroot/venv/bin/python"]
CMD ["-m","gunicorn","--bind","0.0.0.0:5000","--workers","4","--timeout","120","app:app"]
