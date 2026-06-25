async function postJSON(url, body){
  const res = await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify(body)});
  const data = await res.json();
  if(!res.ok) throw new Error(data.error || 'Request failed');
  return data;
}
function values(form){ return Object.fromEntries(new FormData(form).entries()); }
const loginForm=document.getElementById('loginForm');
if(loginForm){ loginForm.addEventListener('submit',async e=>{e.preventDefault(); const msg=document.getElementById('msg'); msg.textContent='Checking...'; try{ await postJSON('/api/login',values(loginForm)); location.href='/dashboard.html'; }catch(err){ msg.textContent=err.message; msg.style.color='#d84646'; }}); }
const registerForm=document.getElementById('registerForm');
if(registerForm){ registerForm.addEventListener('submit',async e=>{e.preventDefault(); const msg=document.getElementById('msg'); msg.textContent='Creating account...'; try{ await postJSON('/api/register',values(registerForm)); location.href='/dashboard.html'; }catch(err){ msg.textContent=err.message; msg.style.color='#d84646'; }}); }
