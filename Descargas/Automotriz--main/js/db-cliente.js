/* Cliente común de las funciones nuevas (financiación, ficha, inventario,
   agenda y panel). No se carga en ninguna página existente. */
window.DasAuto = (() => {
  let token = null;

  async function csrf() {
    if (token) return token;
    const respuesta = await fetch('/api/sesion', { headers: { Accept: 'application/json' } });
    if (!respuesta.ok) throw new Error('El servidor no respondió. Ejecuta: python servidor.py');
    token = (await respuesta.json()).token;
    return token;
  }

  async function api(ruta, opciones = {}) {
    const { metodo = 'GET', cuerpo = null } = opciones;
    const config = { method: metodo, credentials: 'same-origin', headers: { Accept: 'application/json' } };
    if (cuerpo !== null) {
      config.headers['Content-Type'] = 'application/json';
      config.headers['X-CSRF-Token'] = await csrf();
      config.body = JSON.stringify(cuerpo);
    }
    let respuesta;
    try {
      respuesta = await fetch(ruta, config);
    } catch (_) {
      throw new Error('No se pudo conectar. Abre el sitio con python servidor.py (Live Server no guarda en la base).');
    }
    const tipo = respuesta.headers.get('content-type') || '';
    const datos = tipo.includes('json') ? await respuesta.json() : null;
    if (!respuesta.ok) {
      const error = new Error((datos && datos.error) || 'No fue posible completar la operación.');
      error.estado = respuesta.status;
      throw error;
    }
    return datos;
  }

  function uuid() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
      const r = (Math.random() * 16) | 0;
      return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
    });
  }

  const money = valor => new Intl.NumberFormat('es-CO', {
    style: 'currency', currency: 'COP', maximumFractionDigits: 0,
  }).format(Number(valor) || 0);

  const numero = valor => new Intl.NumberFormat('es-CO').format(Number(valor) || 0);

  function fecha(iso) {
    if (!iso) return '—';
    const partes = String(iso).slice(0, 10).split('-');
    return partes.length === 3 ? `${partes[2]}/${partes[1]}/${partes[0]}` : String(iso);
  }

  function fechaHora(valor) {
    if (!valor) return '—';
    return String(valor).replace('T', ' ').slice(0, 16);
  }

  const esc = valor => String(valor === null || valor === undefined ? '' : valor)
    .replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  function aviso(elemento, texto, tipo = '') {
    if (!elemento) return;
    elemento.textContent = texto || '';
    elemento.className = 'aviso' + (tipo ? ' ' + tipo : '');
    elemento.hidden = !texto;
  }

  const qs = nombre => new URLSearchParams(location.search).get(nombre);

  function chipStock(estado) {
    const mapa = {
      disponible: ['ok', 'Disponible'],
      ultimas: ['warn', 'Últimas unidades'],
      agotado: ['bad', 'Agotado'],
      por_confirmar: ['', 'Por confirmar'],
    };
    const [clase, texto] = mapa[estado] || ['', 'Sin dato'];
    return `<span class="chip ${clase}">${texto}</span>`;
  }

  function unidades(estado, existencias) {
    if (existencias === null || existencias === undefined) return 'Stock por confirmar';
    if (existencias === 0) return 'Sin unidades';
    if (existencias === 1) return '1 unidad disponible';
    return `${numero(existencias)} unidades disponibles`;
  }

  const imagen = (url, alterna = 'img/car.jpg') =>
    `onerror="this.onerror=null;this.src='${alterna}'"`;

  return { api, csrf, uuid, money, numero, fecha, fechaHora, esc, aviso, qs, chipStock, unidades, imagen };
})();
