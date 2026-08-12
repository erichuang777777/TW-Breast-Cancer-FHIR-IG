from __future__ import annotations
import json,os
from pathlib import Path
from fastapi import FastAPI,HTTPException
from fastapi.responses import HTMLResponse,FileResponse
from pydantic import BaseModel
from .exporter import export_case
from .fhir import build_bundle
from .importers import import_batch
from .models import Method,ReviewStatus
from .rules import validate
from .validation import validate_case
from .store import JsonStore

ROOT=Path(os.getenv("QBC_WORKDIR",Path.cwd()))
STORE=JsonStore(ROOT/"runtime"/"batches"); EXPORTS=ROOT/"runtime"/"exports"
app=FastAPI(title="QBC Review Workbench",version="0.1.0-alpha.1")

class ImportRequest(BaseModel): source:str; batch_id:str; case_ids:list[str]|None=None
class ReviewRequest(BaseModel): reviewer:str; value:str|None=None; action:str="approve"
class ExportRequest(BaseModel): filename:str
class AiRequest(BaseModel):
    tag:str; task:str; text:str; source_file:str="uploaded-text"; model:str|None=None

@app.get("/",response_class=HTMLResponse)
def home(): return HTML
@app.get("/api/batches")
def batches(): return STORE.list()
@app.post("/api/import")
def do_import(req:ImportRequest):
    batch=import_batch(Path(req.source),req.batch_id,req.case_ids); STORE.save(batch); return {"batch_id":batch.batch_id,"cases":list(batch.cases)}
@app.get("/api/batches/{batch_id}")
def batch(batch_id:str): return STORE.load(batch_id).model_dump(mode="json")
@app.get("/api/batches/{batch_id}/cases/{case_id}")
def case(batch_id:str,case_id:str):
    b=STORE.load(batch_id)
    if case_id not in b.cases: raise HTTPException(404,"case not found")
    validate(b.cases[case_id]); STORE.save(b); return b.cases[case_id].model_dump(mode="json")
@app.post("/api/batches/{batch_id}/cases/{case_id}/fields/{tag}")
def review(batch_id:str,case_id:str,tag:str,req:ReviewRequest):
    b=STORE.load(batch_id); c=b.cases[case_id]; field=c.candidates.get(tag)
    if not field: raise HTTPException(404,"field not found")
    if req.action=="approve": field.approve(req.reviewer,req.value)
    elif req.action=="reject": field.status=ReviewStatus.REJECTED; field.reviewed_by=req.reviewer
    else: raise HTTPException(400,"unsupported action")
    validate(c); STORE.save(b); return field.model_dump(mode="json")
@app.post("/api/batches/{batch_id}/cases/{case_id}/manual/{tag}")
def manual(batch_id:str,case_id:str,tag:str,req:ReviewRequest):
    from .models import Candidate
    b=STORE.load(batch_id); c=b.cases[case_id]
    c.candidates[tag]=Candidate(qbc_tag=tag,value=req.value,method=Method.MANUAL,status=ReviewStatus.APPROVED,reviewed_by=req.reviewer)
    validate(c); STORE.save(b); return c.candidates[tag].model_dump(mode="json")
@app.post("/api/batches/{batch_id}/cases/{case_id}/ai-extract")
def ai_extract(batch_id:str,case_id:str,req:AiRequest):
    from .llm import OllamaClient
    from .models import Candidate,Evidence
    schema={"type":"object","properties":{"value":{"type":["string","null"]},"display":{"type":["string","null"]},"evidence":{"type":"string"},"confidence":{"type":"number","minimum":0,"maximum":1}},"required":["value","evidence","confidence"]}
    client=OllamaClient(model=req.model or os.getenv("QBC_OLLAMA_MODEL","qwen3.5:cloud"))
    try: result=client.extract(req.task,req.text,schema)
    except Exception as e: raise HTTPException(502,f"Ollama extraction failed: {e}")
    b=STORE.load(batch_id); c=b.cases[case_id]
    c.candidates[req.tag]=Candidate(qbc_tag=req.tag,value=result.get("value"),display=result.get("display"),method=Method.AI_EXTRACTION,status=ReviewStatus.PENDING,confidence=float(result.get("confidence",0)),evidence=[Evidence(source_file=req.source_file,source_type="ai_input",text=result.get("evidence"))],rule_id="OLLAMA_STRUCTURED_EXTRACTION")
    validate(c); STORE.save(b); return c.candidates[req.tag].model_dump(mode="json")
@app.post("/api/batches/{batch_id}/cases/{case_id}/approve")
def approve_case(batch_id:str,case_id:str):
    b=STORE.load(batch_id); c=b.cases[case_id]; issues=validate(c)
    if issues: raise HTTPException(409,{"message":"case has blocking issues","issues":issues})
    c.state="approved"; c.fhir_bundle=build_bundle(c); STORE.save(b); return {"state":c.state}
@app.get("/api/batches/{batch_id}/cases/{case_id}/fhir")
def fhir(batch_id:str,case_id:str): return build_bundle(STORE.load(batch_id).cases[case_id])
@app.get("/api/batches/{batch_id}/cases/{case_id}/validation")
def validation_report(batch_id:str,case_id:str):
    c=STORE.load(batch_id).cases[case_id]; issues=validate_case(c)
    return {"accepted":not any(i.severity=="error" for i in issues),"errors":sum(i.severity=="error" for i in issues),"warnings":sum(i.severity=="warning" for i in issues),"issues":[i.as_dict() for i in issues]}
@app.post("/api/batches/{batch_id}/cases/{case_id}/export")
def export(batch_id:str,case_id:str,req:ExportRequest):
    b=STORE.load(batch_id); c=b.cases[case_id]
    if c.state!="approved": raise HTTPException(409,"case must be approved before export")
    try: xml,audit=export_case(c,EXPORTS/ batch_id,req.filename)
    except ValueError as e: raise HTTPException(409,str(e))
    c.state="exported"; STORE.save(b); return {"xml":str(xml),"audit":str(audit)}
@app.get("/download/{batch_id}/{filename}")
def download(batch_id:str,filename:str): return FileResponse(EXPORTS/batch_id/filename,filename=filename)

HTML='''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><title>QBC審核工作臺</title><style>
body{font-family:system-ui;margin:0;background:#f4f7fb;color:#18212f}header{background:#173f5f;color:white;padding:16px 24px}main{padding:20px;max-width:1400px;margin:auto}.card{background:white;border-radius:10px;padding:16px;margin-bottom:16px;box-shadow:0 2px 8px #0001}input,button{padding:8px;margin:4px}button{cursor:pointer}.grid{display:grid;grid-template-columns:160px 1fr 140px 140px;gap:1px;background:#dfe6ee}.grid>div{background:white;padding:8px}.ai{background:#fff3bf!important}.rule{background:#dbeafe!important}.structured{background:#dcfce7!important}.conflict{background:#fed7aa!important}.missing{background:#fee2e2!important}.muted{color:#64748b}.issues{color:#b42318;white-space:pre-wrap}.pill{border-radius:999px;padding:3px 8px;background:#e2e8f0}</style></head>
<body><header><h2>QBC審核工作臺 <small>v0.1.0-alpha</small></h2><div>黃=AI　藍=規則　綠=結構化　橘=衝突　紅=缺漏</div></header><main>
<div class="card"><h3>匯入批次</h3><input id="source" size="55" placeholder="資料來源目錄"><input id="batch" value="demo-001"><input id="caseids" placeholder="病例代碼（可空白）"><button onclick="imp()">匯入</button><span id="msg"></span></div>
<div class="card"><h3>批次／病例</h3><select id="batches" onchange="loadBatch()"></select><select id="cases" onchange="loadCase()"></select><button onclick="approveCase()">核准病例</button><input id="filename" size="38" placeholder="QBC_3501200000_11508_001.xml"><button onclick="exportXml()">產生XML</button></div>
<div class="card"><h3>阻擋問題</h3><div id="issues" class="issues"></div></div><div class="card"><h3>欄位證據</h3><div id="fields" class="grid"></div></div></main><script>
let currentBatch='',currentCase='';async function api(url,opt){let r=await fetch(url,opt);let x=await r.json();if(!r.ok)throw Error(JSON.stringify(x));return x}
async function refresh(){let b=await api('/api/batches');batches.innerHTML=b.map(x=>`<option>${x.batch_id}</option>`).join('');if(b.length){currentBatch=b[0].batch_id;await loadBatch()}}
async function imp(){try{let x=await api('/api/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source:source.value,batch_id:batch.value,case_ids:caseids.value?caseids.value.split(','):null})});msg.textContent='完成 '+x.cases.join(',');await refresh()}catch(e){msg.textContent=e}}
async function loadBatch(){currentBatch=batches.value;let b=await api('/api/batches/'+currentBatch);cases.innerHTML=Object.keys(b.cases).map(x=>`<option>${x}</option>`).join('');if(cases.value)await loadCase()}
function cls(c){if(c.status==='conflict')return'conflict';if(c.status==='missing')return'missing';if(c.method.startsWith('ai'))return'ai';if(c.method.startsWith('rule'))return'rule';return'structured'}
async function loadCase(){currentCase=cases.value;let c=await api(`/api/batches/${currentBatch}/cases/${currentCase}`);issues.textContent=c.issues.join('\n')||'無阻擋問題';fields.innerHTML='<div><b>Tag</b></div><div><b>值／證據</b></div><div><b>方法</b></div><div><b>審核</b></div>'+Object.values(c.candidates).sort((a,b)=>a.qbc_tag.localeCompare(b.qbc_tag)).map(x=>`<div class="${cls(x)}"><b>${x.qbc_tag}</b></div><div class="${cls(x)}">${x.value??''}<br><small>${x.evidence?.[0]?.text?.slice(0,180)??x.evidence?.[0]?.source_file??''}</small></div><div class="${cls(x)}">${x.method}<br><span class="pill">${x.status}</span></div><div class="${cls(x)}"><button onclick="review('${x.qbc_tag}','approve')">確認</button><button onclick="review('${x.qbc_tag}','reject')">拒絕</button></div>`).join('')}
async function review(tag,action){let reviewer=prompt('審核者代碼');if(!reviewer)return;await api(`/api/batches/${currentBatch}/cases/${currentCase}/fields/${tag}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reviewer,action})});await loadCase()}
async function approveCase(){try{await api(`/api/batches/${currentBatch}/cases/${currentCase}/approve`,{method:'POST'});alert('病例已核准')}catch(e){alert(e)}}
async function exportXml(){try{let x=await api(`/api/batches/${currentBatch}/cases/${currentCase}/export`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filename:filename.value})});alert(JSON.stringify(x))}catch(e){alert(e)}}refresh();</script></body></html>'''
