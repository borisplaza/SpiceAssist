let sessionId = localStorage.getItem('spiceassist_session') || crypto.randomUUID();
localStorage.setItem('spiceassist_session', sessionId);
const messages = document.getElementById('messages');
function add(text, who, meta=''){
  const d=document.createElement('div'); d.className=`bubble ${who}`;
  d.innerHTML=`<div>${text.replace(/</g,'&lt;')}</div>${meta?`<div class="meta">${meta}</div>`:''}`;
  messages.appendChild(d); messages.scrollTop=messages.scrollHeight;
}
add('Hola. Soy SpiceAssist. Puedo orientarte sobre productos, cotizaciones, documentos, entregas, órdenes e incidencias. Cuando una respuesta requiere precio, fecha o decisión sensible, la dejo para revisión humana.','assistant');
async function sendMessage(text){
  add(text,'user');
  const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,session_id:sessionId})});
  const j=await r.json();
  if(!r.ok){add(j.error||'Ocurrió un error','assistant');return;}
  sessionId=j.session_id; localStorage.setItem('spiceassist_session', sessionId);
  const meta=`Intención: ${j.intent} | Confianza: ${j.confidence}${j.request_id?` | Solicitud #${j.request_id}`:''}`;
  add(j.reply,'assistant',meta);
}
document.getElementById('chatForm').addEventListener('submit',e=>{e.preventDefault();const i=document.getElementById('msg');const t=i.value.trim();if(t){i.value='';sendMessage(t)}});
document.querySelectorAll('.chips button').forEach(b=>b.addEventListener('click',()=>sendMessage(b.dataset.q)));
document.getElementById('contactForm').addEventListener('submit',async e=>{
e.preventDefault();
  const payload={
  session_id: sessionId,
  name: document.getElementById('name').value,
  email: document.getElementById('email').value,
  phone: document.getElementById('phone').value,
  company: document.getElementById('company').value
};
 const r=await fetch('/api/contact',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}); const j=await r.json();
 contactStatus.textContent=r.ok?`Contacto guardado con ID ${j.contact_id}.`:j.error;
});
