#!/usr/bin/env bash
#
# rename-to-tracoach.sh — Pasa una instalación antigua a los nombres de TraCoach.
#
#   Antes                          Después
#   ~/topnutrition                 ~/tracoach
#   servicio toptrack-app          servicio tracoach
#   nginx sites-*/toptrack-app     nginx sites-*/tracoach
#   BD y usuario Postgres toptrack BD y usuario Postgres tracoach
#
# Se ejecuta UNA vez en la EC2, desde la carpeta antigua:
#
#   cd ~/topnutrition && git pull && bash scripts/rename-to-tracoach.sh
#
# Hace backup de la BD antes de tocar nada. La web está parada 1-2 minutos
# (lo que tarda en reinstalar el venv). Si se corta a medias, se puede volver
# a lanzar desde donde esté la carpeta: cada paso comprueba si ya está hecho.
#
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[0;33m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'
info() { echo -e "${GREEN}==>${NC} $*"; }
warn() { echo -e "${YELLOW}!! ${NC} $*"; }
die()  { echo -e "${RED}xx ${NC} $*" >&2; exit 1; }

OLD_SERVICE="toptrack-app"
NEW_SERVICE="tracoach"
OLD_DB="toptrack"
NEW_DB="tracoach"

# Todo dentro de main(): bash lee el script entero antes de ejecutar, así que
# mover la carpeta donde vive este fichero no le afecta.
main() {
    [ "$(whoami)" != "root" ] || die "Ejecútalo con el usuario ubuntu, no como root (pedirá sudo)."

    local current_dir target_dir env_file
    current_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    target_dir="$(dirname "$current_dir")/tracoach"
    env_file="$current_dir/.env"
    [ -f "$env_file" ] || die "No encuentro $env_file."

    if [ "$current_dir" != "$target_dir" ] && [ -e "$target_dir" ]; then
        die "Ya existe $target_dir. Revísalo antes de continuar."
    fi

    env_value() { grep -E "^$1=" "$env_file" | tail -1 | cut -d= -f2- | sed -E "s/^['\"]//; s/['\"]$//"; }
    local db_name db_user db_password
    db_name="$(env_value DB_NAME)"; db_name="${db_name:-$OLD_DB}"
    db_user="$(env_value DB_USER)"; db_user="${db_user:-$OLD_DB}"
    db_password="$(env_value DB_PASSWORD)"

    echo -e "\n${BOLD}TraCoach: renombrado de la instalación${NC}"
    echo "  Carpeta:  $current_dir -> $target_dir"
    echo "  Servicio: $OLD_SERVICE -> $NEW_SERVICE"
    echo "  BD:       $db_name (usuario $db_user) -> $NEW_DB"
    echo
    read -rp "¿Continuar? La web estará parada 1-2 minutos [s/N]: " ok
    [[ "${ok,,}" == "s" ]] || die "Cancelado."

    # 1. Backup ---------------------------------------------------------------
    mkdir -p "$current_dir/.deploy/backups"
    local backup="$current_dir/.deploy/backups/pre-rename-$(date +%Y%m%d-%H%M%S).dump"
    info "Backup de la base de datos: $backup"
    PGPASSWORD="$db_password" pg_dump --format=custom --file="$backup" \
        --host=localhost --username="$db_user" "$db_name"
    test -s "$backup" || die "El backup ha salido vacío; no sigo."

    # 2. Parar la app ---------------------------------------------------------
    if systemctl list-unit-files "${OLD_SERVICE}.service" --no-legend | grep -q .; then
        info "Parando $OLD_SERVICE"
        sudo systemctl stop "$OLD_SERVICE" || true
    fi

    # 3. Base de datos --------------------------------------------------------
    if [ "$db_name" = "$OLD_DB" ]; then
        info "Renombrando la base de datos y su usuario a $NEW_DB"
        sudo -u postgres psql -v ON_ERROR_STOP=1 -v pw="$db_password" >/dev/null <<SQL
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
  WHERE datname = '$OLD_DB' AND pid <> pg_backend_pid();
ALTER DATABASE $OLD_DB RENAME TO $NEW_DB;
ALTER ROLE $OLD_DB RENAME TO $NEW_DB;
-- Al renombrar un usuario Postgres puede borrar su contraseña: se repone.
ALTER ROLE $NEW_DB WITH PASSWORD :'pw';
SQL
    else
        warn "La BD ya se llama $db_name: no la toco."
    fi

    # 4. .env -----------------------------------------------------------------
    info "Actualizando .env"
    cp "$env_file" "$env_file.pre-rename"
    sed -E -i \
        -e "s#^DB_NAME=['\"]?$OLD_DB['\"]?\$#DB_NAME=$NEW_DB#" \
        -e "s#^DB_USER=['\"]?$OLD_DB['\"]?\$#DB_USER=$NEW_DB#" \
        -e "/^DATABASE_URL=/{s#//$OLD_DB([:@])#//$NEW_DB\\1#; s#/$OLD_DB(['\"]?)\$#/$NEW_DB\\1#;}" \
        -e "s#$current_dir#$target_dir#g" \
        "$env_file"
    chmod 600 "$env_file"

    # 5. Carpeta --------------------------------------------------------------
    if [ "$current_dir" != "$target_dir" ]; then
        info "Moviendo $current_dir a $target_dir"
        mv "$current_dir" "$target_dir"
    fi
    cd "$target_dir"

    # 6. venv (lleva la ruta antigua grabada en sus scripts) --------------------
    info "Reinstalando el entorno de Python (1-2 minutos)"
    python3 -m venv --clear venv
    venv/bin/pip install --quiet --upgrade pip
    venv/bin/pip install --quiet -r requirements.txt

    set -a; source .env; set +a
    venv/bin/python manage.py migrate --noinput
    venv/bin/python manage.py collectstatic --noinput >/dev/null

    # 7. systemd --------------------------------------------------------------
    info "Creando el servicio $NEW_SERVICE"
    sudo tee "/etc/systemd/system/${NEW_SERVICE}.service" >/dev/null <<EOF
[Unit]
Description=TraCoach (gunicorn)
After=network.target postgresql.service

[Service]
User=$(whoami)
WorkingDirectory=$target_dir
EnvironmentFile=$target_dir/.env
ExecStart=$target_dir/venv/bin/gunicorn --workers 3 --timeout 120 --bind 127.0.0.1:8000 core.wsgi:application
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
    if [ -f "/etc/systemd/system/${OLD_SERVICE}.service" ]; then
        sudo systemctl disable "$OLD_SERVICE" >/dev/null 2>&1 || true
        sudo rm -f "/etc/systemd/system/${OLD_SERVICE}.service"
    fi
    sudo systemctl daemon-reload
    sudo systemctl enable "$NEW_SERVICE" >/dev/null 2>&1
    sudo systemctl restart "$NEW_SERVICE"

    # 8. nginx: se copia el fichero actual (certbot le añadió el HTTPS) ----------
    local avail=/etc/nginx/sites-available enabled=/etc/nginx/sites-enabled
    if [ -f "$avail/$OLD_SERVICE" ]; then
        info "Pasando la configuración de nginx a $NEW_SERVICE"
        sudo sed "s#$current_dir#$target_dir#g" "$avail/$OLD_SERVICE" | sudo tee "$avail/$NEW_SERVICE" >/dev/null
        sudo ln -sf "$avail/$NEW_SERVICE" "$enabled/$NEW_SERVICE"
        sudo rm -f "$enabled/$OLD_SERVICE"
        if sudo nginx -t 2>/dev/null; then
            sudo rm -f "$avail/$OLD_SERVICE"
            sudo systemctl reload nginx
        else
            warn "nginx -t falla con la configuración nueva: vuelvo a la anterior."
            sudo rm -f "$enabled/$NEW_SERVICE"
            sudo ln -sf "$avail/$OLD_SERVICE" "$enabled/$OLD_SERVICE"
            sudo nginx -t && sudo systemctl reload nginx
        fi
    elif [ -f "$avail/$NEW_SERVICE" ]; then
        sudo sed -i "s#$current_dir#$target_dir#g" "$avail/$NEW_SERVICE"
        sudo nginx -t && sudo systemctl reload nginx
    fi

    # 9. cron (por si alguna tarea apuntaba a la carpeta vieja) ------------------
    if crontab -l 2>/dev/null | grep -qE "topnutrition|toptrack"; then
        info "Actualizando rutas en el crontab"
        crontab -l | sed -e "s#$current_dir#$target_dir#g" -e "s#$OLD_SERVICE#$NEW_SERVICE#g" | crontab -
    fi

    # 10. Comprobación ----------------------------------------------------------
    info "Comprobando que la web responde"
    local status="000"
    for _ in {1..30}; do
        status="$(curl -sS -o /dev/null -w '%{http_code}' -H 'X-Forwarded-Proto: https' \
            http://127.0.0.1:8000/healthz/ 2>/dev/null || true)"
        [ "$status" = "200" ] && break
        sleep 1
    done
    if [ "$status" != "200" ]; then
        sudo systemctl status "$NEW_SERVICE" --no-pager --lines=20 || true
        die "La web no responde (HTTP $status). Backup: $target_dir/.deploy/backups/$(basename "$backup")"
    fi

    echo
    info "${BOLD}Hecho.${NC} TraCoach vive en $target_dir y el servicio es $NEW_SERVICE."
    echo "  Tu terminal sigue en la carpeta vieja, que ya no existe. Ejecuta:"
    echo -e "    ${BOLD}cd $target_dir${NC}"
    echo "  A partir de ahora: cd $target_dir && bash deploy.sh"
    echo "  Logs: sudo journalctl -u $NEW_SERVICE -f"
}

main "$@"
