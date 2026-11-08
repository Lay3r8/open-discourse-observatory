#!/bin/sh
set -eu

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  if ! docker info >/dev/null 2>&1; then
    cat >&2 <<'EOF'
Docker is installed, but the current user cannot reach the Docker daemon.

Check that Docker is running:
  sudo systemctl enable --now docker

Typical Linux permission fix:
  sudo usermod -aG docker "$USER"

Then log out and back in, or start a shell with the new group:
  newgrp docker

Verify with:
  docker info

Security note: membership in the docker group is effectively root-equivalent.
EOF
    exit 126
  fi
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
