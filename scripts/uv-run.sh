#!/bin/sh
set -eu

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

if command -v mise >/dev/null 2>&1; then
  exec mise exec -- uv run "$@"
fi

exec uv run "$@"
