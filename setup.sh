#!/usr/bin/env bash
#
# setup.sh — Provisión completa de TopTrack (FSC Top Nutrition) en una EC2 Ubuntu vacía.
#
#   1. git clone <repo> topnutrition
#   2. cd topnutrition
#   3. bash setup.sh
#
# Instala Postgres + venv + gunicorn + nginx (+ certbot si hay dominio), crea el
# entrenador/admin y arranca la app. Idempotente: se puede reejecutar sin romper nada.
#
# Requisitos de la EC2:
#   - Ubuntu 22.04 o 24.04 LTS
#   - Security Group con puertos abiertos: 22 (SSH), 80 (HTTP), 443 (HTTPS)
#   - Mínimo recomendado: t3.small (2 GB RAM).
#
set -euo pipefail

BOLD='\033[1m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}==>${NC} $*"; }
warn()  { echo -e "${YELLOW}!! ${NC} $*"; }
err()   { echo -e "${RED}xx ${NC} $*" >&2; }
title() { echo -e "\n${BOLD}$*${NC}"; }

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
ENV_FILE="$PROJECT_DIR/.env"
SERVICE_NAME="toptrack-app"
SERVICE_USER="$(whoami)"

if [ "$SERVICE_USER" = "root" ]; then
    err "No ejecutes este script como root. Usa el usuario 'ubuntu' (pedirá sudo cuando lo necesite)."
    exit 1
fi

# ---------------------------------------------------------------------------
# 0. Detectar IP pública (IMDSv2)
# ---------------------------------------------------------------------------
get_public_ip() {
    local token ip
    token=$(curl -s -m 3 -X PUT "http://169.254.169.254/latest/api/token" \
        -H "X-aws-ec2-metadata-token-ttl-seconds: 60" 2>/dev/null || true)
    if [ -n "$token" ]; then
        ip=$(curl -s -m 3 -H "X-aws-ec2-metadata-token: $token" \
            http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || true)
    fi
    [ -z "${ip:-}" ] && ip=$(curl -s -m 3 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || true)
    [ -z "${ip:-}" ] && ip=$(curl -s -m 3 https://api.ipify.org 2>/dev/null || true)
    echo "${ip:-}"
}
PUBLIC_IP="$(get_public_ip)"

# ---------------------------------------------------------------------------
# 1. Preguntas de configuración
# ---------------------------------------------------------------------------
title "Configuración de TopTrack (FSC Top Nutrition)"
echo "IP pública detectada: ${PUBLIC_IP:-(no detectada)}"
echo "Se creará el ENTRENADOR (admin). Se inicia sesión con el EMAIL (no con usuario)."
echo

read -rp "Email del entrenador (tu acceso) [admin@toptrack.local]: " ADMIN_EMAIL
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@toptrack.local}"
read -rp "Contraseña del entrenador [admin]: " ADMIN_PASSWORD
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
read -rp "Dominio (vacío = usar solo la IP) []: " DOMAIN
DOMAIN="${DOMAIN:-}"

echo
echo "Email saliente (opcional; para 'olvidé mi contraseña' e invitaciones):"
read -rp "  EMAIL_HOST (vacío = sin envío, cae a consola) []: " EMAIL_HOST_INPUT
EMAIL_HOST_INPUT="${EMAIL_HOST_INPUT:-}"
read -rp "  DEFAULT_FROM_EMAIL [TopTrack <no-reply@fsctopnutrition.com>]: " EMAIL_FROM_INPUT
EMAIL_FROM_INPUT="${EMAIL_FROM_INPUT:-TopTrack <no-reply@fsctopnutrition.com>}"
read -rp "  EMAIL_HOST_USER []: " EMAIL_USER_INPUT
EMAIL_USER_INPUT="${EMAIL_USER_INPUT:-}"
read -rp "  EMAIL_HOST_PASSWORD []: " EMAIL_PASS_INPUT
EMAIL_PASS_INPUT="${EMAIL_PASS_INPUT:-}"

echo
read -rp "¿Cargar datos de DEMO (3 clientes de ejemplo con historial)? [s/N]: " LOAD_DEMO
LOAD_DEMO="${LOAD_DEMO:-n}"

if [ -n "$DOMAIN" ]; then
    PRIMARY_HOST="$DOMAIN"; SCHEME="https"; SSL_REDIRECT="True"; HSTS_SECONDS="3600"
else
    # Solo IP (sin certificado): no forzar HTTPS ni HSTS o la web quedaría inaccesible.
    PRIMARY_HOST="${PUBLIC_IP:-localhost}"; SCHEME="http"; SSL_REDIRECT="False"; HSTS_SECONDS="0"
fi

# ---------------------------------------------------------------------------
# 2. Paquetes del sistema
# ---------------------------------------------------------------------------
title "Instalando paquetes del sistema"
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 python3-venv python3-dev build-essential libpq-dev \
    postgresql postgresql-contrib nginx curl git
if [ -n "$DOMAIN" ]; then
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y certbot python3-certbot-nginx
fi
# Node para compilar Tailwind (opcional: deploy.sh cae al CSS versionado si no está).
if ! command -v npm >/dev/null 2>&1; then
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nodejs npm || warn "No se pudo instalar Node; se usará el CSS ya compilado del repo."
fi
git config --global credential.helper store

# ---------------------------------------------------------------------------
# 3. Entorno virtual + dependencias
# ---------------------------------------------------------------------------
title "Creando entorno virtual e instalando dependencias"
[ -d "$VENV_DIR" ] || python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt"

# ---------------------------------------------------------------------------
# 4. Fichero .env
# ---------------------------------------------------------------------------
title "Configurando variables de entorno (.env)"
if [ -f "$ENV_FILE" ]; then
    warn ".env ya existe: se reutiliza. (Bórralo para regenerarlo)"
    DB_PASSWORD="$(grep -E '^DB_PASSWORD=' "$ENV_FILE" | cut -d= -f2- | tr -d "'")"
else
    SECRET_KEY="$("$VENV_DIR/bin/python" -c 'import secrets; print(secrets.token_urlsafe(64))')"
    DB_PASSWORD="$("$VENV_DIR/bin/python" -c 'import secrets; print(secrets.token_hex(24))')"

    ALLOWED_HOSTS="localhost,127.0.0.1"
    [ -n "$PUBLIC_IP" ] && ALLOWED_HOSTS="${ALLOWED_HOSTS},${PUBLIC_IP}"
    if [ -n "$DOMAIN" ]; then
        ALLOWED_HOSTS="${ALLOWED_HOSTS},${DOMAIN}"
        [[ "$DOMAIN" == www.* ]] && ALLOWED_HOSTS="${ALLOWED_HOSTS},${DOMAIN#www.}"
    fi
    CSRF_ORIGINS="${SCHEME}://${PRIMARY_HOST}"
    [ -n "$PUBLIC_IP" ] && CSRF_ORIGINS="${CSRF_ORIGINS},http://${PUBLIC_IP}"
    [[ "$DOMAIN" == www.* ]] && CSRF_ORIGINS="${CSRF_ORIGINS},${SCHEME}://${DOMAIN#www.}"

    cat > "$ENV_FILE" <<EOF
# Generado por setup.sh
DEBUG=False
DJANGO_SECRET_KEY='${SECRET_KEY}'
ALLOWED_HOSTS='${ALLOWED_HOSTS}'
CSRF_TRUSTED_ORIGINS='${CSRF_ORIGINS}'
SITE_NAME=TopTrack
SITE_TAGLINE=FSC Top Nutrition
SUPPORT_EMAIL=info@fsctopnutrition.com

# Seguridad HTTPS: solo se fuerza si hay dominio (con IP no hay certificado).
SECURE_SSL_REDIRECT=${SSL_REDIRECT}
SECURE_HSTS_SECONDS=${HSTS_SECONDS}

# Base de datos PostgreSQL
DATABASE_URL=postgres://toptrack@localhost:5432/toptrack
DB_NAME=toptrack
DB_USER=toptrack
DB_PASSWORD='${DB_PASSWORD}'
DB_HOST=localhost
DB_PORT=5432

# Email saliente (si EMAIL_HOST queda vacío, se usa la consola y no envía nada)
EMAIL_HOST='${EMAIL_HOST_INPUT}'
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER='${EMAIL_USER_INPUT}'
EMAIL_HOST_PASSWORD='${EMAIL_PASS_INPUT}'
DEFAULT_FROM_EMAIL='${EMAIL_FROM_INPUT}'
EOF
    info ".env creado."
fi
chmod 600 "$ENV_FILE"

# ---------------------------------------------------------------------------
# 5. PostgreSQL
# ---------------------------------------------------------------------------
title "Configurando PostgreSQL"
sudo systemctl enable --now postgresql
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='toptrack'" | grep -q 1; then
    sudo -u postgres psql -c "CREATE USER toptrack WITH PASSWORD '${DB_PASSWORD}';"
    info "Usuario de BD 'toptrack' creado."
else
    warn "El usuario de BD 'toptrack' ya existe."
fi
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='toptrack'" | grep -q 1; then
    sudo -u postgres psql -c "CREATE DATABASE toptrack OWNER toptrack;"
    info "Base de datos 'toptrack' creada."
else
    warn "La base de datos 'toptrack' ya existe."
fi

# ---------------------------------------------------------------------------
# 6. Compilar CSS (si hay npm), migrar, estáticos, admin, demo
# ---------------------------------------------------------------------------
title "Preparando la aplicación"
mkdir -p "$PROJECT_DIR/media" "$PROJECT_DIR/staticfiles" "$PROJECT_DIR/logs"
if command -v npm >/dev/null 2>&1; then
    info "Compilando CSS (Tailwind)"
    (cd "$PROJECT_DIR" && npm install --no-audit --no-fund && npm run build:css) || warn "Fallo al compilar CSS; se usa el ya versionado."
fi
set -a; source "$ENV_FILE"; set +a
"$VENV_DIR/bin/python" "$PROJECT_DIR/manage.py" migrate --noinput
"$VENV_DIR/bin/python" "$PROJECT_DIR/manage.py" collectstatic --noinput
env ADMIN_EMAIL="$ADMIN_EMAIL" ADMIN_PASSWORD="$ADMIN_PASSWORD" \
    "$VENV_DIR/bin/python" "$PROJECT_DIR/manage.py" bootstrap_admin
if [[ "${LOAD_DEMO,,}" == "s" ]]; then
    "$VENV_DIR/bin/python" "$PROJECT_DIR/manage.py" seed_demo
fi

# ---------------------------------------------------------------------------
# 7. Servicio systemd (gunicorn)
# ---------------------------------------------------------------------------
title "Configurando el servicio ${SERVICE_NAME} (gunicorn)"
sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" >/dev/null <<EOF
[Unit]
Description=TopTrack (gunicorn)
After=network.target postgresql.service

[Service]
User=${SERVICE_USER}
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${VENV_DIR}/bin/gunicorn --workers 3 --timeout 120 --bind 127.0.0.1:8000 core.wsgi:application
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}"
sudo systemctl restart "${SERVICE_NAME}"

# ---------------------------------------------------------------------------
# 8. Nginx
# ---------------------------------------------------------------------------
title "Configurando nginx"
SERVER_NAME="${DOMAIN:-_}"
[[ "$DOMAIN" == www.* ]] && SERVER_NAME="${SERVER_NAME} ${DOMAIN#www.}"
sudo tee "/etc/nginx/sites-available/${SERVICE_NAME}" >/dev/null <<EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name ${SERVER_NAME};
    client_max_body_size 20M;

    location /media/ { alias ${PROJECT_DIR}/media/; }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120;
        proxy_connect_timeout 10;
    }
}
EOF
sudo ln -sf "/etc/nginx/sites-available/${SERVICE_NAME}" "/etc/nginx/sites-enabled/${SERVICE_NAME}"
sudo rm -f /etc/nginx/sites-enabled/default
sudo chmod o+x "/home/${SERVICE_USER}" 2>/dev/null || true
sudo nginx -t
sudo systemctl restart nginx

# ---------------------------------------------------------------------------
# 9. HTTPS (solo si hay dominio)
# ---------------------------------------------------------------------------
if [ -n "$DOMAIN" ]; then
    BASE_DOMAIN="${DOMAIN#www.}"
    CERT_DOMAIN_ARGS=(-d "$DOMAIN")
    [[ "$DOMAIN" == www.* ]] && CERT_DOMAIN_ARGS+=(-d "$BASE_DOMAIN")
    title "Solicitando certificado HTTPS para ${DOMAIN}"
    warn "Asegúrate de que ${DOMAIN} ya apunta (DNS tipo A) a ${PUBLIC_IP}."
    read -rp "¿Lanzar certbot ahora? [s/N]: " RUN_CERTBOT
    if [[ "${RUN_CERTBOT,,}" == "s" ]]; then
        sudo certbot --nginx "${CERT_DOMAIN_ARGS[@]}" --non-interactive --agree-tos \
            -m "admin@${BASE_DOMAIN}" --redirect \
            || warn "certbot falló; revisa el DNS y reintenta: sudo certbot --nginx ${CERT_DOMAIN_ARGS[*]}"
    else
        warn "Saltado. Cuando el DNS apunte: sudo certbot --nginx ${CERT_DOMAIN_ARGS[*]}"
    fi
fi

# ---------------------------------------------------------------------------
# 10. Resumen
# ---------------------------------------------------------------------------
title "✅ Instalación completada"
echo
if [ -n "$DOMAIN" ]; then
    echo -e "  Web:   ${BOLD}${SCHEME}://${DOMAIN}/${NC}"
else
    echo -e "  Web:   ${BOLD}http://${PUBLIC_IP:-<IP-de-tu-EC2>}/${NC}"
fi
echo -e "  Entra (por EMAIL): ${BOLD}${ADMIN_EMAIL} / ${ADMIN_PASSWORD}${NC}"
echo
echo "  Comandos útiles:"
echo "    sudo systemctl status ${SERVICE_NAME}     # estado"
echo "    sudo journalctl -u ${SERVICE_NAME} -f     # logs en vivo"
echo "    sudo systemctl restart ${SERVICE_NAME}    # reiniciar"
echo "    ${VENV_DIR}/bin/python manage.py seed_demo # cargar demo"
