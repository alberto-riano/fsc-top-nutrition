#!/usr/bin/env bash
#
# deploy.sh — Actualiza TopTrack en la EC2: git pull, backup, migrate, estáticos, restart.
#
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
DEPLOY_STATE_DIR="$PROJECT_DIR/.deploy"
BACKUP_DIR="$DEPLOY_STATE_DIR/backups"

cd "$PROJECT_DIR"
source venv/bin/activate
mkdir -p "$BACKUP_DIR"

if [ -n "$(git status --porcelain)" ]; then
    echo "ERROR: el árbol de trabajo del servidor tiene cambios sin guardar."
    exit 1
fi

PREVIOUS_SHA="$(git rev-parse HEAD)"
echo "$PREVIOUS_SHA" > "$DEPLOY_STATE_DIR/previous_sha"

git pull --ff-only
DEPLOY_SHA="$(git rev-parse HEAD)"
echo "$DEPLOY_SHA" > "$DEPLOY_STATE_DIR/current_sha"

if [ -f .env ]; then set -a; source .env; set +a; fi

# Backup de la BD antes de migrar.
if [ -n "${DATABASE_URL:-}" ]; then
    if ! command -v pg_dump >/dev/null 2>&1; then
        echo "ERROR: pg_dump no está disponible; se cancela antes de migrar."
        exit 1
    fi
    BACKUP_FILE="$BACKUP_DIR/pre-${DEPLOY_SHA:0:12}-$(date +%Y%m%d-%H%M%S).dump"
    echo "==> Creando backup previo: $BACKUP_FILE"
    PGPASSWORD="${DB_PASSWORD:-}" pg_dump \
        --format=custom --file="$BACKUP_FILE" \
        --host="${DB_HOST:-localhost}" --port="${DB_PORT:-5432}" \
        --username="${DB_USER:-toptrack}" "${DB_NAME:-toptrack}"
    test -s "$BACKUP_FILE"
    echo "$BACKUP_FILE" > "$DEPLOY_STATE_DIR/latest_backup"
fi

# Compilar CSS si hay Node; si no, se usa el static/css/app.css versionado.
if command -v npm >/dev/null 2>&1; then
    echo "==> Compilando CSS (Tailwind)"
    npm install --no-audit --no-fund
    npm run build:css
else
    echo "==> npm no disponible: se usa static/css/app.css ya compilado."
fi

pip install -r requirements.txt
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py collectstatic --no-input
sudo systemctl restart toptrack-app

HTTP_STATUS="000"
for attempt in {1..30}; do
    HTTP_STATUS="$(curl -sS -o /dev/null -w '%{http_code}' -H 'X-Forwarded-Proto: https' \
        http://127.0.0.1:8000/healthz/ 2>/dev/null || true)"
    [ "$HTTP_STATUS" = "200" ] && break
    sleep 1
done

if [ "$HTTP_STATUS" != "200" ]; then
    echo "ERROR: health check fallido (HTTP ${HTTP_STATUS:-sin respuesta})."
    echo "Commit anterior: $PREVIOUS_SHA"
    echo "Backup más reciente: ${BACKUP_FILE:-no creado}"
    sudo systemctl status toptrack-app --no-pager --lines=20 || true
    exit 1
fi

sudo systemctl status toptrack-app --no-pager --lines=5
echo "==> Despliegue correcto: ${DEPLOY_SHA:0:12}"
