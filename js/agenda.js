/* Agenda de taller con cupos por franja. */
(() => {
  const { api, esc, aviso, uuid, fecha: fmtFecha } = DasAuto;
  const campoFecha = document.getElementById('fecha');
  const franjas = document.getElementById('franjas');
  const estadoFranjas = document.getElementById('estado-franjas');
  const formCita = document.getElementById('form-cita');
  const sinFranja = document.getElementById('sin-franja');
  const avisoCita = document.getElementById('aviso-cita');
  const avisoAgenda = document.getElementById('aviso-agenda');
  const servicio = document.getElementById('servicio');
  const nombresServicio = {
    mantenimiento: 'Mantenimiento preventivo', diagnostico: 'Diagnóstico',
    frenos: 'Frenos', llantas: 'Llantas', bateria: 'Batería',
    aire_acondicionado: 'Aire acondicionado', pintura: 'Pintura',
    garantia: 'Garantía', otro: 'Otro',
  };
  let elegida = null;
  let envio = null;
  let maxFecha = null;

  const hoyISO = new Date().toLocaleDateString('sv');

  function pintarFranjas(datos) {
    estadoFranjas.textContent = `${datos.franjas.filter(f => f.abierta).length} franjas con cupo para el ` +
      `${fmtFecha(datos.fecha)}.`;
    franjas.innerHTML = datos.franjas.map(f => `
      <button type="button" class="slot ${f.abierta ? '' : (f.activo ? 'lleno' : 'cerrado')}"
              data-hora="${esc(f.hora)}" ${f.abierta ? '' : 'disabled'}
              title="${f.abierta ? f.disponibles + ' cupos libres' : 'Sin cupo'}">
        <b>${esc(f.hora)}</b>
        <span>${f.activo ? (f.disponibles > 0 ? f.disponibles + ' cupo(s)' : 'Lleno') : 'Cerrado'}</span>
      </button>`).join('');
    if (!datos.franjas.some(f => f.abierta)) {
      estadoFranjas.textContent = 'No quedan franjas con cupo ese día. Prueba otra fecha.';
    }
  }

  async function cargar() {
    try {
      const datos = await api('/api/agenda/disponibilidad?fecha=' + encodeURIComponent(campoFecha.value));
      maxFecha = datos.max_fecha;
      campoFecha.min = datos.hoy;
      campoFecha.max = datos.max_fecha;
      document.getElementById('rango-fecha').textContent =
        `De hoy al ${fmtFecha(datos.max_fecha)}.`;
      pintarFranjas(datos);
      if (!servicio.options.length) {
        servicio.innerHTML = datos.servicios
          .map(s => `<option value="${esc(s)}">${esc(nombresServicio[s] || s)}</option>`).join('');
      }
      aviso(avisoAgenda, '');
    } catch (error) {
      aviso(avisoAgenda, error.message, 'error');
      estadoFranjas.textContent = 'No se pudo consultar la agenda.';
    }
  }

  function limpiarSeleccion() {
    elegida = null;
    formCita.hidden = true;
    sinFranja.hidden = false;
    franjas.querySelectorAll('.slot').forEach(b => b.classList.remove('elegido'));
  }

  franjas.addEventListener('click', evento => {
    const boton = evento.target.closest('button.slot');
    if (!boton || boton.disabled) return;
    franjas.querySelectorAll('.slot').forEach(b => b.classList.remove('elegido'));
    boton.classList.add('elegido');
    elegida = boton.dataset.hora;
    formCita.hidden = false;
    sinFranja.hidden = true;
    envio = uuid();
    aviso(avisoCita, '');
    aviso(avisoAgenda, `Elegiste las ${elegida} del ${fmtFecha(campoFecha.value)}. Completa tus datos.`, 'ok');
    formCita.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  });

  campoFecha.addEventListener('change', () => {
    if (campoFecha.value < hoyISO) campoFecha.value = hoyISO;
    limpiarSeleccion();
    cargar();
  });

  formCita.addEventListener('submit', async evento => {
    evento.preventDefault();
    if (!formCita.reportValidity() || !elegida) return;
    const boton = formCita.querySelector('[type=submit]');
    boton.disabled = true;
    aviso(avisoCita, 'Guardando tu cita…');
    try {
      const respuesta = await api('/api/agenda/citas', {
        metodo: 'POST',
        cuerpo: {
          fecha: campoFecha.value,
          hora: elegida,
          nombre: formCita.elements.nombre.value,
          documento: formCita.elements.documento.value,
          email: formCita.elements.email.value,
          telefono: formCita.elements.telefono.value,
          placa: formCita.elements.placa.value,
          servicio: formCita.elements.servicio.value,
          descripcion: formCita.elements.descripcion.value,
          terminos: formCita.elements.terminos.checked,
          envio_id: envio,
        },
      });
      formCita.reset();
      limpiarSeleccion();
      await cargar();
      aviso(avisoAgenda,
        `Cita registrada. Tu radicado es ${respuesta.radicado}. Consérvalo para el seguimiento.`, 'ok');
    } catch (error) {
      aviso(avisoCita, error.message, 'error');
    } finally {
      boton.disabled = false;
    }
  });

  campoFecha.value = hoyISO;
  cargar();
})();
