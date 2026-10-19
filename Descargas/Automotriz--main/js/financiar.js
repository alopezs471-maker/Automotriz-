/* Simulador de financiación: precios, planes y tasas salen de la base. */
(() => {
  const { api, money, numero, aviso, qs, uuid, esc } = DasAuto;
  const form = document.getElementById('form-sim');
  const formSolicitud = document.getElementById('form-solicitud');
  const avisoSim = document.getElementById('aviso-sim');
  const avisoSolicitud = document.getElementById('aviso-solicitud');
  const resultado = document.getElementById('resultado');
  const sinResultado = document.getElementById('sin-resultado');
  const btnSolicitar = document.getElementById('btn-solicitar');

  let catalogo = null;
  let ultima = null;
  let envio = null;

  const inicial = form.elements.cuota_inicial;
  const plazo = form.elements.plazo_meses;

  const planActual = () => {
    if (!catalogo) return null;
    const meses = Number(plazo.value);
    return catalogo.planes.find(p => meses >= p.plazo_min && meses <= p.plazo_max) || null;
  };

  const vehiculoActual = () => catalogo && catalogo.vehiculos.find(v => v.sku === form.elements.sku.value);

  function pintarPlanes() {
    document.getElementById('tabla-planes').innerHTML = catalogo.planes.map(p => `
      <tr>
        <td class="nombre-celda">${esc(p.nombre)}</td>
        <td>${p.plazo_min}–${p.plazo_max} meses</td>
        <td>${p.tasa_anual.toFixed(2).replace('.', ',')} % E.A.</td>
        <td>${String(p.inicial_min_pct).replace('.', ',')} %</td>
      </tr>`).join('') || '<tr><td colspan="4" class="vacio">Sin planes activos.</td></tr>';
  }

  function ajustarCampos(ponerInicial) {
    const vehiculo = vehiculoActual();
    const plan = planActual();
    if (!vehiculo) {
      document.getElementById('nota-plan').textContent = 'Elige un vehículo para ver el plan.';
      return;
    }
    if (!plan) {
      document.getElementById('nota-plan').textContent = 'No hay plan para ese plazo.';
      return;
    }
    const minimo = Math.ceil(vehiculo.precio_venta * plan.inicial_min_pct / 100);
    inicial.min = minimo;
    inicial.max = vehiculo.precio_venta - 100000;
    if (ponerInicial || !inicial.value || Number(inicial.value) < minimo) inicial.value = minimo;
    document.getElementById('nota-plan').innerHTML =
      `${esc(vehiculo.nombre)} · ${money(vehiculo.precio_venta)} · plan con tasa ` +
      `${plan.tasa_anual.toFixed(2).replace('.', ',')} % E.A. y cuota inicial mínima de ` +
      `${money(minimo)} (${String(plan.inicial_min_pct).replace('.', ',')} %).`;
  }

  async function cargar() {
    try {
      catalogo = await api('/api/financiacion/datos');
      const porCategoria = new Map();
      for (const v of catalogo.vehiculos) {
        if (!porCategoria.has(v.categoria)) porCategoria.set(v.categoria, []);
        porCategoria.get(v.categoria).push(v);
      }
      const etiqueta = { automovil: 'Automóviles', camioneta: 'Camionetas', moto: 'Motos' };
      form.elements.sku.innerHTML = '<option value="">Elige un vehículo…</option>' +
        [...porCategoria.entries()].map(([categoria, lista]) => `
          <optgroup label="${esc(etiqueta[categoria] || categoria)}">
            ${lista.map(v => `<option value="${esc(v.sku)}">${esc(v.nombre)} — ${money(v.precio_venta)}</option>`).join('')}
          </optgroup>`).join('');
      plazo.innerHTML = [12, 18, 24, 36, 48, 60, 72, 84]
        .map(m => `<option value="${m}"${m === 48 ? ' selected' : ''}>${m} meses</option>`).join('');
      pintarPlanes();
      const sku = qs('sku');
      if (sku && catalogo.vehiculos.some(v => v.sku === sku)) form.elements.sku.value = sku;
      ajustarCampos(true);
    } catch (error) {
      aviso(avisoSim, error.message, 'error');
      document.getElementById('vehiculo').innerHTML = '<option value="">Sin datos</option>';
    }
  }

  form.elements.sku.addEventListener('change', () => ajustarCampos(true));
  plazo.addEventListener('change', () => ajustarCampos(true));

  form.addEventListener('submit', async evento => {
    evento.preventDefault();
    if (!form.reportValidity()) return;
    const boton = form.querySelector('[type=submit]');
    boton.disabled = true;
    aviso(avisoSim, 'Calculando con las tasas de la base…');
    try {
      const datos = await api('/api/financiacion/simular', {
        metodo: 'POST',
        cuerpo: {
          sku: form.elements.sku.value,
          cuota_inicial: Number(inicial.value),
          plazo_meses: Number(plazo.value),
        },
      });
      ultima = datos.simulacion;
      sinResultado.hidden = true;
      resultado.hidden = false;
      formSolicitud.hidden = true;
      btnSolicitar.hidden = false;
      document.getElementById('cuota').innerHTML = `${money(ultima.cuota_mensual)} <small>/ mes</small>`;
      document.getElementById('plan-elegido').textContent =
        `${ultima.nombre} · ${ultima.plazo_meses} meses · ${ultima.plan}`;
      document.getElementById('r-precio').textContent = money(ultima.precio);
      document.getElementById('r-inicial').textContent = money(ultima.cuota_inicial);
      document.getElementById('r-capital').textContent = money(ultima.capital);
      document.getElementById('r-tasa').textContent = `${ultima.tasa_anual.toFixed(2).replace('.', ',')} % E.A.`;
      document.getElementById('r-intereses').textContent = money(ultima.total_intereses);
      document.getElementById('r-total').textContent = money(ultima.total_a_pagar);
      aviso(avisoSim, '');
    } catch (error) {
      aviso(avisoSim, error.message, 'error');
    } finally {
      boton.disabled = false;
    }
  });

  btnSolicitar.addEventListener('click', () => {
    btnSolicitar.hidden = true;
    formSolicitud.hidden = false;
    envio = uuid();
    formSolicitud.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  });

  formSolicitud.addEventListener('submit', async evento => {
    evento.preventDefault();
    if (!formSolicitud.reportValidity() || !ultima) return;
    const boton = formSolicitud.querySelector('[type=submit]');
    boton.disabled = true;
    aviso(avisoSolicitud, 'Guardando la solicitud…');
    try {
      const respuesta = await api('/api/financiacion/solicitar', {
        metodo: 'POST',
        cuerpo: {
          sku: ultima.sku,
          cuota_inicial: ultima.cuota_inicial,
          plazo_meses: ultima.plazo_meses,
          nombre: formSolicitud.elements.nombre.value,
          documento: formSolicitud.elements.documento.value,
          telefono: formSolicitud.elements.telefono.value,
          email: formSolicitud.elements.email.value,
          terminos: formSolicitud.elements.terminos.checked,
          envio_id: envio,
        },
      });
      aviso(avisoSolicitud,
        `Solicitud registrada. Radicado ${respuesta.radicado}. Un asesor te contactará; ` +
        `la cuota simulada es ${money(respuesta.simulacion.cuota_mensual)}.`, 'ok');
      formSolicitud.querySelector('[type=submit]').textContent = 'Solicitud guardada';
      formSolicitud.reset();
    } catch (error) {
      aviso(avisoSolicitud, error.message, 'error');
      boton.disabled = false;
    }
  });

  cargar();
})();
