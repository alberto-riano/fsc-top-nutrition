/*
 * Calendario mensual de asistencia a sesiones, sin dependencias externas.
 * Se usa como factoría de x-data de Alpine: x-data="topTrackCalendar('<id del json_script>')"
 *
 * Datos esperados en el <script type="application/json" id="...">:
 *   [{ date: 'YYYY-MM-DD', time: 'HH:MM', type: 'Individual', notes: '...' }, ...]
 */
(function () {
  const MONTH_NAMES = [
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
  ];
  const WEEKDAYS = ['L', 'M', 'X', 'J', 'V', 'S', 'D'];

  function readData(id) {
    const el = document.getElementById(id);
    if (!el) return [];
    try { return JSON.parse(el.textContent) || []; } catch (e) { return []; }
  }

  function topTrackCalendar(dataId) {
    const sessions = readData(dataId);
    const byDay = {};
    sessions.forEach(s => { (byDay[s.date] = byDay[s.date] || []).push(s); });
    Object.keys(byDay).forEach(k => byDay[k].sort((a, b) => a.time.localeCompare(b.time)));

    const dates = Object.keys(byDay).sort();
    // Arranca en el mes de la sesión más reciente (o el mes actual si no hay ninguna).
    const anchor = dates.length ? new Date(dates[dates.length - 1] + 'T00:00:00') : new Date();

    return {
      byDay: byDay,
      year: anchor.getFullYear(),
      month: anchor.getMonth(),
      selected: null,
      weekdays: WEEKDAYS,

      get monthLabel() {
        return MONTH_NAMES[this.month] + ' ' + this.year;
      },

      get days() {
        const first = new Date(this.year, this.month, 1);
        const daysInMonth = new Date(this.year, this.month + 1, 0).getDate();
        const offset = (first.getDay() + 6) % 7; // semana empieza en lunes
        const cells = [];
        for (let i = 0; i < offset; i++) cells.push(null);
        for (let day = 1; day <= daysInMonth; day++) {
          const mm = String(this.month + 1).padStart(2, '0');
          const dd = String(day).padStart(2, '0');
          const date = this.year + '-' + mm + '-' + dd;
          cells.push({ day: day, date: date, count: (this.byDay[date] || []).length });
        }
        return cells;
      },

      get selectedSessions() {
        return this.selected ? (this.byDay[this.selected] || []) : [];
      },

      prev() {
        this.month -= 1;
        if (this.month < 0) { this.month = 11; this.year -= 1; }
        this.selected = null;
      },
      next() {
        this.month += 1;
        if (this.month > 11) { this.month = 0; this.year += 1; }
        this.selected = null;
      },
      select(date) {
        this.selected = this.selected === date ? null : date;
      },
    };
  }

  window.topTrackCalendar = topTrackCalendar;
})();
