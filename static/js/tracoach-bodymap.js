/*
 * Estado Alpine del mapa corporal editable (formulario de perímetros).
 * Se usa como factoría de x-data: x-data="traCoachBodyMapEditor('<id del json_script>')"
 *
 * Datos esperados en el <script type="application/json" id="...">:
 *   { chest_cm: 96, waist_cm: 80, ... } (o null si no hay medición anterior)
 */
(function () {
  const FIELDS = [
    'chest_cm', 'waist_cm', 'hip_cm',
    'arm_l_cm', 'arm_r_cm', 'thigh_l_cm', 'thigh_r_cm', 'calf_l_cm', 'calf_r_cm',
  ];

  function readJSON(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
  }

  function emptyValues() {
    const v = {};
    FIELDS.forEach(f => { v[f] = ''; });
    return v;
  }

  window.traCoachBodyMapEditor = function (lastValuesId) {
    const last = readJSON(lastValuesId) || {};
    return {
      values: emptyValues(),
      get filledCount() {
        return FIELDS.filter(f => this.values[f] !== '' && this.values[f] !== null && this.values[f] !== undefined).length;
      },
      copyLast() {
        FIELDS.forEach(f => {
          const v = last[f];
          this.values[f] = (v !== undefined && v !== null) ? v : '';
        });
      },
    };
  };
})();
