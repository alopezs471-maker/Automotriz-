/* Datos vivos del centro de funciones nuevas. */
(() => {
  const { api, aviso } = DasAuto;
  const poner = (id, valor) => { document.getElementById(id).textContent = valor; };

  (async () => {
    try {
      const [inventario, financiacion, agenda] = await Promise.all([
        api('/api/inventario/disponibilidad'),
        api('/api/financiacion/datos'),
        api('/api/agenda/disponibilidad'),
      ]);
      poner('kpi-vehiculos', DasAuto.numero(inventario.vehiculos.length));
      poner('kpi-disponibles', DasAuto.numero(inventario.vehiculos.filter(v =>
        v.estado_stock === 'disponible' || v.estado_stock === 'ultimas').length));
      poner('kpi-planes', DasAuto.numero(financiacion.planes.length));
      poner('kpi-cupos', DasAuto.numero(agenda.franjas.reduce((suma, f) => suma + f.disponibles, 0)));
    } catch (error) {
      aviso(document.getElementById('aviso-hub'), error.message, 'error');
    }
  })();
})();
