#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"

usage() {
  cat <<'EOF'
Usage: scripts/update_frontend.sh [--install]

Builds the Flower frontend assets and produces a Python wheel in frontend/dist/.

Options:
  --install   Install the newest built wheel into the active virtualenv.
EOF
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Error: missing required command: $1" >&2
    exit 1
  fi
}

require_cmd npm
require_cmd uv

do_install=0
while (( "$#" )); do
  case "$1" in
    --install)
      do_install=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Error: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

python_exe=""
if (( do_install )); then
  # Ensure we're installing into a virtual environment.
  # If none is active, try to auto-activate a local venv.
  if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    if [[ -f "$ROOT_DIR/.venv/bin/activate" ]]; then
      # shellcheck disable=SC1091
      source "$ROOT_DIR/.venv/bin/activate"
    elif [[ -f "$ROOT_DIR/venv/bin/activate" ]]; then
      # shellcheck disable=SC1091
      source "$ROOT_DIR/venv/bin/activate"
    else
      echo "Error: no active virtual environment detected." >&2
      echo "Activate one first (e.g. 'source .venv/bin/activate') or create it in .venv/" >&2
      exit 1
    fi
  fi

  if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    python_exe="$VIRTUAL_ENV/bin/python"
  fi

  if [[ -z "$python_exe" || ! -x "$python_exe" ]]; then
    echo "Error: could not determine the Python interpreter for the active environment." >&2
    exit 1
  fi
fi

pushd "$FRONTEND_DIR" >/dev/null

npm_install_cmd="install"
if [[ -f package-lock.json ]]; then
  npm_install_cmd="ci"
fi

if [[ ! -d node_modules ]]; then
  npm "$npm_install_cmd"
fi

npm run build
uv build

# Pick the newest wheel (avoid hard-coding the version).
shopt -s nullglob
wheels=(dist/*.whl)
shopt -u nullglob

if (( ${#wheels[@]} == 0 )); then
  echo "Error: no wheels found in $FRONTEND_DIR/dist after build" >&2
  exit 1
fi

# Sort by mtime: newest first.
latest_wheel="$(ls -t dist/*.whl | head -n 1)"
latest_wheel_path="$FRONTEND_DIR/$latest_wheel"

popd >/dev/null

echo "Built wheel: $latest_wheel_path"

if (( do_install )); then
  uv pip install --python "$python_exe" --reinstall "$latest_wheel_path"
  echo "Installed: $latest_wheel_path"
fi
