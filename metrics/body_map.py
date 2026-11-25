"""
Puntos del "mapa corporal" (perímetros) y su posición sobre la silueta SVG
compartida por el formulario del entrenador y la vista de progreso del
cliente. Las coordenadas se guardan como porcentajes (0-100) para poder
superponer los marcadores como HTML absoluto sobre el SVG sin recalcular
nada en las plantillas.
"""

# viewBox de referencia de la silueta (templates/components/body_silhouette.html).
_VIEWBOX_W, _VIEWBOX_H = 240, 560


def _pt(field, label, x, y, copy_from=None):
    return {
        'field': field,
        'label': label,
        # Strings (no float/Decimal) para que Django no las localice con coma
        # decimal en la plantilla (left:50,0% rompería el CSS en es-ES).
        'x': f"{x / _VIEWBOX_W * 100:.2f}",
        'y': f"{y / _VIEWBOX_H * 100:.2f}",
        'copy_from': copy_from,
    }


# El cuello se dejó de medir: el campo sigue en el modelo para no perder el
# histórico, pero ya no se pide ni se enseña.
POINTS = [
    _pt('chest_cm', 'Pecho', 120, 150),
    _pt('waist_cm', 'Cintura', 120, 232),
    _pt('hip_cm', 'Cadera', 120, 298),
    _pt('arm_l_cm', 'Brazo izq.', 14, 185),
    _pt('arm_r_cm', 'Brazo der.', 226, 185, copy_from='arm_l_cm'),
    _pt('thigh_l_cm', 'Muslo izq.', 70, 400),
    _pt('thigh_r_cm', 'Muslo der.', 170, 400, copy_from='thigh_l_cm'),
    _pt('calf_l_cm', 'Gemelo izq.', 70, 495),
    _pt('calf_r_cm', 'Gemelo der.', 170, 495, copy_from='calf_l_cm'),
]

FIELD_NAMES = [p['field'] for p in POINTS]
