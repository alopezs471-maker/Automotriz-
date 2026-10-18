/* Integración nueva: no cambia los estilos originales. */
(() => {
  const help='Abre el sitio desde http://localhost:8000 después de ejecutar python servidor.py. Live Server no guarda en la base de datos.';
  async function api(path, options) {
    const response=await fetch(path,options);
    const type=response.headers.get('content-type')||'';
    if(!type.includes('application/json')) throw new Error(help);
    const data=await response.json();
    if(!response.ok) throw new Error(data.error||'No fue posible completar la operación.');
    return data;
  }
  // Los campos de fecha arrancan hoy y no aceptan días pasados.
  const hoyISO=new Date().toLocaleDateString('sv');
  for(const campo of document.querySelectorAll('input[type=date]')){
    if(!campo.value)campo.value=hoyISO;
    campo.min=hoyISO;
  }
  const form=document.querySelector('.pqrs-form');
  if(form){
    const message=document.createElement('p');
    message.setAttribute('role','status');message.style.cssText='font-size:14px;line-height:1.5;margin-top:16px;white-space:normal';form.append(message);
    for(const [name,max] of Object.entries({nombre:150,documento:30,email:190,telefono:30,descripcion:10000}))form.elements[name].maxLength=max;
    let envio=null;
    form.addEventListener('submit',async event=>{
      event.preventDefault();
      if(!form.reportValidity())return;
      const button=form.querySelector('[type=submit]');button.disabled=true;message.textContent='Guardando solicitud…';
      try{
        if(!envio)envio=crypto.randomUUID();
        const values=Object.fromEntries(new FormData(form));
        values.terminos=form.elements.terminos.checked;values.envio_id=envio;
        const session=await api('/api/sesion');
        const result=await api('/api/pqrs',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':session.token},body:JSON.stringify(values)});
        message.style.color='#16734b';message.textContent='Solicitud guardada. Tu radicado es '+result.radicado+'. Consérvalo para el seguimiento.';
        form.reset();envio=null;
      }catch(error){message.style.color='#af3030';message.textContent=error.message==='Failed to fetch'?help:error.message;}
      finally{button.disabled=false;}
    });
  }
  const section=document.querySelector('#datos-promociones');
  if(section){
    const body=section.querySelector('tbody'), search=section.querySelector('input'), select=section.querySelector('select'), status=section.querySelector('[role=status]');
    const money=n=>new Intl.NumberFormat('es-CO',{style:'currency',currency:'COP',maximumFractionDigits:0}).format(n);
    let rows=[];
    function draw(){
      body.replaceChildren();
      const filtered=rows.filter(r=>(!select.value||r.categoria===select.value)&&(r.nombre+' '+r.beneficio).toLowerCase().includes(search.value.toLowerCase()));
      for(const r of filtered){
        const tr=document.createElement('tr');
        const discount=r.precio_base?((r.precio_base-r.precio_promocional)*100/r.precio_base).toFixed(1)+' %':'—';
        for(const value of [r.nombre,r.categoria,money(r.precio_base),money(r.precio_promocional),discount,r.existencias===null?'Por confirmar':r.existencias,r.beneficio,r.estado]){
          const td=document.createElement('td');td.textContent=value;tr.append(td);
        }body.append(tr);
      }
      status.textContent=filtered.length+' promociones · Datos leídos de SQLite. Última consulta: '+new Date().toLocaleTimeString('es-CO');
    }
    async function load(){
      status.textContent='Consultando base de datos…';
      try{
        rows=(await api('/api/promociones')).promociones;
        const previous=select.value;select.replaceChildren(new Option('Todas las categorías',''));
        for(const category of new Set(rows.map(r=>r.categoria)))select.add(new Option(category,category));
        select.value=previous;draw();
        // Mantiene las tarjetas existentes y sincroniza sus precios con SQLite.
        for(const card of document.querySelectorAll('.product-card')){
          const r=rows.find(x=>x.sku===card.dataset.id);if(!r)continue;
          card.dataset.price=r.precio_promocional;
          const price=card.querySelector('.product-price'),old=card.querySelector('.old-price'),benefit=card.querySelector('.benefit-subtext');
          if(price)price.textContent=money(r.precio_promocional);
          if(old)old.textContent=money(r.precio_base);
          if(benefit)benefit.textContent=r.beneficio;
        }
      }catch(error){status.textContent='No se pudo consultar la base. '+help;}
    }
    search.addEventListener('input',draw);select.addEventListener('change',draw);
    section.querySelector('button').addEventListener('click',load);load();
  }

  /* ------------------------------------------------------------------
     Formularios genéricos: cualquier <form data-endpoint="..."> se envía
     a /api/<endpoint> con el mismo patrón de PQRS (token + envio_id).
     ------------------------------------------------------------------ */
  const etiquetas = {
    'citas-taller': 'Cita registrada. Tu radicado es ',
    'pruebas-manejo': 'Prueba de manejo agendada. Tu radicado es ',
    'pedidos': 'Pedido registrado. Tu radicado es ',
    'contacto': 'Mensaje enviado. Te responderemos pronto.',
    'seguros': 'Cotización solicitada. Un asesor te contactará.'
  };

  function destino(form){
    const propio = form.querySelector('[role=status]') || form.parentElement.querySelector('#formMessage, .form-message');
    if(propio) return propio;
    const creado=document.createElement('p');
    creado.setAttribute('role','status');
    creado.style.cssText='font-size:14px;line-height:1.5;margin-top:14px;white-space:normal';
    form.append(creado);
    return creado;
  }

  function itemsCarrito(){
    try{
      const carrito=JSON.parse(localStorage.getItem('premium_cart'))||[];
      return carrito.filter(i=>i && i.id).map(i=>({sku:String(i.id),cantidad:Math.max(1,parseInt(i.quantity||1,10))}));
    }catch(_){return [];}
  }

  function vaciarCarrito(){
    localStorage.removeItem('premium_cart');
    // j6.js se refresca escuchando el evento 'storage', pero ese evento solo
    // salta entre pestañas: se lo disparamos a mano para que actualice la UI.
    window.dispatchEvent(new StorageEvent('storage',{key:'premium_cart',newValue:null}));
    const badge=document.getElementById('cart-count-badge')||document.getElementById('index-cart-count');
    if(badge)badge.textContent='0';
  }

  for(const f of document.querySelectorAll('form[data-endpoint]')){
    const endpoint=f.dataset.endpoint, salida=destino(f);
    let envio=null;
    f.addEventListener('submit',async event=>{
      event.preventDefault();
      if(!f.reportValidity())return;
      const button=f.querySelector('[type=submit]');
      if(button)button.disabled=true;
      salida.style.color='';salida.textContent='Enviando…';
      try{
        if(!envio)envio=crypto.randomUUID();
        const values=Object.fromEntries(new FormData(f));
        values.terminos=f.elements.terminos?f.elements.terminos.checked:true;
        values.envio_id=envio;
        if(endpoint==='pedidos'){
          const items=itemsCarrito();
          if(!items.length)throw new Error('Tu carrito está vacío.');
          values.items=items;
        }
        const session=await api('/api/sesion');
        const result=await api('/api/'+endpoint,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':session.token},body:JSON.stringify(values)});
        salida.style.color='#16734b';
        salida.textContent=result.radicado
          ? (etiquetas[endpoint]||'Solicitud registrada. Radicado ')+result.radicado+'. Consérvalo para el seguimiento.'
          : (f.dataset.mensaje||etiquetas[endpoint]||'Solicitud registrada.');
        f.reset();envio=null;
        if(endpoint==='pedidos')vaciarCarrito();
      }catch(error){
        salida.style.color='#af3030';
        salida.textContent=error.message==='Failed to fetch'?help:error.message;
      }finally{if(button)button.disabled=false;}
    });
  }

  /* Checkout: el botón "Proceder al Pago" del carrito (j6.js) no hacía nada.
     Se despliega un formulario y el pedido queda guardado en SQLite. */
  const checkout=document.getElementById('checkout-btn');
  if(checkout){
    const contenedor=document.createElement('div');
    contenedor.id='checkout-dasauto';
    contenedor.style.cssText='padding:0 24px 20px';
    const estado=document.createElement('p');
    estado.setAttribute('role','status');
    estado.style.cssText='font-size:13px;line-height:1.5;margin:8px 0 0';
    const formulario=document.createElement('form');
    formulario.dataset.endpoint='pedidos';
    formulario.style.cssText='display:none;flex-direction:column;gap:10px;margin-top:12px';
    const campo=(nombre,tipo,placeholder,requerido)=>`<input type="${tipo}" name="${nombre}" placeholder="${placeholder}" ${requerido?'required':''} style="width:100%;padding:11px;border:1px solid #d0d0d0;border-radius:4px;font:inherit">`;
    formulario.innerHTML=`
      ${campo('nombre','text','Nombre completo',true)}
      ${campo('documento','text','Documento',true)}
      ${campo('email','email','Correo electrónico',true)}
      ${campo('telefono','tel','Teléfono',true)}
      <label style="font-size:12px;line-height:1.4;display:flex;gap:8px;align-items:flex-start;color:#5c5e62">
        <input type="checkbox" name="terminos" required style="margin-top:2px">
        Autorizo el tratamiento de mis datos personales (Ley 1581 de 2012).
      </label>
      <button type="submit" style="padding:13px;background:#171a20;color:#fff;border:none;border-radius:4px;cursor:pointer;font-weight:500">Confirmar pedido</button>`;
    contenedor.append(formulario,estado);
    checkout.parentElement.append(contenedor);
    checkout.addEventListener('click',()=>{
      const items=itemsCarrito();
      if(!items.length){estado.style.color='#af3030';estado.textContent='Tu carrito está vacío.';return;}
      estado.style.color='';
      estado.textContent=items.length+' vehículo(s) en el carrito. Completa tus datos para confirmar.';
      formulario.style.display='flex';
      formulario.scrollIntoView({block:'nearest'});
    });
  }
})();
