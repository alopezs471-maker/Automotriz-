/* Panel de administración: sesión, promociones, inventario, agenda,
   financiación, pedidos y usuarios. */
(() => {
  const { api, money, numero, fecha, fechaHora, esc, aviso } = DasAuto;

  const acceso = document.getElementById('acceso');
  const app = document.getElementById('app');
  const vista = document.getElementById('vista');
  const avisoPanel = document.getElementById('aviso-panel');
  const avisoLogin = document.getElementById('aviso-login');
  const kpis = document.getElementById('kpis');
  const tabs = document.getElementById('tabs');

  const hoyISO = () => new Date().toLocaleDateString('sv');
  const ESTADOS_PROMO = { borrador: 'Borrador', publicada: 'Publicada', finalizada: 'Finalizada' };
  const ESTADOS_CITA = ['solicitada', 'confirmada', 'en_taller', 'finalizada', 'cancelada', 'no_show'];
  const ESTADOS_PEDIDO = ['pendiente', 'confirmado', 'facturado', 'cancelado'];
  const ESTADOS_COT = ['simulada', 'enviada', 'aprobada', 'rechazada'];
  const NOMBRE_SERVICIO = {
    mantenimiento: 'Mantenimiento', diagnostico: 'Diagnóstico', frenos: 'Frenos',
    llantas: 'Llantas', bateria: 'Batería', aire_acondicionado: 'Aire acondicionado',
    pintura: 'Pintura', garantia: 'Garantía', otro: 'Otro',
  };

  let admin = null;
  let seccion = 'resumen';
  const cache = {};

  /* ---------------------------------------------------------- utilidades */
  function manejarError(error) {
    if (error && error.estado === 401) return mostrarAcceso();
    aviso(avisoPanel, (error && error.message) || 'No fue posible completar la acción.', 'error');
  }

  const enviar = (accion, datos) =>
    api('/api/admin/accion', { metodo: 'POST', cuerpo: { accion, datos } });

  async function conBoton(boton, tarea) {
    if (boton && boton.disabled) return;
    if (boton) boton.disabled = true;
    try {
      await tarea();
    } catch (error) {
      manejarError(error);
    } finally {
      if (boton) boton.disabled = false;
    }
  }

  async function accionYRefrescar(accion, datos, mensaje) {
    await enviar(accion, datos);
    await cargar(seccion);
    aviso(avisoPanel, mensaje || 'Cambio guardado.', 'ok');
  }

  const chip = (clase, texto) => `<span class="chip ${clase}">${texto}</span>`;

  function chipPromo(fila) {
    if (fila.promo_vigente) return chip('ok', 'Publicada · vigente');
    if (fila.estado === 'publicada') return chip('warn', 'Publicada · fuera de fechas');
    if (fila.estado === 'finalizada') return chip('', 'Finalizada');
    if (fila.estado === 'borrador') return chip('', 'Borrador · no se aplica');
    return chip('', 'Sin promoción');
  }

  const chipStock = estado => ({
    disponible: chip('ok', 'Disponible'),
    ultimas: chip('warn', 'Últimas unidades'),
    agotado: chip('bad', 'Agotado'),
  }[estado] || chip('', 'Por confirmar'));

  const seleccion = (nombre, opciones, actual) => `
    <select name="${esc(nombre)}">
      ${opciones.map(o => `<option value="${esc(o)}"${o === actual ? ' selected' : ''}>${esc(o)}</option>`).join('')}
    </select>`;

  /* ------------------------------------------------------------- sesión */
  function mostrarAcceso() {
    admin = null;
    app.hidden = true;
    acceso.hidden = false;
    kpis.innerHTML = '';
    vista.innerHTML = '';
    document.getElementById('clave').value = '';
    document.getElementById('clave').focus();
  }

  function mostrarApp(datos) {
    admin = datos;
    acceso.hidden = true;
    app.hidden = false;
    document.getElementById('quien').textContent = `${datos.nombre} · ${datos.rol}`;
    cargar('resumen');
  }

  document.getElementById('form-login').addEventListener('submit', async evento => {
    evento.preventDefault();
    const formulario = evento.target;
    const boton = formulario.querySelector('button');
    boton.disabled = true;
    aviso(avisoLogin, 'Verificando…');
    try {
      const datos = await api('/api/admin/login', {
        metodo: 'POST',
        cuerpo: { usuario: formulario.elements.usuario.value, clave: formulario.elements.clave.value },
      });
      formulario.reset();
      aviso(avisoLogin, '');
      mostrarApp(datos);
    } catch (error) {
      aviso(avisoLogin, error.message, 'error');
    } finally {
      boton.disabled = false;
    }
  });

  document.getElementById('salir').addEventListener('click', async () => {
    try { await api('/api/admin/logout', { metodo: 'POST', cuerpo: {} }); } catch (_) { /* da igual */ }
    mostrarAcceso();
  });

  tabs.addEventListener('click', evento => {
    const boton = evento.target.closest('[data-seccion]');
    if (!boton) return;
    cargar(boton.dataset.seccion);
  });

  function marcarTabs() {
    tabs.querySelectorAll('[data-seccion]').forEach(boton =>
      boton.classList.toggle('activo', boton.dataset.seccion === seccion));
  }

  /* ------------------------------------------------------------- cargar */
  async function cargar(nombre = seccion) {
    seccion = nombre;
    marcarTabs();
    aviso(avisoPanel, '');
    vista.innerHTML = '<div class="panel"><p class="nota"><span class="cargando"></span>Cargando…</p></div>';
    try {
      const resumen = await api('/api/admin/resumen');
      pintarKpis(resumen.resumen);
      if (nombre === 'resumen') {
        pintarResumen(resumen);
        return;
      }
      const datos = await api('/api/admin/datos?seccion=' + encodeURIComponent(nombre));
      cache[nombre] = datos;
      (pintores[nombre] || pintarVacio)(datos);
    } catch (error) {
      if (error.estado === 401) return mostrarAcceso();
      vista.innerHTML = `<div class="panel"><p class="aviso error">${esc(error.message)}</p></div>`;
    }
  }

  function pintarKpis(r) {
    kpis.innerHTML = [
      ['Pedidos pendientes', r.pedidos_pendientes, `de ${r.pedidos} en total`],
      ['Citas de hoy', r.citas_hoy, `${r.citas_semana} en 7 días`],
      ['Financiación nueva', r.financiacion_nuevas, `${r.financiacion} solicitudes`],
      ['Stock bajo o agotado', r.stock_bajo + r.agotados, `${r.agotados} agotados`],
      ['Promos vigentes', r.promos_vigentes, `${r.promos_borrador} en borrador`],
      ['Reservas activas', r.reservas_activas, 'unidades comprometidas'],
    ].map(([titulo, valor, pie]) =>
      `<div class="kpi"><b>${numero(valor)}</b><span>${titulo} · ${pie}</span></div>`).join('');
  }

  /* ------------------------------------------------------------ resumen */
  function pintarResumen({ resumen }) {
    vista.innerHTML = `
      <div class="panel">
        <h2>Estado general</h2>
        <p class="nota">Actualizado a las ${esc(fechaHora(resumen.actualizado))}. Los contadores salen
          de la base de datos en vivo.</p>
        <div class="grid3" style="margin-top:14px">
          <button class="btn btn-linea" data-ir="promociones">Publicar promociones</button>
          <button class="btn btn-linea" data-ir="inventario">Ajustar existencias</button>
          <button class="btn btn-linea" data-ir="agenda">Revisar agenda</button>
          <button class="btn btn-linea" data-ir="financiacion">Ver solicitudes</button>
          <button class="btn btn-linea" data-ir="pedidos">Gestionar pedidos</button>
          <button class="btn btn-linea" data-ir="usuarios">Usuarios del panel</button>
        </div>
      </div>
      <div class="panel">
        <h2>Mantenimiento</h2>
        <p class="nota">Los pedidos pendientes reservan unidades durante 48 horas. Si no se confirman,
          la reserva vence y el stock vuelve a estar disponible. El servidor lo hace solo al arrancar,
          pero puedes forzarlo aquí.</p>
        <button class="btn btn-linea" data-vencidas>Liberar reservas vencidas</button>
      </div>
      <div class="panel">
        <h2>Cómo funciona el precio</h2>
        <p class="nota">La oferta se muestra y se cobra solo si la promoción está <b>publicada</b> y
          la fecha de hoy está entre el inicio y el fin. En cualquier otro caso se cobra el precio base.
          Todo cambio de precio queda en el historial.</p>
      </div>`;
  }

  function pintarVacio() {
    vista.innerHTML = '<div class="panel"><p class="nota">Sección sin datos.</p></div>';
  }

  /* ------------------------------------------------------- promociones */
  function pintarPromociones(datos) {
    const filas = datos.filas.map(r => `
      <tr>
        <td class="nombre-celda">${esc(r.nombre)}<div class="sku">${esc(r.sku)}</div></td>
        <td class="monto">${money(r.precio_base)}</td>
        <td class="monto">${r.precio_promocional === null ? '—' : money(r.precio_promocional)}</td>
        <td>${chipPromo(r)}</td>
        <td class="mini">${r.fecha_inicio ? fecha(r.fecha_inicio) : 'sin inicio'} →
          ${r.fecha_fin ? fecha(r.fecha_fin) : 'sin fin'}</td>
        <td class="monto"><b>${money(r.precio_venta)}</b></td>
        <td><button class="btn btn-mini btn-linea" data-editar-promo="${esc(r.sku)}">Editar</button></td>
      </tr>`).join('');

    const archivo = (datos.archivo || []).map(a => `
      <tr>
        <td>${esc(a.nombre)}</td>
        <td>${esc(a.titulo)}</td>
        <td class="monto">${money(a.precio_promocional)}</td>
        <td class="mini">${a.fecha_inicio ? fecha(a.fecha_inicio) : '—'} →
          ${a.fecha_fin ? fecha(a.fecha_fin) : '—'}</td>
        <td class="mini">${esc(fechaHora(a.cerrada_en))}</td>
      </tr>`).join('') || '<tr><td colspan="5" class="vacio">Sin promociones cerradas.</td></tr>';

    vista.innerHTML = `
      <div class="panel">
        <div class="barra">
          <h2>Promociones y precios</h2>
          <div class="der">
            <a class="btn btn-mini btn-linea" href="/api/admin/exportar?seccion=promociones">Exportar CSV</a>
          </div>
        </div>
        <p class="nota">Al guardar se registran el precio base, la oferta, el estado y las fechas.
          La columna <b>Precio de venta</b> es lo que se cobra hoy.</p>
        <div class="tabla-scroll" style="margin-top:12px">
          <table>
            <thead><tr><th>Vehículo</th><th>Precio base</th><th>Oferta</th><th>Estado</th>
              <th>Vigencia</th><th>Precio de venta</th><th></th></tr></thead>
            <tbody>${filas}</tbody>
          </table>
        </div>
      </div>
      <div class="panel">
        <h2>Promociones cerradas</h2>
        <p class="nota">Se archivan solas al pasar a “finalizada” o al borrarlas.</p>
        <div class="tabla-scroll" style="margin-top:10px">
          <table><thead><tr><th>Vehículo</th><th>Título</th><th>Oferta</th><th>Vigencia</th><th>Cerrada</th></tr></thead>
            <tbody>${archivo}</tbody></table>
        </div>
      </div>`;
  }

  function editorPromo(r) {
    return `<tr class="editor"><td colspan="7">
      <form data-promo="${esc(r.sku)}" class="rejilla">
        <div class="campo"><label>Precio base</label>
          <input name="precio_base" type="number" min="0" step="1" value="${r.precio_base}" required></div>
        <div class="campo"><label>Oferta</label>
          <input name="precio_promocional" type="number" min="0" step="1"
                 value="${r.precio_promocional === null ? '' : r.precio_promocional}"></div>
        <div class="campo"><label>Estado</label>
          <select name="estado">
            ${Object.entries(ESTADOS_PROMO).map(([valor, texto]) =>
              `<option value="${valor}"${valor === r.estado ? ' selected' : ''}>${texto}</option>`).join('')}
          </select></div>
        <div class="campo"><label>Inicio</label>
          <input name="fecha_inicio" type="date" value="${r.fecha_inicio || ''}"></div>
        <div class="campo"><label>Fin</label>
          <input name="fecha_fin" type="date" value="${r.fecha_fin || ''}"></div>
        <div class="campo"><label>&nbsp;</label>
          <button class="btn btn-dark" type="submit">Guardar fila</button></div>
      </form></td></tr>`;
  }

  async function guardarPromo(formulario) {
    const sku = formulario.dataset.promo;
    const original = (cache.promociones.filas || []).find(r => r.sku === sku);
    if (!original) return;
    const base = Number(formulario.elements.precio_base.value);
    const oferta = formulario.elements.precio_promocional.value === '' ? null : Number(formulario.elements.precio_promocional.value);
    const estado = formulario.elements.estado.value;
    const inicio = formulario.elements.fecha_inicio.value;
    const fin = formulario.elements.fecha_fin.value;
    if (inicio && fin && fin < inicio) throw new Error('La fecha final no puede ser anterior a la inicial.');
    const pasos = [];
    if (base !== original.precio_base) pasos.push(['precio_base', { sku, precio: base }]);
    if (oferta !== null && oferta !== original.precio_promocional) {
      pasos.push(['promocion_precio', { sku, precio: oferta }]);
    }
    if (estado !== original.estado || inicio !== (original.fecha_inicio || '') ||
        fin !== (original.fecha_fin || '')) {
      pasos.push(['promocion_estado', { sku, estado, fecha_inicio: inicio, fecha_fin: fin }]);
    }
    if (!pasos.length) {
      aviso(avisoPanel, 'No cambiaste nada en esa fila.');
      return;
    }
    for (const [accion, datos] of pasos) await enviar(accion, datos);
    await cargar('promociones');
    aviso(avisoPanel, `Cambios guardados en ${original.nombre}.`, 'ok');
  }

  /* ------------------------------------------------------- inventario */
  function pintarInventario(datos) {
    const filas = datos.filas.map(v => `
      <tr>
        <td class="nombre-celda">${esc(v.nombre)}<div class="sku">${esc(v.sku)}</div></td>
        <td class="mini">${esc(v.categoria)}</td>
        <td class="mini">${esc([v.marca, v.modelo, v.anio].filter(Boolean).join(' ') || 'Sin ficha')}</td>
        <td class="monto">${money(v.precio_venta)}</td>
        <td>
          <div class="usuario-fila">
            <input type="number" min="0" max="999" value="${v.existencias === null ? 0 : v.existencias}"
                   data-stock-input="${esc(v.sku)}" style="max-width:88px">
            <button class="btn btn-mini btn-linea" data-stock="${esc(v.sku)}">Guardar</button>
          </div>
        </td>
        <td>${chipStock(v.estado_stock)}</td>
        <td><button class="btn btn-mini btn-linea" data-editar-ficha="${esc(v.sku)}">Ficha</button></td>
      </tr>`).join('');

    const reservas = (datos.reservas || []).map(r => `
      <tr>
        <td>${esc(r.nombre)} <span class="mini">${esc(r.sku)}</span></td>
        <td class="mini">${esc(r.radicado || '—')}</td>
        <td class="monto">${numero(r.cantidad)}</td>
        <td>${chip(r.estado === 'activa' ? 'warn' : (r.estado === 'consumida' ? 'ok' : ''), r.estado)}</td>
        <td class="mini">${esc(fechaHora(r.expira_en))}</td>
        <td>${r.estado === 'activa'
          ? `<button class="btn btn-mini btn-linea" data-liberar="${r.id}">Liberar</button>` : ''}</td>
      </tr>`).join('') || '<tr><td colspan="6" class="vacio">Sin reservas registradas.</td></tr>';

    const movimientos = (datos.movimientos || []).map(m => `
      <tr>
        <td class="mini">${esc(fechaHora(m.creado_en))}</td>
        <td>${esc(m.nombre)}</td>
        <td>${chip(m.tipo === 'salida' ? 'bad' : (m.tipo === 'entrada' ? 'ok' : 'info'), m.tipo)}</td>
        <td class="monto">${numero(m.cantidad)}</td>
        <td class="monto">${m.saldo_final === null ? '—' : numero(m.saldo_final)}</td>
        <td class="mini">${esc(m.motivo || '')}</td>
        <td class="mini">${esc(m.referencia || '')}</td>
      </tr>`).join('') || '<tr><td colspan="7" class="vacio">Sin movimientos.</td></tr>';

    vista.innerHTML = `
      <div class="panel">
        <div class="barra">
          <h2>Existencias</h2>
          <div class="der">
            <button class="btn btn-mini btn-linea" data-vencidas>Liberar reservas vencidas</button>
            <a class="btn btn-mini btn-linea" href="/api/admin/exportar?seccion=inventario">Exportar CSV</a>
          </div>
        </div>
        <p class="nota">Los pedidos descuentan solos. Aquí se corrige el conteo físico; cada ajuste queda
          en el kardex con su motivo.</p>
        <div class="tabla-scroll" style="margin-top:12px">
          <table>
            <thead><tr><th>Vehículo</th><th>Categoría</th><th>Ficha</th><th>Precio</th>
              <th>Existencias</th><th>Estado</th><th></th></tr></thead>
            <tbody>${filas}</tbody>
          </table>
        </div>
      </div>
      <div class="panel">
        <h2>Reservas de pedidos</h2>
        <p class="nota">Una reserva activa descuenta stock. Se consume al confirmar el pedido y se
          libera al cancelarlo o al vencer (48 h).</p>
        <div class="tabla-scroll" style="margin-top:10px">
          <table><thead><tr><th>Vehículo</th><th>Pedido</th><th>Cantidad</th><th>Estado</th>
            <th>Vence</th><th></th></tr></thead><tbody>${reservas}</tbody></table>
        </div>
      </div>
      <div class="panel">
        <h2>Kardex (últimos movimientos)</h2>
        <div class="tabla-scroll" style="margin-top:10px">
          <table><thead><tr><th>Fecha</th><th>Vehículo</th><th>Tipo</th><th>Cantidad</th>
            <th>Saldo</th><th>Motivo</th><th>Referencia</th></tr></thead><tbody>${movimientos}</tbody></table>
        </div>
      </div>`;
  }

  function editorFicha(v) {
    return `<tr class="editor"><td colspan="7">
      <form data-ficha="${esc(v.sku)}" class="rejilla">
        <div class="campo" style="grid-column:span 2"><label>Descripción</label>
          <textarea name="descripcion" maxlength="1000">${esc(v.descripcion || '')}</textarea></div>
        <div class="campo"><label>Imagen (img/… o http…)</label>
          <input name="imagen_url" maxlength="200" value="${esc(v.imagen_url || '')}"></div>
        <div class="campo"><label>Destacado</label>
          <select name="destacado"><option value="0">No</option>
            <option value="1"${v.destacado ? ' selected' : ''}>Sí</option></select></div>
        <div class="campo"><label>&nbsp;</label>
          <button class="btn btn-dark" type="submit">Guardar ficha</button></div>
      </form></td></tr>`;
  }

  /* ---------------------------------------------------------- historial */
  function pintarPrecios(datos) {
    const filas = (datos.filas || []).map(h => `
      <tr>
        <td class="mini">${esc(fechaHora(h.creado_en))}</td>
        <td class="nombre-celda">${esc(h.nombre)}<div class="sku">${esc(h.sku)}</div></td>
        <td>${chip(h.campo === 'precio_base' ? 'info' : 'warn', h.campo === 'precio_base' ? 'Precio base' : 'Oferta')}</td>
        <td class="monto">${h.valor_anterior === null ? '—' : money(h.valor_anterior)}</td>
        <td class="monto"><b>${money(h.valor_nuevo)}</b></td>
        <td class="mini">${esc(h.origen || '')}</td>
      </tr>`).join('') || '<tr><td colspan="6" class="vacio">Sin registros.</td></tr>';
    vista.innerHTML = `
      <div class="panel">
        <div class="barra">
          <h2>Historial de precios</h2>
          <div class="der">
            <a class="btn btn-mini btn-linea" href="/api/admin/exportar?seccion=precios">Exportar CSV</a>
          </div>
        </div>
        <p class="nota">Los cambios se registran solos con los disparadores <code>tr_precio_*</code>.
          Aplica a precios base y a ofertas, vengan del panel, de <code>gestionar.py</code> o de SQL.</p>
        <div class="tabla-scroll" style="margin-top:12px">
          <table><thead><tr><th>Cuándo</th><th>Vehículo</th><th>Campo</th>
            <th>Antes</th><th>Ahora</th><th>Origen</th></tr></thead><tbody>${filas}</tbody></table>
        </div>
      </div>`;
  }

  /* -------------------------------------------------------------- agenda */
  function pintarAgenda(datos) {
    const citas = datos.citas.map(c => `
      <tr>
        <td class="nombre-celda">${esc(c.nombre)}<div class="sku">${esc(c.radicado)}</div></td>
        <td class="mini">${esc(fecha(c.fecha_programada))} · ${esc(c.hora_programada)}</td>
        <td>${esc(NOMBRE_SERVICIO[c.servicio] || c.servicio)}</td>
        <td class="mini">${esc(c.placa || '—')}<br>${esc(c.telefono || '')}</td>
        <td>
          <div class="usuario-fila">
            ${seleccion('estado', ESTADOS_CITA, c.estado).replace('<select', `<select data-cita="${esc(c.radicado)}"`)}
            <button class="btn btn-mini btn-linea" data-guardar-cita="${esc(c.radicado)}">Guardar</button>
          </div>
        </td>
      </tr>`).join('') || '<tr><td colspan="5" class="vacio">Sin citas registradas.</td></tr>';

    vista.innerHTML = `
      <div class="panel">
        <div class="barra">
          <h2>Cupos por franja</h2>
          <div class="der">
            <span class="mini">Capacidad por defecto: 2 citas por hora</span>
          </div>
        </div>
        <p class="nota">Fija cuántas citas caben en cada hora. 0 cierra la franja; el máximo es 20.</p>
        <div class="barra" style="margin-top:12px">
          <div class="campo" style="margin:0;max-width:190px">
            <label for="fecha-cupos">Fecha</label>
            <input id="fecha-cupos" type="date" value="${hoyISO()}" min="${hoyISO()}">
          </div>
          <button class="btn btn-mini btn-linea" data-ver-cupos>Ver cupos</button>
        </div>
        <div class="especificaciones" id="cupos-dia">
          <p class="nota"><span class="cargando"></span>Consultando…</p>
        </div>
      </div>
      <div class="panel">
        <h2>Citas</h2>
        <p class="nota">Cambiar a “cancelada” o “no_show” libera el cupo de inmediato.</p>
        <div class="tabla-scroll" style="margin-top:12px">
          <table><thead><tr><th>Cliente</th><th>Fecha</th><th>Servicio</th><th>Contacto</th><th>Estado</th></tr></thead>
            <tbody>${citas}</tbody></table>
        </div>
      </div>`;

    cargarCupos(hoyISO()).catch(manejarError);
  }

  async function cargarCupos(fecha) {
    const caja = document.getElementById('cupos-dia');
    if (!caja) return;
    caja.innerHTML = '<p class="nota"><span class="cargando"></span>Consultando…</p>';
    const datos = await api('/api/agenda/disponibilidad?fecha=' + encodeURIComponent(fecha));
    caja.innerHTML = datos.franjas.map(f => `
      <div class="spec">
        <dt>${esc(f.hora)}</dt>
        <dd>${f.disponibles} de ${f.capacidad} libres</dd>
        <div class="usuario-fila" style="margin-top:8px">
          <input type="number" min="0" max="20" value="${f.capacidad}"
                 data-capacidad="${esc(f.hora)}" style="max-width:80px">
          <button class="btn btn-mini btn-linea" data-cupo="${esc(f.hora)}">Fijar</button>
        </div>
      </div>`).join('');
  }

  /* -------------------------------------------------------- financiación */
  function pintarFinanciacion(datos) {
    const planes = (datos.planes || []).map(p => `
      <tr>
        <td class="nombre-celda">${esc(p.nombre)}<div class="sku">${p.plazo_min}–${p.plazo_max} meses</div></td>
        <td class="monto">${String(p.inicial_min_pct).replace('.', ',')} %</td>
        <td>
          <form data-tasa="${p.id}" class="usuario-fila">
            <input name="tasa_anual" type="number" step="0.01" min="0" max="100"
                   value="${p.tasa_anual}" style="max-width:110px"> % E.A.
            <select name="activo"><option value="1"${p.activo ? ' selected' : ''}>Activo</option>
              <option value="0"${p.activo ? '' : ' selected'}>Inactivo</option></select>
            <button class="btn btn-mini btn-linea">Guardar</button>
          </form>
        </td>
      </tr>`).join('');

    const solicitudes = (datos.filas || []).map(c => `
      <tr>
        <td class="nombre-celda">${esc(c.nombre)}<div class="sku">${esc(c.email)}</div></td>
        <td>${esc(c.vehiculo || c.sku || '—')}</td>
        <td class="monto">${money(c.precio_vehiculo)}</td>
        <td class="monto">${money(c.cuota_inicial)}</td>
        <td>${c.plazo_meses} meses · ${c.tasa_anual.toFixed(2).replace('.', ',')} %</td>
        <td class="monto"><b>${money(c.cuota_mensual)}</b></td>
        <td>${chip(c.estado === 'aprobada' ? 'ok' : (c.estado === 'rechazada' ? 'bad' : 'info'), c.estado)}</td>
        <td>
          <div class="usuario-fila">
            ${seleccion('estado', ESTADOS_COT, c.estado).replace('<select', `<select data-cotizacion="${c.id}"`)}
            <button class="btn btn-mini btn-linea" data-guardar-cotizacion="${c.id}">Guardar</button>
          </div>
        </td>
      </tr>`).join('') || '<tr><td colspan="8" class="vacio">Sin solicitudes todavía.</td></tr>';

    vista.innerHTML = `
      <div class="panel">
        <h2>Planes y tasas</h2>
        <p class="nota">La tasa que se guarda aquí es la que usa el simulador. Cambiarla no altera
          las solicitudes ya registradas (cada una guarda su tasa).</p>
        <div class="tabla-scroll" style="margin-top:12px">
          <table><thead><tr><th>Plan</th><th>Cuota inicial mínima</th><th>Tasa anual</th></tr></thead>
            <tbody>${planes}</tbody></table>
        </div>
      </div>
      <div class="panel">
        <div class="barra">
          <h2>Solicitudes</h2>
          <div class="der">
            <a class="btn btn-mini btn-linea" href="/api/admin/exportar?seccion=financiacion">Exportar CSV</a>
          </div>
        </div>
        <div class="tabla-scroll" style="margin-top:12px">
          <table><thead><tr><th>Cliente</th><th>Vehículo</th><th>Precio</th><th>Inicial</th>
            <th>Plan</th><th>Cuota</th><th>Estado</th><th></th></tr></thead>
            <tbody>${solicitudes}</tbody></table>
        </div>
      </div>`;
  }

  /* ------------------------------------------------------------- pedidos */
  function pintarPedidos(datos) {
    const filas = (datos.filas || []).map(p => `
      <tr>
        <td class="nombre-celda">${esc(p.radicado)}<div class="sku">${esc(fechaHora(p.creado_en))}</div></td>
        <td>${esc(p.nombre)}<div class="mini">${esc(p.email)} · ${esc(p.telefono)}</div></td>
        <td class="mini">${(p.items || []).map(i =>
          `${esc(i.nombre)} × ${numero(i.cantidad)}`).join('<br>') || '—'}</td>
        <td class="monto"><b>${money(p.total)}</b></td>
        <td>${chip(p.estado === 'cancelado' ? 'bad' : (p.estado === 'pendiente' ? 'warn' : 'ok'), p.estado)}</td>
        <td>
          <div class="usuario-fila">
            ${seleccion('estado', ESTADOS_PEDIDO, p.estado).replace('<select', `<select data-pedido="${esc(p.radicado)}"`)}
            <button class="btn btn-mini btn-linea" data-guardar-pedido="${esc(p.radicado)}">Guardar</button>
          </div>
        </td>
      </tr>`).join('') || '<tr><td colspan="6" class="vacio">Sin pedidos registrados.</td></tr>';

    vista.innerHTML = `
      <div class="panel">
        <div class="barra">
          <h2>Pedidos</h2>
          <div class="der">
            <a class="btn btn-mini btn-linea" href="/api/admin/exportar?seccion=pedidos">Exportar CSV</a>
          </div>
        </div>
        <p class="nota">Confirmar consume la reserva; cancelar devuelve las unidades al inventario.</p>
        <div class="tabla-scroll" style="margin-top:12px">
          <table><thead><tr><th>Pedido</th><th>Cliente</th><th>Vehículos</th><th>Total</th>
            <th>Estado</th><th></th></tr></thead><tbody>${filas}</tbody></table>
        </div>
      </div>`;
  }

  /* ------------------------------------------------------------ usuarios */
  function pintarUsuarios(datos) {
    const filas = datos.filas.map(u => `
      <tr>
        <td class="nombre-celda">${esc(u.usuario)}<div class="sku">${esc(u.nombre)}</div></td>
        <td>${chip(u.rol === 'admin' ? 'info' : '', u.rol)}</td>
        <td>${chip(u.activo ? 'ok' : 'bad', u.activo ? 'Activo' : 'Inactivo')}</td>
        <td class="mini">${u.ultimo_acceso ? esc(fechaHora(u.ultimo_acceso)) : 'nunca'}</td>
        <td>
          <form data-clave="${esc(u.usuario)}" class="usuario-fila">
            <input name="clave" type="password" minlength="8" maxlength="200"
                   placeholder="Nueva clave" required style="max-width:170px">
            <button class="btn btn-mini btn-linea">Cambiar</button>
          </form>
        </td>
        <td><button class="btn btn-mini btn-linea" data-usuario-activo="${esc(u.usuario)}"
          data-activo="${u.activo ? 0 : 1}">${u.activo ? 'Desactivar' : 'Activar'}</button></td>
      </tr>`).join('');

    vista.innerHTML = `
      <div class="panel">
        <h2>Nuevo usuario</h2>
        <p class="nota">Roles: <b>admin</b> (todo), <b>ventas</b> (promociones, pedidos y financiación),
          <b>taller</b> (agenda) y <b>consulta</b> (solo lectura).</p>
        <form data-crear-usuario class="rejilla" style="margin-top:12px">
          <div class="campo"><label>Usuario</label>
            <input name="usuario" maxlength="30" pattern="[a-z0-9._-]{3,30}" required></div>
          <div class="campo"><label>Nombre</label>
            <input name="nombre" maxlength="150" required></div>
          <div class="campo"><label>Rol</label>
            <select name="rol">${datos.roles.map(r => `<option value="${esc(r)}">${esc(r)}</option>`).join('')}</select></div>
          <div class="campo"><label>Clave (mín. 8)</label>
            <input name="clave" type="password" minlength="8" maxlength="200" required></div>
          <div class="campo"><label>&nbsp;</label>
            <button class="btn btn-dark" type="submit">Crear usuario</button></div>
        </form>
      </div>
      <div class="panel">
        <h2>Usuarios del panel</h2>
        <div class="tabla-scroll" style="margin-top:12px">
          <table><thead><tr><th>Usuario</th><th>Rol</th><th>Estado</th><th>Último acceso</th>
            <th>Cambiar clave</th><th></th></tr></thead><tbody>${filas}</tbody></table>
        </div>
      </div>`;
  }

  const pintores = {
    promociones: pintarPromociones,
    precios: pintarPrecios,
    inventario: pintarInventario,
    agenda: pintarAgenda,
    financiacion: pintarFinanciacion,
    pedidos: pintarPedidos,
    usuarios: pintarUsuarios,
  };

  /* ------------------------------------------------------------ eventos */
  vista.addEventListener('click', evento => {
    const ir = evento.target.closest('[data-ir]');
    if (ir) {
      evento.preventDefault();
      return cargar(ir.dataset.ir);
    }

    const editarPromo = evento.target.closest('[data-editar-promo]');
    if (editarPromo) {
      const fila = editarPromo.closest('tr');
      const siguiente = fila.nextElementSibling;
      if (siguiente && siguiente.classList.contains('editor')) {
        siguiente.remove();
        return;
      }
      const datos = (cache.promociones.filas || []).find(r => r.sku === editarPromo.dataset.editarPromo);
      if (datos) fila.insertAdjacentHTML('afterend', editorPromo(datos));
      return;
    }

    const stock = evento.target.closest('[data-stock]');
    if (stock) {
      const sku = stock.dataset.stock;
      const campo = vista.querySelector(`[data-stock-input="${sku}"]`);
      return conBoton(stock, () => accionYRefrescar('stock_fijar',
        { sku, cantidad: Number(campo.value) }, `Existencias de ${sku} actualizadas.`));
    }

    const ficha = evento.target.closest('[data-editar-ficha]');
    if (ficha) {
      const fila = ficha.closest('tr');
      const siguiente = fila.nextElementSibling;
      if (siguiente && siguiente.classList.contains('editor')) {
        siguiente.remove();
        return;
      }
      const datos = (cache.inventario.filas || []).find(r => r.sku === ficha.dataset.editarFicha);
      if (datos) fila.insertAdjacentHTML('afterend', editorFicha(datos));
      return;
    }

    const liberar = evento.target.closest('[data-liberar]');
    if (liberar) {
      return conBoton(liberar, () => accionYRefrescar('reserva_liberar',
        { id: Number(liberar.dataset.liberar) }, 'Reserva liberada: las unidades volvieron al stock.'));
    }

    const vencidas = evento.target.closest('[data-vencidas]');
    if (vencidas) {
      return conBoton(vencidas, async () => {
        const respuesta = await enviar('reservas_vencidas', {});
        await cargar(seccion);
        aviso(avisoPanel, `Reservas vencidas liberadas: ${numero(respuesta.liberadas || 0)}.`, 'ok');
      });
    }

    const verCupos = evento.target.closest('[data-ver-cupos]');
    if (verCupos) {
      const campo = document.getElementById('fecha-cupos');
      return conBoton(verCupos, () => cargarCupos(campo.value));
    }

    const cupo = evento.target.closest('[data-cupo]');
    if (cupo) {
      const hora = cupo.dataset.cupo;
      const fechaCupo = document.getElementById('fecha-cupos').value;
      const capacidad = Number(vista.querySelector(`[data-capacidad="${hora}"]`).value);
      return conBoton(cupo, async () => {
        await enviar('cupo_fijar', { fecha: fechaCupo, hora, capacidad });
        await cargarCupos(fechaCupo);
        aviso(avisoPanel, `Cupo de las ${hora} actualizado a ${capacidad}.`, 'ok');
      });
    }

    const guardarCita = evento.target.closest('[data-guardar-cita]');
    if (guardarCita) {
      const radicado = guardarCita.dataset.guardarCita;
      const estado = vista.querySelector(`[data-cita="${radicado}"]`).value;
      return conBoton(guardarCita, () => accionYRefrescar('cita_estado',
        { radicado, estado }, `Cita ${radicado}: ${estado}.`));
    }

    const guardarPedido = evento.target.closest('[data-guardar-pedido]');
    if (guardarPedido) {
      const radicado = guardarPedido.dataset.guardarPedido;
      const estado = vista.querySelector(`[data-pedido="${radicado}"]`).value;
      return conBoton(guardarPedido, () => accionYRefrescar('pedido_estado',
        { radicado, estado }, `Pedido ${radicado}: ${estado}.`));
    }

    const guardarCot = evento.target.closest('[data-guardar-cotizacion]');
    if (guardarCot) {
      const id = Number(guardarCot.dataset.guardarCotizacion);
      const estado = vista.querySelector(`[data-cotizacion="${id}"]`).value;
      return conBoton(guardarCot, () => accionYRefrescar('financiacion_estado',
        { id, estado }, `Solicitud #${id}: ${estado}.`));
    }

    const activar = evento.target.closest('[data-usuario-activo]');
    if (activar) {
      const usuario = activar.dataset.usuarioActivo;
      const activo = Number(activar.dataset.activo);
      return conBoton(activar, () => accionYRefrescar('usuario_activo',
        { usuario, activo }, `Usuario ${usuario}: ${activo ? 'activado' : 'desactivado'}.`));
    }
  });

  vista.addEventListener('submit', evento => {
    const formulario = evento.target.closest('form');
    if (!formulario) return;

    if (formulario.matches('form[data-promo]')) {
      evento.preventDefault();
      return conBoton(formulario.querySelector('button'), () => guardarPromo(formulario));
    }

    if (formulario.matches('form[data-ficha]')) {
      evento.preventDefault();
      return conBoton(formulario.querySelector('button'), async () => {
        await enviar('ficha_editar', {
          sku: formulario.dataset.ficha,
          descripcion: formulario.elements.descripcion.value,
          imagen_url: formulario.elements.imagen_url.value,
          destacado: Number(formulario.elements.destacado.value),
        });
        await cargar('inventario');
        aviso(avisoPanel, 'Ficha actualizada.', 'ok');
      });
    }

    if (formulario.matches('form[data-tasa]')) {
      evento.preventDefault();
      return conBoton(formulario.querySelector('button'), async () => {
        await enviar('tasa_actualizar', {
          id: Number(formulario.dataset.tasa),
          tasa_anual: Number(formulario.elements.tasa_anual.value),
          activo: Number(formulario.elements.activo.value),
        });
        await cargar('financiacion');
        aviso(avisoPanel, 'Plan actualizado.', 'ok');
      });
    }

    if (formulario.matches('form[data-clave]')) {
      evento.preventDefault();
      return conBoton(formulario.querySelector('button'), async () => {
        await enviar('usuario_clave', {
          usuario: formulario.dataset.clave,
          clave: formulario.elements.clave.value,
        });
        formulario.reset();
        aviso(avisoPanel, 'Clave cambiada.', 'ok');
      });
    }

    if (formulario.matches('form[data-crear-usuario]')) {
      evento.preventDefault();
      return conBoton(formulario.querySelector('button'), async () => {
        await enviar('usuario_crear', {
          usuario: formulario.elements.usuario.value.toLowerCase(),
          nombre: formulario.elements.nombre.value,
          rol: formulario.elements.rol.value,
          clave: formulario.elements.clave.value,
        });
        await cargar('usuarios');
        aviso(avisoPanel, 'Usuario creado.', 'ok');
      });
    }
  });

  /* -------------------------------------------------------------- inicio */
  (async () => {
    try {
      const estado = await api('/api/admin/estado');
      if (estado.sesion) mostrarApp(estado);
      else mostrarAcceso();
    } catch (error) {
      mostrarAcceso();
      aviso(avisoLogin, error.message, 'error');
    }
  })();
})();
