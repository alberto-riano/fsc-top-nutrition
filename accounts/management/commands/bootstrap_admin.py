"""
Crea el usuario ENTRENADOR (admin) de TopTrack. Es superusuario para poder
entrar también a /admin/. Idempotente.

Lee variables de entorno: ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_USERNAME.
"""
import os
from django.core.management.base import BaseCommand

from accounts.models import User


class Command(BaseCommand):
    help = "Crea el entrenador/admin (superadmin) de TopTrack. Idempotente."

    def add_arguments(self, parser):
        parser.add_argument('--username', default=os.environ.get('ADMIN_USERNAME', ''))
        parser.add_argument('--password', default=os.environ.get('ADMIN_PASSWORD', 'admin'))
        parser.add_argument('--email', default=os.environ.get('ADMIN_EMAIL', 'admin@toptrack.local'))

    def handle(self, *args, **opts):
        email = (opts['email'] or '').strip().lower() or 'admin@toptrack.local'
        # El entrenador entra por EMAIL; el username = email para no confundir.
        username = (opts['username'] or '').strip() or email

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': username,
                'role': 'admin',
                'first_name': 'Entrenador',
                'is_staff': True,
                'is_superuser': True,
            },
        )

        if created:
            user.set_password(opts['password'])
            user.save()
            self.stdout.write(self.style.SUCCESS(
                f"Entrenador creado. Inicia sesión con: {email}"
            ))
        else:
            changed = []
            if user.role != 'admin':
                user.role = 'admin'
                changed.append('role')
            if not user.is_staff:
                user.is_staff = True
                changed.append('is_staff')
            if not user.is_superuser:
                user.is_superuser = True
                changed.append('is_superuser')
            if changed:
                user.save(update_fields=changed)
            self.stdout.write(
                f"El entrenador ya existía ({email}); no se cambió la contraseña."
            )
