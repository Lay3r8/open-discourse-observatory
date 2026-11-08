#!/bin/sh
set -u

status=0

printf "mise: "
if command -v mise >/dev/null 2>&1; then
  mise --version | head -n 1
else
  echo "missing"
  status=1
fi

printf "uv: "
if command -v uv >/dev/null 2>&1; then
  uv --version
else
  echo "missing"
  status=1
fi

printf "project python: "
if command -v mise >/dev/null 2>&1; then
  if ! mise exec -- python --version 2>&1; then
    echo "unavailable (run: mise install)"
    status=1
  fi
else
  echo "unavailable"
  status=1
fi

printf "compose engine: "
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  docker compose version
elif command -v podman >/dev/null 2>&1 && podman compose --help >/dev/null 2>&1; then
  echo "podman compose"
elif command -v podman-compose >/dev/null 2>&1; then
  echo "podman-compose"
else
  echo "missing"
  status=1
fi

if [ -f .env ]; then echo ".env: present"; else echo ".env: missing (make setup creates it)"; fi

exit "$status"
