#!/usr/bin/env bash
#
# Set up (or migrate) the pyenv-virtualenv environment for this project.
# Reads the Python version and project name from pyproject.toml so there is
# a single source of truth (see .python-version / requires-python).
#
# Requires: pyenv, pyenv-virtualenv plugin.
set -Eeuo pipefail

ROOT_DIR="$(git -C "$(dirname "${0}")" rev-parse --show-toplevel)"
cd "${ROOT_DIR}"

# --- dependency checks -----------------------------------------------------
if ! command -v pyenv >/dev/null 2>&1; then
  echo "Error: pyenv is not installed or not on PATH" >&2
  exit 1
fi
if ! pyenv commands | grep -qx virtualenv; then
  echo "Error: the pyenv-virtualenv plugin is required" >&2
  exit 1
fi

# --- read config from pyproject.toml -------------------------------------
# requires-python = "==3.14.*"  ->  3.14
PYVERSION="$(grep -E '^[[:space:]]*requires-python[[:space:]]*=' pyproject.toml \
  | grep -oE '[0-9]+\.[0-9]+' | head -n1)"
# name = "python-ipam"  ->  python-ipam-env
ENVNAME="$(grep -E '^[[:space:]]*name[[:space:]]*=' pyproject.toml \
  | head -n1 | sed -E 's/.*"([^"]+)".*/\1/')-env"

if [[ -z "${PYVERSION}" || -z "${ENVNAME}" ]]; then
  echo "Error: could not read requires-python / name from pyproject.toml" >&2
  exit 1
fi
echo "Ziel: Python ${PYVERSION}, Environment ${ENVNAME}"

# --- ensure the interpreter is installed -------------------------------
if pyenv versions --bare --skip-envs --skip-aliases | grep -qE "^${PYVERSION}(\.[0-9]+)?$"; then
  echo "Python ${PYVERSION} bereits installiert"
else
  echo "Installiere Python ${PYVERSION}"
  pyenv install -s "${PYVERSION}"
fi

# patch version pyenv actually resolves PYVERSION to (e.g. 3.14 -> 3.14.7)
RESOLVED="$(pyenv latest "${PYVERSION}" 2>/dev/null || echo "${PYVERSION}")"

# --- create / migrate the virtualenv ----------------------------------
if ! pyenv versions --bare | grep -qx "${ENVNAME}"; then
  echo "Environment ${ENVNAME} wird angelegt"
  pyenv virtualenv "${PYVERSION}" "${ENVNAME}"
elif pyenv versions --bare --skip-aliases | grep -qx "${RESOLVED}/envs/${ENVNAME}"; then
  echo "Environment ${ENVNAME} nutzt bereits Python ${RESOLVED}"
else
  echo "Environment ${ENVNAME} hat eine veraltete Python-Version - wird neu aufgebaut"
  pyenv virtualenv-delete -f "${ENVNAME}"
  pyenv virtualenv "${PYVERSION}" "${ENVNAME}"
fi

pyenv local "${ENVNAME}"

# --- install dependencies -------------------------------------------
echo "Installiere Abhaengigkeiten"
pyenv exec python -m pip install --upgrade pip
pyenv exec python -m pip install -r requirements.txt -r requirements-dev.txt

echo "Fertig. '${ENVNAME}' ist via .python-version aktiv."
