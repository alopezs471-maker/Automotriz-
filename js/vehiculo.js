/* Ficha del vehículo: datos, precio vigente, stock e historial. */
(() => {
  const { api, money, fechaHora, esc, aviso, qs, unidades, imagen } = DasAuto;
  const miga = document.getElementById('miga');
  const caja = document.getElementById('detalle');
  const cargando = document.getElementById('cargando-panel');

  const bonito = clave => {
    const texto = String(clave).replace(/_/g, ' ');
    return texto.charAt(0).toUpperCase() + texto.slice(1);
  };

  function pintar(vehiculo) {
    document.title = `${vehiculo.nombre} · DasAuto`;
    document.getElementById('nombre').textContent = vehiculo.nombre;
    document.getElementById('descripcion').textContent = vehiculo.descripcion ||
      'Ficha pendiente de completar. Se puede editar desde el panel de administración.';

    miga.innerHTML = `<a href="disponibilidad.html">Inventario</a> / ${esc(vehiculo.nombre)}`;

    const foto = document.getElementById('foto');
    foto.src = vehiculo.imagen_url || 'img/car.jpg';
    foto.alt = vehiculo.nombre;
    foto.onerror = () => { foto.onerror = null; foto.src = 'img/car.jpg'; };

    const stock = document.getElementById('stock');
    const estilos = { disponible: ['ok', 'Disponible'], ultimas: ['warn', 'Últimas unidades'],
                      agotado: ['bad', 'Agotado'] };
    const [clase, texto] = estilos[vehiculo.estado_stock] || ['', 'Por confirmar'];
    stock.className = 'chip ' + clase;
    stock.textContent = texto;
    document.getElementById('unidades').textContent = unidades(vehiculo.estado_stock, vehiculo.existencias);

    document.getElementById('precio').innerHTML = `${money(vehiculo.precio_venta)}`;
    const antes = document.getElementById('antes');
    if (vehiculo.promo_vigente) {
      antes.hidden = false;
      antes.innerHTML = `Antes ${money(vehiculo.precio_base)}`;
      const promo = document.getElementById('promo');
      promo.hidden = false;
      promo.textContent = `Oferta vigente${vehiculo.titulo ? ': ' + vehiculo.titulo : ''}` +
        `${vehiculo.beneficio ? ' · ' + vehiculo.beneficio : ''}`;
    }

    const specs = document.getElementById('specs');
    const detalle = vehiculo.especificaciones || {};
    specs.innerHTML = Object.entries(detalle).map(([clave, valor]) => `
      <div class="spec"><dt>${esc(bonito(clave))}</dt><dd>${esc(valor)}</dd></div>`).join('') ||
      '<div class="spec"><dt>Ficha técnica</dt><dd>Por completar</dd></div>';

    document.getElementById('financiar').href = `financiar.html?sku=${encodeURIComponent(vehiculo.sku)}`;
    document.getElementById('vendido-por').textContent =
      [vehiculo.marca, vehiculo.modelo, vehiculo.anio].filter(Boolean).join(' · ') ||
      'Ficha por completar';

    if (vehiculo.financiacion_estimada) {
      const f = vehiculo.financiacion_estimada;
      document.getElementById('caja-financiacion').hidden = false;
      document.getElementById('cuota-estimada').innerHTML = `${money(f.cuota_mensual)} <small>/ mes</small>`;
      document.getElementById('detalle-financiacion').textContent =
        `${f.plazo_meses} meses · ${f.tasa_anual.toFixed(2).replace('.', ',')} % E.A. · ` +
        `cuota inicial de ${money(f.cuota_inicial)}.`;
      document.getElementById('enlace-financiar').href =
        `financiar.html?sku=${encodeURIComponent(vehiculo.sku)}`;
    }

    const historial = vehiculo.historial || [];
    document.getElementById('sin-historial').hidden = historial.length > 0;
    document.getElementById('historial').innerHTML = historial.map(h => {
      const nombreCampo = h.campo === 'precio_base' ? 'Precio base' : 'Oferta';
      let texto;
      if (h.valor_anterior === null || h.valor_anterior === undefined) {
        texto = `${nombreCampo}: ${money(h.valor_nuevo)}`;
      } else {
        texto = `${nombreCampo}: ${money(h.valor_anterior)} → <b>${money(h.valor_nuevo)}</b>`;
      }
      return `<li><span class="punto"></span><div>${texto}
        <div class="cuando">${esc(h.origen || 'cambio')} · ${esc(fechaHora(h.creado_en))}</div></div></li>`;
    }).join('');

    const similares = vehiculo.similares || [];
    if (similares.length) {
      document.getElementById('caja-similares').hidden = false;
      document.getElementById('similares').innerHTML = similares.map(s => `
        <a class="card" href="vehiculo.html?sku=${encodeURIComponent(s.sku)}">
          <div class="foto"><img src="${esc(s.imagen_url || 'img/car.jpg')}" alt="${esc(s.nombre)}" ${imagen()}></div>
          <div class="cuerpo">
            <span class="categoria">${esc(s.sku)}</span>
            <h3>${esc(s.nombre)}</h3>
            <div class="precio">${money(s.precio_venta)}</div>
          </div>
        </a>`).join('');
    }

    caja.hidden = false;
    cargando.hidden = true;
  }

  (async () => {
    const sku = qs('sku');
    if (!sku) {
      cargando.hidden = true;
      const cajaAviso = document.getElementById('aviso');
      cajaAviso.className = 'aviso error';
      cajaAviso.innerHTML = 'Elige un vehículo en <a href="disponibilidad.html"><b>Inventario</b></a>.';
      cajaAviso.hidden = false;
      return;
    }
    try {
      const datos = await api('/api/ficha?sku=' + encodeURIComponent(sku));
      pintar(datos.vehiculo);
    } catch (error) {
      cargando.hidden = true;
      aviso(document.getElementById('aviso'), error.message, 'error');
    }
  })();
})();
