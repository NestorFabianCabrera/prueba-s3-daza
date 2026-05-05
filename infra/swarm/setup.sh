#!/usr/bin/env bash
# PulseBoard — setup completo: SSH servers, imágenes, Swarm single-node, stack
set -euo pipefail

STACK="pulseboard"
BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
REDIS_PASS="PulseRedis2024!"
PG_PASS="PulsePostgres2024!"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

log()  { echo ""; echo "▶ $*"; }
ok()   { echo "  ✓ $*"; }

cd "$ROOT_DIR"

# ── 1. SSH keys ───────────────────────────────────────────────────────────────
log "Generando claves SSH..."
mkdir -p infra/ssh-keys
[ ! -f infra/ssh-keys/deployer_ed25519 ] && \
  ssh-keygen -t ed25519 -f infra/ssh-keys/deployer_ed25519 -N "" -C "deployer@pulseboard" -q
[ ! -f infra/ssh-keys/operator_ed25519 ] && \
  ssh-keygen -t ed25519 -f infra/ssh-keys/operator_ed25519 -N "" -C "operator@pulseboard" -q
ok "claves listas"
DEPLOYER_PUBKEY=$(cat infra/ssh-keys/deployer_ed25519.pub)
OPERATOR_PUBKEY=$(cat infra/ssh-keys/operator_ed25519.pub)

# ── 2. Build imágenes ─────────────────────────────────────────────────────────
log "Construyendo imágenes..."

build() {
  local name=$1 version=${2:-1.0}
  echo "  → pulseboard/${name}:${version}"
  docker build --build-arg BUILD_DATE="$BUILD_DATE" --build-arg VERSION="$version" \
    -t "pulseboard/${name}:${version}" -f "infra/dockerfiles/${name}/Dockerfile" . -q
}

build ingest-api 1.0
build ingest-api 2.0
build query-api  1.0
build aggregator 1.0
build alerter    1.0
build dashboard  1.0
build proxy      1.0

docker build --build-arg DEPLOYER_PUBKEY="$DEPLOYER_PUBKEY" \
  --build-arg BUILD_DATE="$BUILD_DATE" \
  -t pulseboard/jumphost:1.0 -f infra/dockerfiles/jumphost/Dockerfile . -q

docker build --build-arg DEPLOYER_PUBKEY="$DEPLOYER_PUBKEY" \
  --build-arg BUILD_DATE="$BUILD_DATE" \
  -t pulseboard/ssh-server-01:1.0 -f infra/ssh-servers/Dockerfile.server01 . -q

docker build --build-arg OPERATOR_PUBKEY="$OPERATOR_PUBKEY" \
  --build-arg BUILD_DATE="$BUILD_DATE" \
  -t pulseboard/ssh-server-02:1.0 -f infra/ssh-servers/Dockerfile.server02 . -q

ok "todas las imágenes construidas"

# ── 3. SSH servers (contenedores standalone, fuera del Swarm) ─────────────────
log "Levantando servidores SSH..."

docker rm -f ssh-server-01 ssh-server-02 2>/dev/null || true
docker run -d --name ssh-server-01 -p 2223:2223 pulseboard/ssh-server-01:1.0 > /dev/null
docker run -d --name ssh-server-02 -p 2224:2224 pulseboard/ssh-server-02:1.0 > /dev/null
ok "ssh-server-01 en :2223, ssh-server-02 en :2224"

# ── 4. Swarm single-node ──────────────────────────────────────────────────────
log "Configurando Swarm single-node..."

SWARM_STATE=$(docker info --format '{{.Swarm.LocalNodeState}}')
if [ "$SWARM_STATE" != "active" ]; then
  docker swarm init > /dev/null
  ok "Swarm inicializado"
else
  ok "Swarm ya activo"
fi

NODE_ID=$(docker node ls --format '{{.ID}}' | head -1)
docker node update --label-add role=db "$NODE_ID" > /dev/null
ok "Nodo etiquetado con role=db"

# ── 5. Secretos ───────────────────────────────────────────────────────────────
log "Creando secretos Swarm..."

for secret in redis_password pg_password; do
  docker secret rm "$secret" 2>/dev/null || true
done
echo "$REDIS_PASS" | docker secret create redis_password - > /dev/null
echo "$PG_PASS"    | docker secret create pg_password    - > /dev/null
ok "redis_password y pg_password creados"

# ── 6. Deploy stack ───────────────────────────────────────────────────────────
log "Desplegando stack..."
docker stack deploy -c infra/swarm/stack.yml "$STACK" 2>/dev/null

log "Esperando servicios (90s máx)..."
for i in $(seq 1 18); do
  RUNNING=$(docker stack ps "$STACK" --format '{{.CurrentState}}' 2>/dev/null | grep -c "^Running" || true)
  TOTAL=$(docker stack ps "$STACK" --format '{{.CurrentState}}' 2>/dev/null | wc -l || true)
  [ "$RUNNING" -ge "$TOTAL" ] && [ "$TOTAL" -gt 0 ] && break
  echo "  ${RUNNING}/${TOTAL} Running... (${i})"
  sleep 5
done

# ── 7. ~/.ssh/config ──────────────────────────────────────────────────────────
log "Configurando ~/.ssh/config..."
SSH_CFG="$HOME/.ssh/config"
mkdir -p "$HOME/.ssh"

add_host() {
  local alias=$1 host=$2 port=$3 user=$4 key=$5
  grep -q "Host $alias" "$SSH_CFG" 2>/dev/null && return
  cat >> "$SSH_CFG" << EOF

Host $alias
    HostName $host
    Port $port
    User $user
    IdentityFile $ROOT_DIR/infra/ssh-keys/$key
    IdentitiesOnly yes
    IdentityAgent none
    StrictHostKeyChecking no
EOF
  ok "alias '$alias' añadido"
}

add_host pulseboard-jump  127.0.0.1 2222 deployer deployer_ed25519
add_host pulseboard-ssh01 127.0.0.1 2223 deployer deployer_ed25519
add_host pulseboard-ssh02 127.0.0.1 2224 operator operator_ed25519

# ── 8. Resumen ────────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════"
log "Nodo Swarm:"
docker node ls

log "Servicios:"
docker service ls

log "SSH servers standalone:"
docker ps --filter name=ssh-server --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "  Dashboard:    http://localhost"
echo "  Jumphost:     ssh pulseboard-jump"
echo "  SSH server01: ssh pulseboard-ssh01"
echo "  SSH server02: ssh pulseboard-ssh02"
echo "════════════════════════════════════════════════════════"
