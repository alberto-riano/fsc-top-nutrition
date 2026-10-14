"""Utilidades compartidas para las vistas de bonos/sesiones."""


def sessions_calendar_data(sessions):
    """
    Serializa una lista de `Session` a dicts JSON-serializables para pintar el
    calendario de asistencia (ver components/session_calendar.html).
    """
    return [
        {
            'date': s.date.date().isoformat(),
            'time': s.date.strftime('%H:%M'),
            'type': s.get_session_type_display(),
            'notes': s.notes,
        }
        for s in sessions
    ]
