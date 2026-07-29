# TopTrack · FSC Top Nutrition

Aplicación web de seguimiento de entrenamiento personal para **FSC Top Nutrition**
(Alcobendas, C/ Libertad 59). El entrenador (admin) gestiona clientes, sesiones,
bonos, métricas de progreso y planes; cada cliente ve **solo sus datos** desde el
móvil.

Es una app **single-tenant** (un centro, un entrenador) construida con Django,
Tailwind CSS y Alpine.js, con tema oscuro verde/negro y PWA para instalar en el móvil.

## Características

- **Login por email** (no username), con normalización a minúsculas.
- **Dos roles**: entrenador (acceso total) y cliente (solo lectura de sus datos).
- **Perfiles de cliente** que condicionan qué secciones se muestran:
  - **Completo**: composición corporal, PRs de fuerza, tests de resistencia, rutina y plan de alimentación.
  - **Básico**: sesiones/bonos, composición corporal y notas.
  - **Futbolista**: sesiones/bonos, tests físicos adaptados (velocidad, salto…), posición, fecha de nacimiento y contacto del tutor.
- **Bonos y sesiones**: registrar una sesión en 2 clics («Marcar sesión de hoy»),
  descuento automático, corrección/borrado que restaura el contador, aviso cuando
  quedan ≤2 sesiones.
- **Métricas** con gráficas de evolución (peso, % grasa/músculo, progresión de PRs
  y tests) y récords destacados.
- **Planes** en texto y/o PDF, con histórico al archivar el anterior.
- **PWA** instalable en el móvil (manifest + icono).

## Arquitectura

Monolito Django modular, una app por dominio. Los modelos no dependen de vistas;
la lógica de negocio vive en servicios/helpers (`clients/services.py`,
`metrics/charts.py`); las vistas son finas.

| App | Responsabilidad |
| --- | --- |
| `accounts` | Usuario custom (email), roles, autenticación e invitaciones |
| `clients` | Perfil del cliente y visibilidad por tipo de perfil |
| `bonos` | Bonos y sesiones (descuento y estados derivados) |
| `metrics` | Composición corporal, PRs y tests + catálogos ampliables |
| `plans` | Rutinas y planes de alimentación (texto/PDF) |
| `dashboard` | Panel del entrenador y portal del cliente |

## Desarrollo local (SQLite)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Sin DATABASE_URL en el entorno usa SQLite automáticamente.
python manage.py migrate
python manage.py bootstrap_admin           # crea admin@toptrack.local / admin
python manage.py seed_demo                  # (opcional) 3 clientes de ejemplo
python manage.py runserver
```

Abre <http://127.0.0.1:8000/> e inicia sesión con `admin@toptrack.local / admin`.
Clientes de demo: `ana@demo.com`, `luis@demo.com`, `marco@demo.com` (contraseña `demo1234`).

### Estilos (Tailwind)

El CSS compilado (`static/css/app.css`) se versiona. Para recompilarlo tras tocar
plantillas:

```bash
npm install
npm run build:css        # o npm run watch:css durante el desarrollo
```

## Despliegue en EC2

En una EC2 Ubuntu 22.04/24.04 vacía (puertos 22/80/443 abiertos):

```bash
git clone <repo> topnutrition
cd topnutrition
bash setup.sh
```

`setup.sh` es idempotente: detecta la IP pública, pregunta email/contraseña del
entrenador y dominio opcional, instala PostgreSQL + venv + gunicorn + nginx
(+ certbot si hay dominio), genera `.env` con claves aleatorias, migra, compila
estáticos, crea el admin, ofrece cargar la demo y arranca el servicio.

Para actualizar tras un `git push`, en la EC2:

```bash
./deploy.sh
```

Hace `git pull --ff-only`, backup `pg_dump`, migraciones, `collectstatic`,
reinicio del servicio y health check.

## Tests

```bash
python manage.py test
```

Cubren los flujos críticos: descuento de sesiones y estados de bono, restauración
del contador al borrar una sesión, permisos (un cliente no ve datos de otro ni
accede a vistas de entrenador) y alta de cliente.
