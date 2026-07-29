from django.db import migrations


EXERCISES = [
    'Peso muerto', 'Sentadilla', 'Press banca', 'Press hombro', 'Remo',
    'Dominadas lastradas', 'Hip thrust',
]

# (nombre, unidad, menos_es_mejor)
TESTS = [
    ('Plancha', 'segundos', False),
    ('Sentadilla isométrica', 'segundos', False),
    ('Flexiones máximas', 'repeticiones', False),
    ('Dominadas máximas', 'repeticiones', False),
    # Tests orientados a fútbol
    ('Sprint 30m', 'segundos', True),
    ('Salto vertical', 'metros', False),
    ('Course Navette', 'repeticiones', False),
]


def seed(apps, schema_editor):
    Exercise = apps.get_model('metrics', 'Exercise')
    EnduranceTestType = apps.get_model('metrics', 'EnduranceTestType')
    for i, name in enumerate(EXERCISES):
        Exercise.objects.get_or_create(name=name, defaults={'order': i})
    for i, (name, unit, lower) in enumerate(TESTS):
        EnduranceTestType.objects.get_or_create(
            name=name, defaults={'unit': unit, 'lower_is_better': lower, 'order': i})


def unseed(apps, schema_editor):
    # No borramos: el entrenador puede haber añadido registros que los referencian.
    pass


class Migration(migrations.Migration):
    dependencies = [('metrics', '0001_initial')]
    operations = [migrations.RunPython(seed, unseed)]
