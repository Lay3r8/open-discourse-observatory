#!/bin/sh
set -eu

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  exec docker compose "$@"
fi

if command -v podman >/dev/null 2>&1 && podman compose --help >/dev/null 2>&1; then
  exec podman compose "$@"
fi

if command -v podman-compose >/dev/null 2>&1; then
  exec podman-compose "$@"
fi

cat >&2 <<'EOF'
No Compose-compatible container engine was found.

Install either:
  - Docker + the Compose plugin, or
  - Podman + a Compose provider.

Then rerun:
  make doctor
  make bootstrap

You can also override the command explicitly, for example:
  make COMPOSE="podman compose" up
EOF
exit 127
