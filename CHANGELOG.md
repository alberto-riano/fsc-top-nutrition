# Changelog

Todas las novedades relevantes de TopTrack (FSC Top Nutrition). Sigue
[Semantic Versioning](https://semver.org/lang/es/).

## [1.0.0] - 2026-07-29

Primera versión. App single-tenant de seguimiento de entrenamiento personal.

### Añadido
- **Cuentas** (`accounts`): usuario custom con login por email (case-insensitive),
  roles entrenador/cliente, backend de autenticación por email, perfil editable,
  cambio de contraseña, recuperación de contraseña e invitación por enlace para
  que el cliente establezca su contraseña.
- **Clientes** (`clients`): perfil 1:1 con el usuario, tipos de perfil
  (completo/básico/futbolista) que condicionan las secciones visibles, objetivo,
  notas internas privadas, datos de futbolista (nacimiento, posición, tutor) y
  buscador con filtros.
- **Bonos y sesiones** (`bonos`): bonos con sesiones totales/precio/caducidad,
  sesiones que descuentan automáticamente (contador derivado del número de
  sesiones), estados derivados (activo/agotado/caducado/archivado), «Marcar sesión
  de hoy» en 2 clics, y borrado que restaura el contador.
- **Métricas** (`metrics`): composición corporal, PRs de fuerza y tests de
  resistencia con catálogos de ejercicios y tests ampliables desde el admin;
  gráficas de evolución y récords destacados.
- **Planes** (`plans`): rutinas y planes de alimentación en texto y/o PDF, con
  archivado del anterior y descarga protegida por permisos.
- **Panel** (`dashboard`): panel del entrenador (métricas, avisos de bonos por
  agotar/caducar, clientes) y portal del cliente (bono activo con anillo de
  progreso, evolución y accesos a progreso/bonos/planes).
- **Diseño**: tema oscuro verde/negro con Tailwind (paleta `brand` centralizada),
  Alpine.js self-hosted, gráficas propias sobre `<canvas>` (sin CDN) y PWA
  instalable (manifest + icono).
- **Operación**: `setup.sh` (provisión completa de EC2, idempotente), `deploy.sh`
  (pull + backup + migrate + restart + health check), `seed_demo` (3 clientes de
  ejemplo con historial) y tests de los flujos críticos.
