import json,requests
class OllamaClient:
    def __init__(self,base_url="http://127.0.0.1:11434",model="qwen3.5:cloud",timeout=120): self.base_url=base_url; self.model=model; self.timeout=timeout
    def extract(self,task,text,schema):
        prompt="Extract only explicit facts. Never guess. Return JSON matching this exact schema and key names.\nSCHEMA:"+json.dumps(schema,ensure_ascii=False)+"\nTASK:"+task+"\nTEXT:\n"+text
        r=requests.post(self.base_url+"/api/chat",json={"model":self.model,"stream":False,"format":schema,"messages":[{"role":"user","content":prompt}],"options":{"temperature":0}},timeout=self.timeout)
        r.raise_for_status(); result=json.loads(r.json()["message"]["content"])
        required=schema.get("required",[])
        missing=[k for k in required if k not in result]
        if missing: raise ValueError("model output failed schema validation; missing: "+", ".join(missing))
        return result
