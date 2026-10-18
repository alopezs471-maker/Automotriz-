/* Inventario público: stock real por vehículo. */
(() => {
  const { api, money, numero, esc, aviso, chipStock, unidades, imagen } = DasAuto;
  const lista = document.getElementById('lista');
  const vacio = document.getElementById('vacio');
  const resumen = document.getElementById('resumen');
  const filtros = {
    categoria: document.getElementById('categoria'),
    buscar: document.getElementById('buscar'),
    solo: document.getElementById('solo-unidades'),
  };
  const etiqueta = { automovil: 'Automóvil', camioneta: 'Camioneta', moto: 'Moto' };
  let vehiculos = [];

  function pintar() {
    const texto = filtros.buscar.value.trim().toLowerCase();
    const categoria = filtros.categoria.value;
    const solo = filtros.solo.checked;
    const visibles = vehiculos.filter(v => {
      if (categoria && v.categoria !== categoria) return false;
      if (solo && !(v.existencias > 0)) return false;
      if (texto && !(v.nombre + ' ' + (v.marca || '') + ' ' + (v.modelo || '')).toLowerCase().includes(texto)) return false;
      return true;
    });
    vacio.hidden = visibles.length > 0;
    resumen.textContent = `${visibles.length} de ${vehiculos.length} vehículos`;
    lista.innerHTML = visibles.map(v => `
      <a class="card" href="vehiculo.html?sku=${encodeURIComponent(v.sku)}">
        <div class="foto"><img src="${esc(v.imagen_url || 'img/car.jpg')}" alt="${esc(v.nombre)}" ${imagen()}></div>
        <div class="cuerpo">
          <span class="categoria">${esc(etiqueta[v.categoria] || v.categoria)} · ${esc(v.propulsion || '')}</span>
          <h3>${esc(v.nombre)}</h3>
          ${v.promo_vigente ? `<span class="antes">${money(v.precio_base)}</span>` : ''}
          <div class="precio">${money(v.precio_venta)}</div>
          <span class="mini">${esc(unidades(v.estado_stock, v.existencias))}</span>
          <div class="pie">
            ${chipStock(v.estado_stock)}
            <span class="btn btn-mini btn-linea">Ver ficha</span>
          </div>
        </div>
      </a>`).join('');
  }

  async function cargar() {
    try {
      const datos = await api('/api/inventario/disponibilidad');
      vehiculos = datos.vehiculos;
      const conUnidades = vehiculos.filter(v => v.existencias > 0).length;
      document.getElementById('resumen').textContent = `${conUnidades} con unidades de ${vehiculos.length}`;
      pintar();
      if (datos.reservas_vencidas_liberadas) {
        aviso(document.getElementById('aviso'),
          `Se liberaron ${numero(datos.reservas_vencidas_liberadas)} reservas vencidas y el stock volvió a estar disponible.`, 'ok');
      }
    } catch (error) {
      aviso(document.getElementById('aviso'), error.message, 'error');
      resumen.textContent = 'Sin datos';
    }
  }

  Object.values(filtros).forEach(campo => {
    campo.addEventListener(campo.type === 'search' ? 'input' : 'change', pintar);
  });
  cargar();
})();
