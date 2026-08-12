import json
from pathlib import Path
from .models import BatchRecord

class JsonStore:
    def __init__(self,root:Path): self.root=root; root.mkdir(parents=True,exist_ok=True)
    def path(self,batch_id): return self.root/f"{batch_id}.json"
    def save(self,batch):
        target=self.path(batch.batch_id); temp=target.with_suffix(".tmp")
        temp.write_text(batch.model_dump_json(indent=2),encoding="utf-8"); temp.replace(target)
    def load(self,batch_id): return BatchRecord.model_validate_json(self.path(batch_id).read_text(encoding="utf-8"))
    def list(self):
        out=[]
        for p in sorted(self.root.glob("*.json")):
            d=json.loads(p.read_text(encoding="utf-8")); out.append({"batch_id":d["batch_id"],"created_at":d["created_at"],"cases":len(d["cases"])})
        return out
