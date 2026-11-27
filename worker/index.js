const PAGE = `<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><title>MMD Remote Agent</title>
<style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;min-height:100vh;background:#080d16;color:#e5edf8;font:15px system-ui,-apple-system,Segoe UI,sans-serif;display:grid;place-items:center;padding:22px}.wrap{width:min(760px,100%)}header{margin-bottom:20px}h1{font-size:26px;margin:0 0 8px}.muted{color:#9aabc1;line-height:1.9}.card{background:#111c2b;border:1px solid #26364b;border-radius:18px;padding:22px;margin:14px 0}.row{display:flex;gap:12px;align-items:center;flex-wrap:wrap}.status{font-weight:700}.dot{display:inline-block;width:9px;height:9px;border-radius:50%;background:#64748b;margin-left:8px}.dot.on{background:#22c55e}.code-input{width:100%;margin:15px 0 10px;padding:16px;background:#080d16;border:1px solid #42546d;border-radius:12px;color:#e5edf8;text-align:center;direction:ltr;font:700 25px ui-monospace,monospace;letter-spacing:7px}.code{direction:ltr;text-align:center;font:700 34px ui-monospace,monospace;letter-spacing:9px;padding:18px;background:#080d16;border:1px dashed #42546d;border-radius:12px;margin:15px 0}.btn{border:0;border-radius:10px;padding:11px 17px;font-weight:700;cursor:pointer;background:#2563eb;color:white}.btn.secondary{background:#26364b}.btn.danger{background:#991b1b}.btn:disabled{opacity:.45;cursor:not-allowed}.hidden{display:none}.job{border-top:1px solid #26364b;padding:12px 0;direction:ltr;text-align:left;white-space:pre-wrap;overflow-wrap:anywhere}.hint{font-size:13px;color:#93a4ba}.pill{border-radius:99px;padding:5px 10px;background:#1e293b;color:#cbd5e1;font-size:12px}code{direction:ltr}
body{background:radial-gradient(ellipse at 80% -10%,#18365d 0,transparent 44%),#080d18;padding:28px 18px}.wrap{width:min(980px,100%)}header{display:flex;align-items:center;gap:14px;margin-bottom:24px}header:before{content:"M";width:48px;height:48px;display:grid;place-items:center;border-radius:15px;background:linear-gradient(135deg,#3978f6,#1645a5);font-weight:900;font-size:20px;box-shadow:0 10px 30px #174ca866}h1{font-size:23px}.card{background:linear-gradient(155deg,#142238,#101a29);border-color:#2b405d;box-shadow:0 14px 35px #0003}.job{background:#0a1422;border:1px solid #263a55;border-radius:13px;padding:14px;margin:12px 0}.job-command{direction:ltr;text-align:left;white-space:pre-wrap;overflow-wrap:anywhere;background:#080f1a;border:1px solid #26364b;border-radius:9px;padding:11px;font:13px/1.65 ui-monospace,Consolas,monospace;color:#dbeafe}.job-actions{display:flex;gap:9px;flex-wrap:wrap;margin-top:11px}.btn.success{background:#137653}.approval-pending{color:#f4c15d;font-weight:700}.approval-done{color:#4adea2;font-weight:700}.topline{display:flex;justify-content:space-between;align-items:center;gap:12px}.job-output{max-height:220px;overflow:auto}.btn{transition:filter .15s,transform .15s}.btn:hover{filter:brightness(1.12);transform:translateY(-1px)}</style></head><body><main class="wrap"><header><h1>MMD Remote Agent</h1><div class="muted">پنل امن مدیریت دستگاه ویندوز، وضعیت اتصال و تأیید فرمان‌های MCP.</div></header>
<section class="card"><div class="row"><span class="dot" id="dot"></span><span class="status" id="status">در حال بررسی اتصال…</span><span class="pill" id="seen">—</span></div><p class="muted" id="description">کدی را که برنامه ویندوز در ترمینال نشان می‌دهد، اینجا وارد کنید تا دستگاه به نشست شما متصل شود.</p>
<div id="pairArea"><input class="code-input" id="pairCode" inputmode="numeric" autocomplete="one-time-code" maxlength="8" placeholder="کد ۸ رقمی برنامه ویندوز" aria-label="کد اتصال"><button class="btn" id="pair">تأیید کد و اتصال دستگاه</button><p class="hint" id="expiry">ابتدا برنامه MMD Remote Agent را در ویندوز اجرا کنید.</p></div>
<div class="row"><button class="btn" id="start" disabled>شروع اتصال AI</button><button class="btn secondary" id="stop" disabled>توقف موقت</button><button class="btn danger" id="disconnect" disabled>قطع و لغو اتصال</button></div></section>
<section class="card"><h3>آخرین فرمان‌ها</h3><div class="hint">هر فرمان پیش از اجرا باید یک‌بار از سایت یا PowerShell تأیید شود.</div><div id="jobs" class="muted">هنوز فرمانی ثبت نشده است.</div></section>
<footer class="hint">اتصال خروجی HTTPS است؛ هیچ پورت ورودی یا SSH Server روی ویندوز لازم نیست.</footer></main>
<script>
const $=id=>document.getElementById(id);let state=null;
async function api(path,method='GET',body){const r=await fetch(path,{method,headers:body?{'content-type':'application/json'}:{},body:body?JSON.stringify(body):undefined,credentials:'same-origin',cache:'no-store'});const d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d.error||('HTTP '+r.status));return d}
function render(d){state=d;const online=d.device&&d.online; $('dot').className='dot'+(online?' on':'');$('status').textContent=!d.device?'اپ ویندوز متصل نیست':online?'اپ ویندوز متصل است': 'اپ ویندوز آفلاین است';$('seen').textContent=d.device?(d.state==='running'?'در حال اجرا':d.state==='stopped'?'متوقف':'متصل'):'بدون دستگاه';$('description').textContent=d.device?'شناسه دستگاه: '+d.device.id.slice(0,8)+' — وضعیت اجرا را از اینجا کنترل کنید.':'کدی را که برنامه ویندوز در ترمینال نشان می‌دهد، اینجا وارد کنید تا دستگاه به نشست شما متصل شود.';$('start').disabled=!d.device||!online||d.state==='running';$('stop').disabled=!d.device||d.state!=='running';$('disconnect').disabled=!d.device;$('pair').disabled=!!d.device&&d.state!=='stopped'}
function renderJobs(rows){$('jobs').innerHTML=rows.length?rows.map(j=>{const pending=j.status==='running'&&(j.approval_status||'pending')==='pending';return '<article class="job"><div class="topline"><b class="'+(pending?'approval-pending':'approval-done')+'">'+(pending?'در انتظار تأیید':esc(j.status))+'</b><span class="hint">'+esc(j.id)+'</span></div><pre class="job-command">'+esc(j.command)+'</pre>'+(j.output?'<pre class="job-command job-output">'+esc(j.output.slice(0,5000))+'</pre>':'')+(pending?'<div class="job-actions"><button class="btn success" data-approve="'+esc(j.id)+'">✓ تأیید و اجرا</button><button class="btn danger" data-reject="'+esc(j.id)+'">رد فرمان</button></div>':'')+'</article>'}).join(''):'هنوز فرمانی ثبت نشده است.'}
async function refresh(){try{render(await api('/api/status'));const d=await api('/api/jobs');renderJobs(d.jobs||[])}catch(e){$('status').textContent=e.message}}
$('jobs').addEventListener('click',async e=>{const b=e.target.closest('[data-approve],[data-reject]');if(!b)return;const id=b.dataset.approve||b.dataset.reject,decision=b.dataset.approve?'approve':'reject';if(!confirm(decision==='approve'?'این فرمان اجرا شود؟':'این فرمان رد شود؟'))return;b.disabled=true;try{await api('/api/'+decision,'POST',{id});await refresh()}catch(err){alert(err.message);await refresh()}});
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
$('pair').onclick=async()=>{const code=$('pairCode').value.trim();if(!/^[0-9]{8}$/.test(code)){alert('کد باید دقیقاً ۸ رقم باشد.');return}try{$('pair').disabled=true;await api('/api/pair-code','POST',{code});$('expiry').textContent='کد تأیید شد؛ در حال انتظار برای تکمیل اتصال برنامه ویندوز...';$('pairCode').disabled=true;await refresh()}catch(e){$('pair').disabled=false;alert(e.message)}};
$('start').onclick=async()=>{try{await api('/api/start','POST');await refresh()}catch(e){alert(e.message)}};
$('stop').onclick=async()=>{try{await api('/api/stop','POST');await refresh()}catch(e){alert(e.message)}};
$('disconnect').onclick=async()=>{if(!confirm('اتصال این دستگاه قطع و اعتبار آن باطل شود؟'))return;try{await api('/api/disconnect','POST');$('code').classList.add('hidden');await refresh()}catch(e){alert(e.message)}};
refresh();setInterval(refresh,3000);
</script></body></html>`;
const cors = { "content-type":"application/json; charset=utf-8", "cache-control":"no-store", "x-content-type-options":"nosniff" };
const reply = (data,status=200,extra={}) => new Response(JSON.stringify(data),{status,headers:{...cors,...extra}});
const hex = b => [...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,"0")).join("");
const random = n => {const b=new Uint8Array(n);crypto.getRandomValues(b);return hex(b)};
const hash = async s => hex(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(s)));
const parseBody = async r => {try{return await r.json()}catch{return null}};
const bearer = r => (r.headers.get("authorization")||"").replace(/^Bearer\s+/i,"");
async function browserSession(req,env,create=false){
 const raw=(req.headers.get("cookie")||"").split(";").map(x=>x.trim()).find(x=>x.startsWith("mmd_session="))?.slice(12);
 if(raw){const row=await env.DB.prepare("SELECT id FROM browser_sessions WHERE id=? AND expires_at>?").bind(await hash(raw),Math.floor(Date.now()/1000)).first();if(row)return {id:row.id,cookie:null};}
 if(!create)return null;
 const secret=random(32),id=await hash(secret),now=Math.floor(Date.now()/1000);
 await env.DB.prepare("INSERT INTO browser_sessions(id,created_at,expires_at) VALUES(?,?,?)").bind(id,now,now+60*60*24*30).run();
 return {id,cookie:"mmd_session="+secret+"; Path=/; Max-Age=2592000; Secure; HttpOnly; SameSite=Strict"};
}
async function deviceFromToken(req,env){const token=bearer(req);if(!token)return null;return await env.DB.prepare("SELECT id,session_id,state FROM devices WHERE token_hash=?").bind(await hash(token)).first();}
async function browserDevice(session,env){return await env.DB.prepare("SELECT id,state,last_seen,version FROM devices WHERE session_id=? ORDER BY paired_at DESC LIMIT 1").bind(session.id).first();}
async function mcp(req,env){
 if(bearer(req)!==env.MCP_TOKEN)return reply({jsonrpc:"2.0",error:{code:-32001,message:"Unauthorized"},id:null},401);
 const b=await parseBody(req);if(!b||b.jsonrpc!=="2.0")return reply({jsonrpc:"2.0",error:{code:-32600,message:"Invalid Request"},id:b?.id??null},400);
 if(b.method==="initialize")return reply({jsonrpc:"2.0",id:b.id,result:{protocolVersion:"2025-03-26",capabilities:{tools:{}},serverInfo:{name:"ssh-the-end-gateway",version:"2.0.0"}}});
 if(b.method==="notifications/initialized")return new Response(null,{status:202});
 if(b.method==="ping")return reply({jsonrpc:"2.0",id:b.id,result:{}});
 if(b.method==="tools/list")return reply({jsonrpc:"2.0",id:b.id,result:{tools:[
 {name:"run_command",description:"Queue a command for the paired Windows app. It must be approved exactly once, either in the website dashboard or locally in PowerShell.",inputSchema:{type:"object",properties:{command:{type:"string",minLength:1,maxLength:4000}},required:["command"]}},
 {name:"get_result",description:"Get the status and output of a command by job ID.",inputSchema:{type:"object",properties:{id:{type:"string"}},required:["id"]}}
 ]}});
 if(b.method==="tools/call"){const name=b.params?.name,args=b.params?.arguments||{};
 if(name==="run_command"){if(typeof args.command!=="string"||!args.command.trim()||args.command.length>4000)return reply({jsonrpc:"2.0",id:b.id,result:{isError:true,content:[{type:"text",text:"Invalid command"}]}});const dev=await env.DB.prepare("SELECT id,state,session_id FROM devices ORDER BY paired_at DESC LIMIT 1").first();const now=Math.floor(Date.now()/1000);const legacy=await env.DB.prepare("SELECT last_seen FROM agent_state WHERE id=1").first();const legacyOnline=!!legacy&&now-legacy.last_seen<45;if(dev?dev.state!=="running":!legacyOnline)return reply({jsonrpc:"2.0",id:b.id,result:{isError:true,content:[{type:"text",text:"Windows agent is offline. Start MMD-Remote-Agent on Windows and ensure its gateway token is configured."}]}});const id=random(16);if(dev&&dev.state==="running"){await env.DB.prepare("INSERT INTO jobs(id,command,status,created_at,updated_at,owner_session_id) VALUES(?,?,'queued',?,?,?)").bind(id,args.command,now,now,dev.session_id).run();}else{await env.DB.prepare("INSERT INTO jobs(id,command,status,created_at,updated_at) VALUES(?,?,'queued',?,?)").bind(id,args.command,now,now).run();}return reply({jsonrpc:"2.0",id:b.id,result:{content:[{type:"text",text:JSON.stringify({job_id:id,status:"queued",approval_required:true,approval_options:["website","local"]})}]}});}
 if(name==="get_result"){if(typeof args.id!=="string")return reply({jsonrpc:"2.0",id:b.id,result:{isError:true,content:[{type:"text",text:"Missing job id"}]}});const row=await env.DB.prepare("SELECT id,status,output,exit_code,created_at,updated_at FROM jobs WHERE id=?").bind(args.id).first();return reply({jsonrpc:"2.0",id:b.id,result:{content:[{type:"text",text:row?JSON.stringify(row):"Job not found"}]}});}
 return reply({jsonrpc:"2.0",id:b.id,result:{isError:true,content:[{type:"text",text:"Unknown tool"}]}});}
 return reply({jsonrpc:"2.0",id:b.id,error:{code:-32601,message:"Method not found"}});
}
export default {async fetch(request,env){
 const u=new URL(request.url),p=u.pathname,now=Math.floor(Date.now()/1000);
 if(p==="/health"){const d=await env.DB.prepare("SELECT id,state,last_seen FROM devices ORDER BY paired_at DESC LIMIT 1").first();return reply({ok:true,service:"ssh-gateway",agent:d&&now-d.last_seen<45?"online":"offline",mcp:true,pairing:true});}
 if(p==="/mcp"&&request.method==="POST")return mcp(request,env);
 if(p==="/agent/pair/init"&&request.method==="POST"){
 const b=await parseBody(request);
 if(!b||typeof b.code!=="string"||!/^[0-9]{8}$/.test(b.code)||typeof b.secret!=="string"||b.secret.length<32||b.secret.length>128)return reply({error:"invalid pairing request"},400);
 await env.DB.prepare("DELETE FROM agent_pair_requests WHERE expires_at<=? OR used_at IS NOT NULL").bind(now).run();
 try{await env.DB.prepare("INSERT INTO agent_pair_requests(code_hash,secret_hash,session_id,created_at,expires_at,used_at) VALUES(?,?,NULL,?,?,NULL)").bind(await hash(b.code),await hash(b.secret),now,now+180).run();}
 catch{return reply({error:"pairing code collision; restart the app to generate another code"},409);}
 return reply({ok:true,expires_in:180});
 }
 if(p==="/agent/pair/complete"&&request.method==="POST"){
 const b=await parseBody(request);
 if(!b||typeof b.code!=="string"||!/^[0-9]{8}$/.test(b.code)||typeof b.secret!=="string")return reply({error:"invalid pairing request"},400);
 const codeHash=await hash(b.code),secretHash=await hash(b.secret);
 const pending=await env.DB.prepare("SELECT session_id FROM agent_pair_requests WHERE code_hash=? AND secret_hash=? AND used_at IS NULL AND expires_at>?").bind(codeHash,secretHash,now).first();
 if(!pending)return reply({error:"pairing request expired or invalid"},410);
 if(!pending.session_id)return reply({paired:false,waiting_for_website:true},202);
 const claimed=await env.DB.prepare("UPDATE agent_pair_requests SET used_at=? WHERE code_hash=? AND secret_hash=? AND session_id=? AND used_at IS NULL AND expires_at>? RETURNING session_id").bind(now,codeHash,secretHash,pending.session_id,now).first();
 if(!claimed)return reply({error:"pairing request already completed"},409);
 const id=random(12),token=random(32);
 await env.DB.prepare("INSERT INTO devices(id,session_id,token_hash,state,paired_at,last_seen,version) VALUES(?,?,?,'running',?,?,?)").bind(id,claimed.session_id,await hash(token),now,now,"2.1.0").run();
 return reply({device_id:id,device_token:token,paired:true});
 }
 if(p==="/agent/pair"&&request.method==="POST"){const b=await parseBody(request);if(!b||typeof b.code!=="string"||!/^\d{8}$/.test(b.code))return reply({error:"invalid pairing code"},400);const codeHash=await hash(b.code),pair=await env.DB.prepare("UPDATE pair_codes SET used_at=? WHERE code_hash=? AND used_at IS NULL AND expires_at>? RETURNING session_id").bind(now,codeHash,now).first();if(!pair)return reply({error:"pairing code expired or already used"},401);const id=random(12),token=random(32);await env.DB.prepare("INSERT INTO devices(id,session_id,token_hash,state,paired_at,last_seen,version) VALUES(?,?,?,'running',?,?,?)").bind(id,pair.session_id,await hash(token),now,now,"2.0.0").run();return reply({device_id:id,device_token:token,paired:true});}
 if(p==="/agent/unpair"&&request.method==="POST"){const d=await deviceFromToken(request,env);if(!d)return reply({error:"unauthorized"},401);await env.DB.prepare("UPDATE devices SET state='stopped' WHERE id=?").bind(d.id).run();return reply({ok:true,unpaired:true});}
 if(p==="/agent/poll"&&request.method==="POST"){const d=await deviceFromToken(request,env);if(d){await env.DB.prepare("UPDATE devices SET last_seen=?,version='2.0.0' WHERE id=?").bind(now,d.id).run();if(d.state!=="running")return reply({job:null,state:d.state});const job=await env.DB.prepare("SELECT id,command,approval_status FROM jobs WHERE status='queued' AND owner_session_id=? ORDER BY created_at LIMIT 1").bind(d.session_id).first();if(!job)return reply({job:null,state:"running"});const changed=await env.DB.prepare("UPDATE jobs SET status='running',updated_at=? WHERE id=? AND status='queued' RETURNING id").bind(now,job.id).first();return reply({job:changed?job:null,state:"running"});}
 if(bearer(request)===env.AGENT_TOKEN){await env.DB.prepare("UPDATE agent_state SET last_seen=?,version=? WHERE id=1").bind(now,"legacy-agent").run();const job=await env.DB.prepare("SELECT id,command FROM jobs WHERE status='queued' AND owner_session_id IS NULL ORDER BY created_at LIMIT 1").first();if(!job)return reply({job:null});await env.DB.prepare("UPDATE jobs SET status='running',updated_at=? WHERE id=? AND status='queued'").bind(now,job.id).run();return reply({job});}return reply({error:"unauthorized"},401);}
 if(p==="/agent/approval"&&request.method==="POST"){
 const d=await deviceFromToken(request,env);if(!d||d.state!=="running")return reply({error:"unauthorized"},401);
 const b=await parseBody(request);
 if(!b||typeof b.id!=="string"||!["approve","reject"].includes(b.decision))return reply({error:"bad approval request"},400);
 const row=await env.DB.prepare("SELECT approval_status FROM jobs WHERE id=? AND owner_session_id=? AND status='running'").bind(b.id,d.session_id).first();
 if(!row)return reply({error:"job not found"},404);
 const wanted=b.decision==="approve"?"approved":"rejected";
 if(row.approval_status==="pending")await env.DB.prepare("UPDATE jobs SET approval_status=?,approval_source='local',updated_at=? WHERE id=? AND owner_session_id=? AND approval_status='pending'").bind(wanted,now,b.id,d.session_id).run();
 const final=await env.DB.prepare("SELECT approval_status,approval_source FROM jobs WHERE id=? AND owner_session_id=?").bind(b.id,d.session_id).first();
 return reply({ok:true,approval_status:final.approval_status,approval_source:final.approval_source});
 }
 if(p==="/agent/result"&&request.method==="POST"){const d=await deviceFromToken(request,env),legacy=!d&&bearer(request)===env.AGENT_TOKEN;if(!d&&!legacy)return reply({error:"unauthorized"},401);const b=await parseBody(request);if(!b||typeof b.id!=="string"||typeof b.output!=="string")return reply({error:"bad request"},400);
 if(d){if(d.state!=="running")return reply({error:"device is unpaired"},401);const row=await env.DB.prepare("SELECT approval_status FROM jobs WHERE id=? AND owner_session_id=? AND status='running'").bind(b.id,d.session_id).first();if(!row)return reply({error:"job not found"},404);if(!["approved","rejected"].includes(row.approval_status))return reply({error:"command has not been approved"},403);if(row.approval_status==="rejected"&&b.exit_code!==125)return reply({error:"rejected command cannot report execution"},403);}
 await env.DB.prepare("UPDATE jobs SET status=?,output=?,exit_code=?,updated_at=? WHERE id=?").bind(b.exit_code===125?"rejected":"completed",b.output.slice(0,30000),Number.isInteger(b.exit_code)?b.exit_code:-1,now,b.id).run();return reply({ok:true});}
 if(p==="/"){const s=await browserSession(request,env,true);return new Response(PAGE,{headers:{"content-type":"text/html; charset=utf-8","cache-control":"no-store","content-security-policy":"default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'","referrer-policy":"no-referrer","x-content-type-options":"nosniff",...(s.cookie?{"set-cookie":s.cookie}:{})}});}
 if(p.startsWith("/api/")){const s=await browserSession(request,env,false);if(!s)return reply({error:"session expired; reload the page"},401);
 if(p==="/api/status"&&request.method==="GET"){const d=await browserDevice(s,env);return reply({device:d?{id:d.id}:null,state:d?.state||"stopped",online:!!d&&now-d.last_seen<45,last_seen:d?.last_seen||0});}
 if(p==="/api/pair-code"&&request.method==="POST"){
 const old=await browserDevice(s,env);if(old&&old.state!=="stopped")return reply({error:"a device is already paired"},409);
 const b=await parseBody(request);if(!b||typeof b.code!=="string"||!/^[0-9]{8}$/.test(b.code))return reply({error:"کد باید دقیقاً ۸ رقم باشد."},400);
 const ip=request.headers.get("cf-connecting-ip")||"unknown",ipHash=await hash(ip+env.MCP_TOKEN);
 const attempt=await env.DB.prepare("SELECT window_started_at,attempts FROM agent_pair_attempts WHERE ip_hash=?").bind(ipHash).first();
 if(attempt&&now-attempt.window_started_at<60&&attempt.attempts>=10)return reply({error:"تعداد تلاش‌ها زیاد است؛ یک دقیقه دیگر دوباره امتحان کنید."},429);
 if(attempt&&now-attempt.window_started_at<60)await env.DB.prepare("UPDATE agent_pair_attempts SET attempts=attempts+1 WHERE ip_hash=?").bind(ipHash).run();
 else await env.DB.prepare("INSERT INTO agent_pair_attempts(ip_hash,window_started_at,attempts) VALUES(?,?,1) ON CONFLICT(ip_hash) DO UPDATE SET window_started_at=excluded.window_started_at,attempts=1").bind(ipHash,now).run();
 const codeHash=await hash(b.code);
const prior=await env.DB.prepare("SELECT session_id FROM agent_pair_requests WHERE code_hash=? AND used_at IS NULL AND expires_at>?").bind(codeHash,now).first();
if(prior?.session_id===s.id)return reply({ok:true,message:"این کد قبلاً برای همین نشست تأیید شده است."});
if(prior?.session_id)return reply({error:"این کد قبلاً در نشست دیگری استفاده شده است."},409);
const paired=await env.DB.prepare("UPDATE agent_pair_requests SET session_id=? WHERE code_hash=? AND session_id IS NULL AND used_at IS NULL AND expires_at>? RETURNING code_hash").bind(s.id,codeHash,now).first();
 if(!paired)return reply({error:"کد نامعتبر است یا منقضی شده است."},401);
 return reply({ok:true,message:"کد تأیید شد؛ برنامه ویندوز اتصال را تکمیل می‌کند."});
 }
 if(p==="/api/jobs"&&request.method==="GET"){const rows=await env.DB.prepare("SELECT id,command,status,output,exit_code,created_at,approval_status,approval_source FROM jobs WHERE owner_session_id=? ORDER BY created_at DESC LIMIT 12").bind(s.id).all();return reply({jobs:rows.results||[]});}
 if((p==="/api/approve"||p==="/api/reject")&&request.method==="POST"){
 const b=await parseBody(request);if(!b||typeof b.id!=="string"||b.id.length>64)return reply({error:"شناسه فرمان نامعتبر است."},400);
 const decision=p==="/api/approve"?"approved":"rejected";
 const changed=await env.DB.prepare("UPDATE jobs SET approval_status=?,approval_source='website',updated_at=? WHERE id=? AND owner_session_id=? AND status='running' AND approval_status='pending'").bind(decision,now,b.id,s.id).run();
 if(!changed.meta?.changes){const row=await env.DB.prepare("SELECT approval_status FROM jobs WHERE id=? AND owner_session_id=?").bind(b.id,s.id).first();if(!row)return reply({error:"فرمان پیدا نشد."},404);return reply({error:"این فرمان قبلاً تعیین تکلیف شده است.",approval_status:row.approval_status},409);}
 return reply({ok:true,approval_status:decision});
 }
 if(p==="/api/start"&&request.method==="POST"){const d=await browserDevice(s,env);if(!d)return reply({error:"no paired device"},404);await env.DB.prepare("UPDATE devices SET state='running' WHERE id=?").bind(d.id).run();return reply({ok:true,state:"running"});}
 if(p==="/api/stop"&&request.method==="POST"){const d=await browserDevice(s,env);if(!d)return reply({error:"no paired device"},404);await env.DB.prepare("UPDATE devices SET state='stopped' WHERE id=?").bind(d.id).run();return reply({ok:true,state:"stopped"});}
 if(p==="/api/disconnect"&&request.method==="POST"){const d=await browserDevice(s,env);if(!d)return reply({ok:true});await env.DB.prepare("DELETE FROM jobs WHERE owner_session_id=? AND status='queued'").bind(s.id).run();await env.DB.prepare("DELETE FROM devices WHERE id=?").bind(d.id).run();return reply({ok:true});}
 return reply({error:"not found"},404);}
 return reply({error:"not found"},404);
}};