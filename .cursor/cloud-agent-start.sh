#!/usr/bin/env bash
# Per-boot Cloud Agent start: Docker services, migrated database, catalog, Vite.
set -euo pipefail

cd /workspace

export PATH="/usr/local/bin:${PATH}"

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
  sudo mkdir -p /etc/docker /var/log
  if [ ! -s /etc/docker/daemon.json ]; then
    printf '%s\n' '{"storage-driver":"fuse-overlayfs","iptables":true,"ip6tables":false}' |
      sudo tee /etc/docker/daemon.json >/dev/null
  fi
  if [ -x /usr/sbin/iptables-legacy ]; then
    sudo update-alternatives --set iptables /usr/sbin/iptables-legacy >/dev/null
    sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy >/dev/null
  fi
  if ! pgrep -x dockerd >/dev/null 2>&1; then
    sudo rm -f /var/run/docker.sock
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

ensure_env() {
  if [ -f .env ]; then
    return 0
  fi
  cp .env.example .env
  sed -i \
    -e 's/^HOUSTON_AI_OBSERVATION_PROVIDER=.*/HOUSTON_AI_OBSERVATION_PROVIDER=fake/' \
    -e 's/^HOUSTON_AI_ANALYTICS_PATTERN_PROVIDER=.*/HOUSTON_AI_ANALYTICS_PATTERN_PROVIDER=fake/' \
    -e 's/^HOUSTON_AI_TRANSCRIPTION_PROVIDER=.*/HOUSTON_AI_TRANSCRIPTION_PROVIDER=fake/' \
    .env
  cat >> .env <<'EOF'
CELERY_AI_INTERACTIVE_CONCURRENCY=1
CELERY_OPERATIONAL_CONCURRENCY=1
CELERY_BACKGROUND_CONCURRENCY=1
CELERY_BRAIN_CONCURRENCY=1
EOF
}

wait_for_url() {
  local url="$1"
  local attempts="$2"
  local attempt
  for attempt in $(seq 1 "${attempts}"); do
    if curl -fsS -o /dev/null --max-time 5 "${url}"; then
      echo "ready: ${url}"
      return 0
    fi
    sleep 2
  done
  echo "timed out waiting for ${url}" >&2
  return 1
}

start_vite() {
  if curl -fsS -o /dev/null --max-time 3 http://127.0.0.1:5173/; then
    echo "vite already listening on :5173"
    return 0
  fi
  /usr/bin/tmux has-session -t web 2>/dev/null && /usr/bin/tmux kill-session -t web || true
  /usr/bin/tmux new-session -d -s web -c /workspace/apps/web -- \
    bash -lc 'export PATH="/usr/local/bin:${PATH}"; npm run dev -- --host 0.0.0.0 --port 5173 2>&1 | tee /tmp/vite.log'
}

start_dockerd
ensure_env
make up-backend
wait_for_url http://127.0.0.1:8000/api/v1/health/ 60
make migrate
make import-catalog
make check
make catalog-check
start_vite
wait_for_url http://127.0.0.1:5173/ 60
echo "cloud-agent-start: API :8000 and Vite :5173 are ready"
