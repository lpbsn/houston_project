#!/usr/bin/env bash
# Idempotent Cloud Agent install: toolchains, lockfile dependencies, and API image.
set -euo pipefail

cd /workspace

export DEBIAN_FRONTEND=noninteractive
export PATH="/usr/local/bin:${PATH}"

NODE_VERSION=24.15.0
UV_VERSION=0.11.16
PYTHON_VERSION=3.13.13

sudo apt-get update -qq
sudo apt-get \
  -o Dpkg::Options::=--force-confdef \
  -o Dpkg::Options::=--force-confold \
  install -y --no-install-recommends \
  ca-certificates \
  curl \
  xz-utils \
  git \
  make \
  procps \
  python3 \
  tmux \
  docker.io \
  docker-compose-v2 \
  fuse-overlayfs \
  iptables

if [ -x /usr/sbin/iptables-legacy ]; then
  sudo update-alternatives --set iptables /usr/sbin/iptables-legacy
  sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy
fi

sudo mkdir -p /etc/docker
if [ ! -s /etc/docker/daemon.json ]; then
  printf '%s\n' '{"storage-driver":"fuse-overlayfs","iptables":true,"ip6tables":false}' |
    sudo tee /etc/docker/daemon.json >/dev/null
fi

printf '%s\n' 'export PATH="/usr/local/bin:${PATH}"' |
  sudo tee /etc/profile.d/houston-cloud-path.sh >/dev/null

if ! /usr/local/bin/node -v 2>/dev/null | grep -qx "v${NODE_VERSION}"; then
  curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" |
    sudo tar -xJ -C /usr/local --strip-components=1 --no-same-owner
fi

if ! /usr/local/bin/uv --version 2>/dev/null | grep -q "${UV_VERSION}"; then
  curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" | bash
  sudo ln -sfn "${HOME}/.local/bin/uv" /usr/local/bin/uv
  sudo ln -sfn "${HOME}/.local/bin/uvx" /usr/local/bin/uvx
fi

if ! id -nG "${USER}" | tr ' ' '\n' | grep -qx docker; then
  sudo usermod -aG docker "${USER}"
fi

uv python install "${PYTHON_VERSION}"
uv sync --locked
npm ci --prefix apps/web

start_dockerd() {
  if docker info >/dev/null 2>&1; then
    return 0
  fi
  if [ -S /var/run/docker.sock ]; then
    sudo chmod 666 /var/run/docker.sock || true
  fi
  if docker info >/dev/null 2>&1; then
    return 0
  fi
  if ! pgrep -x dockerd >/dev/null 2>&1; then
    sudo rm -f /var/run/docker.sock
    sudo mkdir -p /var/log
    /usr/bin/tmux has-session -t dockerd 2>/dev/null && /usr/bin/tmux kill-session -t dockerd || true
    /usr/bin/tmux new-session -d -s dockerd -- sudo dockerd --host=unix:///var/run/docker.sock
  fi
  local attempt
  for attempt in $(seq 1 60); do
    if [ -S /var/run/docker.sock ]; then
      sudo chmod 666 /var/run/docker.sock || true
    fi
    if docker info >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "dockerd did not become ready" >&2
  return 1
}

start_dockerd
docker compose pull postgres redis rabbitmq
docker compose build api

echo "cloud-agent-install: node $(/usr/local/bin/node -v), $(/usr/local/bin/uv --version), docker image houston-api:dev ready"
