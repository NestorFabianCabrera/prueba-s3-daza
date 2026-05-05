# Evaluación 1 — PulseBoard

**Alumno:** Carlos Daza  
**Fecha de entrega:** Lunes 04 de mayo  
**Duración máxima:** 5 horas

---

## Reglas

- **Prohibido el uso de IA** (ChatGPT, Copilot, Claude, Gemini o cualquier LLM).
- Recursos permitidos: `man`, `--help`, documentación oficial de Docker, documentación oficial de OpenSSH, tus apuntes.
- **No modifiques** ningún archivo dentro de `servicios/`. Todo tu trabajo va en `infra/`.
- Guarda todas las evidencias en `evidencias/` con los nombres exactos indicados.
- Al terminar: `git push`. Avisa cuando hayas hecho el push.

---

## Qué es PulseBoard

Sistema de monitorización de métricas en tiempo real. Recibe métricas de servicios externos, las almacena, detecta anomalías y las muestra en un dashboard web.

```
Browser → http://localhost
              │
           proxy (nginx)
           ├── /           → dashboard  (nginx:alpine, SPA estática)
           ├── /ingest/    → ingest-api (Flask, 4 réplicas)
           └── /query/     → query-api  (Flask, 2 réplicas)

ingest-api ──► Redis (cola metrics_queue)
                   │
              aggregator  ──► PostgreSQL (tabla metrics)
              alerter     ──► PostgreSQL (tabla alerts) + Redis pub/sub

jumphost (Ubuntu + sshd hardened) — administración del entorno

── Parte SSH separada ──────────────────────────────────────
ssh-server-01  :2223  (Ubuntu + sshd)  usuario: deployer
ssh-server-02  :2224  (Ubuntu + sshd)  usuario: operator
```

### Flujo de una métrica

1. Cliente `POST /ingest/metric` → `{service, metric_name, value}`
2. `ingest-api` valida y pone en Redis `metrics_queue`
3. `aggregator` consume la cola (BLPOP) y persiste en PostgreSQL
4. `alerter` analiza últimos registros; si `value > threshold` → inserta en `alerts` y publica en canal Redis `alerts`
5. `query-api` sirve datos al dashboard desde PostgreSQL

### Variables de entorno que consumen los servicios

| Variable | Servicios | Descripción |
|---|---|---|
| `REDIS_HOST` | ingest-api, query-api, aggregator, alerter | hostname Redis |
| `REDIS_PORT` | todos | puerto (default 6379) |
| `REDIS_PASSWORD` | todos | contraseña Redis |
| `POSTGRES_DSN` | query-api, aggregator, alerter | DSN completo |
| `POSTGRES_USER` / `POSTGRES_HOST` / `POSTGRES_DB` | query-api, aggregator, alerter | partes del DSN |
| `THRESHOLD_CPU` | alerter | umbral cpu_usage (default 80) |
| `THRESHOLD_MEMORY` | alerter | umbral memory_usage (default 85) |
| `THRESHOLD_ERROR_RATE` | alerter | umbral error_rate (default 5) |
| `THRESHOLD_RESPONSE_TIME` | alerter | umbral response_time_ms (default 2000) |

---

## Lo que debes construir

Todo tu trabajo va en `infra/`. La estructura interna es decisión tuya.

### Parte A — Dockerfiles

Crea un `Dockerfile` (y `.dockerignore`) para cada servicio:

| Servicio | Código fuente | Puerto | Arranque |
|---|---|---|---|
| `ingest-api` | `servicios/ingest-api/` | 5000 | gunicorn `wsgi:app` |
| `query-api` | `servicios/query-api/` | 5001 | gunicorn `wsgi:app` |
| `aggregator` | `servicios/aggregator/` | — | `python aggregator.py` |
| `alerter` | `servicios/alerter/` | — | `python alerter.py` |
| `dashboard` | `servicios/dashboard/` | 80 | nginx sirviendo estáticos |
| `jumphost` | — | 2222 | `sshd -D` |
| `ssh-server-01` | — | 2223 | `sshd -D` |
| `ssh-server-02` | — | 2224 | `sshd -D` |

Imagen base sugerida para los servicios Python: `python:3.12-slim`.  
Imagen base para SSH servers y jumphost: `ubuntu:24.04`.

### Parte B — SSH servers (standalone, fuera del Swarm)

Dos contenedores Ubuntu con sshd que se levantan con `docker run`, no como servicios Swarm.

**ssh-server-01** (puerto 2223):
- Usuario `deployer` con acceso por clave ED25519
- Usuario `monitor` con shell `/sbin/nologin`
- sshd hardened (ver criterios)

**ssh-server-02** (puerto 2224):
- Usuario `operator` con acceso por clave ED25519 (clave diferente a la de `deployer`)
- sshd hardened

### Parte C — Docker Swarm (single-node)

Un único nodo manager. Todos los servicios del stack se despliegan en él.

**Stack:** proxy, dashboard, ingest-api (4 réplicas), query-api (2 réplicas), aggregator (global), alerter (global), redis, postgres, jumphost.

**Secretos Swarm:** las contraseñas de PostgreSQL y Redis deben ser secretos Swarm externos, no variables de entorno en texto plano.

**Redes overlay:**
- `frontend-net`: proxy, dashboard, ingest-api, query-api
- `backend-net`: ingest-api, query-api, aggregator, alerter, redis, postgres

**Placement constraint:** postgres solo en el nodo etiquetado con `role=db`.

---

## Criterios de aceptación

### Docker (30 pts)

- [ ] Las imágenes de `ingest-api`, `query-api`, `aggregator` y `alerter` son **multistage** con mínimo 2 etapas nombradas.
- [ ] Ningún contenedor de los servicios Python corre como `root`. Comprobable con `docker exec <container> whoami`.
- [ ] `ingest-api` y `query-api` tienen `HEALTHCHECK` en el Dockerfile y alcanzan estado `healthy`.
- [ ] Las 4 imágenes Python tienen labels OCI: `org.opencontainers.image.title`, `org.opencontainers.image.version`, `org.opencontainers.image.created`.
- [ ] `CMD` / `ENTRYPOINT` en **exec form** en todos los servicios Python (no shell form).
- [ ] Trivy o docker scout sobre `pulseboard/ingest-api:1.0` no reporta vulnerabilidades `CRITICAL`.
- [ ] El `.dockerignore` de cada servicio Python excluye: `__pycache__`, `*.pyc`, `.git`, `.env`.

### SSH (35 pts)

**Sobre ssh-server-01 y ssh-server-02 (y el jumphost del stack):**

- [ ] Puerto SSH distinto de 22 en cada servidor (2223, 2224 y 2222 respectivamente).
- [ ] `PasswordAuthentication no` en todos. Un intento de login con contraseña devuelve `Permission denied (publickey)`.
- [ ] `PermitRootLogin no` en todos. `ssh root@<servidor>` es rechazado.
- [ ] `AllowUsers` configurado en cada servidor solo con el usuario correspondiente.
- [ ] `MaxAuthTries` ≤ 3 en todos.
- [ ] `ClientAliveInterval` y `ClientAliveCountMax` configurados.
- [ ] Banner legal visible antes del prompt de login en todos.
- [ ] El archivo `~/.ssh/config` del host tiene alias para los tres servidores: `pulseboard-jump` (puerto 2222), `pulseboard-ssh01` (puerto 2223), `pulseboard-ssh02` (puerto 2224). Cada alias usa su `IdentityFile` correspondiente.
- [ ] El usuario `monitor` en `ssh-server-01` tiene shell `/sbin/nologin` — puede tener clave pública pero no obtiene shell interactiva.
- [ ] Demostrar recarga de config sshd **sin cerrar la sesión activa**: modificar una directiva (p. ej. `MaxAuthTries`), recargar el daemon (`kill -HUP <pid_sshd>`) y verificar el efecto. En Ubuntu con systemd: `systemctl reload ssh`.
- [ ] Transferir un archivo desde el host a `ssh-server-01` usando **SCP** y verificar la integridad.

### Docker Swarm (35 pts)

- [ ] `docker service ls` muestra todos los servicios en estado `Running` con las réplicas correctas.
- [ ] `ingest-api` tiene exactamente **4 réplicas**.
- [ ] `query-api` tiene exactamente **2 réplicas**.
- [ ] `aggregator` y `alerter` están en **modo global**.
- [ ] `postgres` tiene placement constraint `node.labels.role == db` — verificable en el stack file y en `docker service ps`.
- [ ] Las contraseñas son **secretos Swarm externos**. No aparecen en `docker service inspect` ni en `docker exec <container> env`.
- [ ] Existe una red overlay `frontend-net` y una `backend-net`. El proxy **no puede resolver** `postgres` por nombre.
- [ ] **Rolling update** de `ingest-api` de `v1` a `v2` ejecutado con `--update-parallelism 1`. El `docker service ps` muestra réplicas de v1 (Shutdown) y v2 (Running).
- [ ] **Rollback** de `v2` a `v1` ejecutado con un único comando. El servicio queda operativo.
- [ ] Flujo end-to-end funcional: `POST /ingest/metric` con valor sobre umbral → alerta visible en `/query/alerts` → dashboard muestra alerta.

---

## Evidencias requeridas

| # | Qué debe mostrar | Archivo |
|---|---|---|
| 01 | `docker service ls` — todos Running con réplicas correctas | `01-services.png` |
| 02 | `docker service ps pulseboard_ingest-api` — 4 réplicas Running | `02-ingest-replicas.png` |
| 03 | `docker service ps pulseboard_aggregator` — modo global | `03-global-mode.png` |
| 04 | `docker service ps pulseboard_postgres` — placement constraint aplicado | `04-placement-db.png` |
| 05 | `docker exec` en ingest-api, query-api y aggregator → ninguno es `root` | `05-no-root.png` |
| 06 | `docker inspect` de imagen `ingest-api` mostrando labels OCI | `06-labels-oci.png` |
| 07 | Trivy o docker scout sobre `pulseboard/ingest-api:1.0` — sin CRITICAL | `07-scanner.png` |
| 08 | Conexión SSH exitosa al jumphost con alias `pulseboard-jump` — banner visible | `08-jumphost-ok.png` |
| 09 | Conexión SSH exitosa a ssh-server-01 con alias `pulseboard-ssh01` — banner visible | `09-server01-ok.png` |
| 10 | Conexión SSH exitosa a ssh-server-02 con alias `pulseboard-ssh02` — banner visible | `10-server02-ok.png` |
| 11 | Intento de login con contraseña en cualquier servidor → `Permission denied (publickey)` | `11-password-fail.png` |
| 12 | Contenido de `~/.ssh/config` con los 3 aliases | `12-ssh-config.png` |
| 13 | Recarga de sshd sin cerrar sesión — antes y después de cambiar una directiva | `13-sshd-reload.png` |
| 14 | SCP de un archivo al server-01 y verificación de integridad (`md5sum` o `sha256sum`) | `14-scp-transfer.png` |
| 15 | Secretos no en variables de entorno — `docker exec <ingest-api> env \| grep -i password` vacío | `15-secrets-no-env.png` |
| 16 | Rolling update en progreso — `docker service ps` con réplicas v1 Shutdown y v2 Running | `16-rolling-update.png` |
| 17 | Rollback completado — todas las réplicas vuelven a v1 Running | `17-rollback.png` |
| 18 | `POST /ingest/metric` con valor sobre umbral → respuesta 201 | `18-ingest-metric.png` |
| 19 | `GET /query/alerts` → alerta generada visible en JSON | `19-alert-triggered.png` |
| 20 | Dashboard en el navegador mostrando métricas y alertas | `20-dashboard.png` |

---

## Entrega

```bash
git add .
git commit -m "entrega evaluacion 1 pulseboard - Carlos Daza"
git push
```

Avisa a tu tutor cuando hayas hecho el push.
