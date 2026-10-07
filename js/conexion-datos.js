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
})();
