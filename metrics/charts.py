"""
Construcción de series para las gráficas de evolución (Chart.js).

Devuelve estructuras JSON-serializables (listas de fechas y valores) para que
las plantillas las incrusten y Chart.js las pinte. La lógica vive aquí para no
duplicarla entre la ficha del entrenador y el panel del cliente.
"""
from .models import BodyMeasurement, StrengthPR, EnduranceTest


def _fmt(d):
    return d.strftime('%d/%m/%y')


def _trend(values):
    """Delta entre el primer y el último valor no nulo de una serie (o None si no hay al menos 2)."""
    clean = [v for v in values if v is not None]
    if len(clean) < 2:
        return None
    first, last = clean[0], clean[-1]
    delta = last - first
    pct = round(delta / first * 100, 1) if first else None
    return {'first': first, 'last': last, 'delta': round(delta, 1), 'pct': pct}


def body_series(client):
    """Series de peso y % grasa a lo largo del tiempo (orden cronológico)."""
    rows = list(client.body_measurements.order_by('date'))
    labels = [_fmt(r.date) for r in rows]
    weight = [float(r.weight_kg) for r in rows]
    return {
        'labels': labels,
        'weight': weight,
        'body_fat': [float(r.body_fat_pct) if r.body_fat_pct is not None else None for r in rows],
        'muscle': [float(r.muscle_mass_pct) if r.muscle_mass_pct is not None else None for r in rows],
        'count': len(rows),
        'weight_trend': _trend(weight),
    }


def strength_series(client):
    """Una serie por ejercicio con su progresión de peso."""
    rows = list(client.strength_prs.select_related('exercise').order_by('date'))
    by_ex = {}
    for r in rows:
        by_ex.setdefault(r.exercise.name, {'labels': [], 'values': [], 'best': 0.0})
        by_ex[r.exercise.name]['labels'].append(_fmt(r.date))
        val = float(r.weight_kg)
        by_ex[r.exercise.name]['values'].append(val)
        by_ex[r.exercise.name]['best'] = max(by_ex[r.exercise.name]['best'], val)
    result = []
    for name, data in by_ex.items():
        trend = _trend(data['values'])
        result.append({
            'name': name, **data,
            'trend': trend,
            'improved': bool(trend and trend['delta'] > 0),
        })
    return result


def endurance_series(client):
    """Una serie por tipo de test con su progresión de valor."""
    rows = list(client.endurance_tests.select_related('test_type').order_by('date'))
    by_test = {}
    for r in rows:
        key = r.test_type.name
        if key not in by_test:
            by_test[key] = {
                'labels': [], 'values': [],
                'unit': r.test_type.unit_short,
                'lower_is_better': r.test_type.lower_is_better,
            }
        by_test[key]['labels'].append(_fmt(r.date))
        by_test[key]['values'].append(float(r.value))
    result = []
    for name, data in by_test.items():
        vals = data['values']
        best = (min(vals) if data['lower_is_better'] else max(vals)) if vals else None
        trend = _trend(vals)
        improved = bool(trend and (
            (trend['delta'] < 0) if data['lower_is_better'] else (trend['delta'] > 0)
        ))
        result.append({'name': name, 'best': best, 'trend': trend, 'improved': improved, **data})
    return result
