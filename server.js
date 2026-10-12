const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { randomUUID } = require('node:crypto');
const VERSION = 'V 0.1.0';
const PORT = Number(process.env.PORT || 8765);
const root = __dirname;
const dataDir = path.join(root, 'data');
fs.mkdirSync(dataDir, { recursive: true });
const file = path.join(dataDir, 'state.json');
const initial = {
  version: VERSION,
  preferences: {roles: ['Credit risk','Market risk','Investment banking','AI/software','Fintech'], employerCategory: 'Global Capability Centres included', seniority: 'Mid-level to AVP', locations: 'All India metros, Bengaluru, Pune', arrangements: 'Remote, hybrid, on-site', minimumCTCLPA:25, allowUnknownSalary:true, noticeMonths:2, workAuthorization:'NA — clarify when required', gmail:'tapomoy400@gmail.com', checkMinutes:240, reportDays:7, automaticSubmission:true, tailorVerifiedFacts:true},
  jobs:[], events:[], lastCheck:null,
  integrations: {Gemini:'Deferred', Gmail:'Not connected', HiringCafe:'Not connected', 'Welcome to the Jungle':'Not connected', Himalayas:'Not connected', 'Work at a Startup':'Not connected', Glassdoor:'Not connected', LinkedIn:'Manual application route', ZipRecruiter:'Not connected'}
};
let state = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file,'utf8')) : initial;
state.version = VERSION;
function save(){const tmp=file+'.tmp';fs.writeFileSync(tmp,JSON.stringify(state,null,2));fs.renameSync(tmp,file);}
save();
function metrics(jobs){
 const submitted=jobs.filter(j=>j.submittedAt);
 const responses=submitted.filter(j=>['Recruiter response','Interview','Offer'].includes(j.status));
 return {submitted:submitted.length,responses:responses.length,interviews:submitted.filter(j=>['Interview','Offer'].includes(j.status)).length,responseRate:submitted.length?Math.round(responses.length/submitted.length*100):null};
}
function eligibility(job,p){
 if(job.ctcLPA!==null && job.ctcLPA<p.minimumCTCLPA)return 'Below salary minimum';
 if(job.ctcLPA===null && !p.allowUnknownSalary)return 'Salary unknown';
 return 'Needs role, location and application-route verification';
}
async function body(req){let raw='';for await(const part of req){raw+=part;if(raw.length>100000)throw Error('Request too large');}return JSON.parse(raw||'{}');}
function send(res,status,data){res.writeHead(status,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end(JSON.stringify(data));}
function check(){state.lastCheck=new Date().toISOString();state.events.unshift({at:state.lastCheck,message:'Local review completed. Portal discovery is not connected; no applications were submitted.'});state.events=state.events.slice(0,100);save();}
const server=http.createServer(async(req,res)=>{
 try {
  if(req.headers.host!==`127.0.0.1:${PORT}` && req.headers.host!==`localhost:${PORT}`)return send(res,403,{error:'Invalid host'});
  if(req.method==='POST' && req.headers.origin!==`http://127.0.0.1:${PORT}` && req.headers.origin!==`http://localhost:${PORT}`)return send(res,403,{error:'Invalid origin'});
  if(req.method==='GET' && req.url==='/'){res.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Content-Security-Policy':"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'"});return res.end(fs.readFileSync(path.join(root,'index.html')));}
  if(req.method==='GET' && req.url==='/api/state')return send(res,200,{...state,metrics:metrics(state.jobs)});
  if(req.method==='GET' && req.url==='/api/report'){const since=Date.now()-state.preferences.reportDays*86400000;const jobs=state.jobs.filter(j=>j.submittedAt && Date.parse(j.submittedAt)>=since);return send(res,200,{version:VERSION,generatedAt:new Date().toISOString(),periodDays:state.preferences.reportDays,metrics:metrics(jobs),jobs,note:'Rates use applications submitted in this period and their currently recorded outcomes. Calls require manual logging.'});}
  if(req.method==='POST' && req.url==='/api/preferences'){const b=await body(req);for(const [k,min,max] of [['checkMinutes',5,10080],['reportDays',1,365]]){if(!Number.isInteger(b[k])||b[k]<min||b[k]>max)throw Error('Invalid '+k);}state.preferences.checkMinutes=b.checkMinutes;state.preferences.reportDays=b.reportDays;save();return send(res,200,{ok:true});}
  if(req.method==='POST' && req.url==='/api/check'){check();return send(res,200,{ok:true});}
  if(req.method==='POST' && req.url==='/api/jobs'){const b=await body(req);if(!b.company?.trim()||!b.title?.trim())throw Error('Company and title required');const url=new URL(b.url);if(!['https:','http:'].includes(url.protocol))throw Error('Invalid URL');if(state.jobs.some(j=>j.url===url.href))throw Error('This job URL is already tracked');const ctc=b.ctcLPA===''||b.ctcLPA==null?null:Number(b.ctcLPA);if(ctc!==null&&(!Number.isFinite(ctc)||ctc<0))throw Error('Invalid salary');const j={id:randomUUID(),company:b.company.trim(),title:b.title.trim(),url:url.href,ctcLPA:ctc,status:'Queued',createdAt:new Date().toISOString(),submittedAt:null,cvVersion:'',history:[]};j.eligibility=eligibility(j,state.preferences);state.jobs.unshift(j);save();return send(res,200,{ok:true});}
  if(req.method==='POST' && req.url==='/api/outcome'){const b=await body(req);const j=state.jobs.find(j=>j.id===b.id);if(!j)throw Error('Job not found');if(!['Queued','Submitted','Recruiter response','Interview','Rejected','Offer'].includes(b.status))throw Error('Invalid status');if(b.status!=='Queued'&&!j.submittedAt){if(!b.confirmSubmitted)throw Error('Confirm that an application was actually submitted');j.submittedAt=new Date().toISOString();}j.status=b.status;j.cvVersion=String(b.cvVersion||j.cvVersion).slice(0,200);j.history.push({at:new Date().toISOString(),status:b.status,note:String(b.note||'').slice(0,2000)});save();return send(res,200,{ok:true});}
  send(res,404,{error:'Not found'});
 }catch(e){send(res,400,{error:e.message});}
});
if(require.main===module){server.listen(PORT,'127.0.0.1',()=>console.log(`${VERSION} — http://127.0.0.1:${PORT}`));setInterval(()=>{if(!state.lastCheck||Date.now()-Date.parse(state.lastCheck)>=state.preferences.checkMinutes*60000)check();},60000);}
module.exports={metrics,eligibility,server};
